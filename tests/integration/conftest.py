"""Integration test fixtures — Postgres testcontainer + alembic upgrade.

Scoped to ``tests/integration/`` so unit tests stay docker-free.

D-16: real Postgres from P1; D-08: alembic round-trip validated in CI (see
``ci.yml``). R5: alembic runs as a subprocess, never from inside the app process.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer]:
    """Spin up a real Postgres 16-alpine for the test session."""
    with PostgresContainer(
        image="postgres:16-alpine",
        username="test",
        password="test",
        dbname="test_db",
        driver=None,
    ) as pg:
        yield pg


@pytest.fixture(scope="session")
def database_url_direct(postgres_container: PostgresContainer) -> str:
    """Return a ``postgresql://`` direct URL (Alembic-compatible)."""
    return postgres_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql://"
    )


@pytest.fixture(scope="session")
def database_url_async(database_url_direct: str) -> str:
    """Return the async (asyncpg) URL for SQLAlchemy."""
    return database_url_direct.replace("postgresql://", "postgresql+asyncpg://", 1)


@pytest.fixture(scope="session", autouse=True)
def _run_alembic_upgrade(database_url_direct: str) -> Iterator[None]:
    """Bring the test DB to ``head`` once per session (R5 — subprocess, never in-process)."""
    env = os.environ.copy()
    env["DATABASE_URL_DIRECT"] = database_url_direct
    subprocess.run(
        ["alembic", "upgrade", "head"],
        env=env,
        check=True,
    )
    yield


@pytest_asyncio.fixture
async def engine(database_url_async: str) -> AsyncIterator[AsyncEngine]:
    e = create_async_engine(database_url_async, pool_pre_ping=True)
    try:
        yield e
    finally:
        await e.dispose()


@pytest_asyncio.fixture
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def seeded_session(db_session: AsyncSession) -> AsyncIterator[AsyncSession]:
    """Seed the minimal Catalan fixture on a fresh per-test session.

    P2 — used by standings/leaderboards/endpoint tests that need 24 box-scores +
    2 teams + 12 players. Uses ``force=True`` so prior test state is wiped.
    """
    from basketball_stats.seed.minimal import seed

    await seed(db_session, force=True)
    yield db_session


@pytest_asyncio.fixture
async def async_client(
    seeded_session: AsyncSession,
) -> AsyncIterator[httpx.AsyncClient]:  # type: ignore[name-defined]  # noqa: F821
    """Yield an httpx AsyncClient bound to the FastAPI app + the seeded test session.

    Overrides ``get_db`` so every endpoint touches the test container DB.
    """
    import httpx

    from basketball_stats.api.v1.deps import get_db
    from basketball_stats.main import create_app

    app = create_app()

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield seeded_session

    app.dependency_overrides[get_db] = override_get_db

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
