"""Async engine factory + :func:`get_db` dependency.

Pattern from ``tiangolo/full-stack-fastapi-template``; mitigates PITFALLS P1.3
(session leaked across requests) by yielding from an async generator with explicit
``finally close``.

``pool_pre_ping=True`` survives stale Neon connections when the compute auto-suspends.

Engine + sessionmaker are built lazily on first request (via :func:`get_engine`)
so importing this module does not require ``DATABASE_URL`` to be set.
"""

from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from basketball_stats.core.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """Return the cached async engine.

    Lazy so unit tests can monkeypatch :func:`get_settings` before the engine is built.
    """
    settings = get_settings()
    return create_async_engine(
        settings.async_database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        # Neon requires SSL. asyncpg rejects ``sslmode`` URL params (libpq
        # syntax), so SSL is enforced here. ``to_asyncpg_url`` strips
        # ``sslmode`` from the URL upstream.
        connect_args={"ssl": "require"},
    )


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the cached :class:`AsyncSession` factory."""
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an :class:`AsyncSession`, closing it on exit.

    Use as a FastAPI dependency: ``session: AsyncSession = Depends(get_db)``.
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        await session.close()
