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
