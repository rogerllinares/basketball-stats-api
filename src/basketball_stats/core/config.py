"""Pydantic Settings — single source of runtime config.

Rewrites Neon's ``postgresql://`` to ``postgresql+asyncpg://`` for SQLAlchemy 2.0 async
engine (RESEARCH §2.3 Q3 — Strategy A: rewrite in code, keep Neon dashboard URLs intact).

Two database URLs are required:
- ``DATABASE_URL``      → pooled connection (PgBouncer, used by the FastAPI app).
- ``DATABASE_URL_DIRECT`` → direct connection (used by Alembic — pgbouncer transaction
  mode silently corrupts migration state, RESEARCH R3).
"""

from functools import lru_cache
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from pydantic_settings import BaseSettings, SettingsConfigDict


def to_asyncpg_url(raw: str) -> str:
    """Convert a Neon-style ``postgresql://...?sslmode=require`` URL to one
    asyncpg's dialect accepts.

    Two steps:
    1. Swap the scheme to ``postgresql+asyncpg://`` so SQLAlchemy picks the
       async dialect.
    2. Strip libpq-only query params (``sslmode``, ``channel_binding``).
       asyncpg's ``connect()`` raises ``TypeError: unexpected keyword
       argument 'sslmode'``; SSL is enforced via ``connect_args={"ssl":
       "require"}`` in db.py and migrations/env.py instead.
    """
    if not raw.startswith("postgresql+asyncpg://"):
        raw = raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    parsed = urlparse(raw)
    params = parse_qs(parsed.query)
    params.pop("sslmode", None)
    params.pop("channel_binding", None)
    return urlunparse(parsed._replace(query=urlencode(params, doseq=True)))


class Settings(BaseSettings):
    """Runtime configuration sourced from environment variables / .env file."""

    DATABASE_URL: str
    DATABASE_URL_DIRECT: str
    ENV: str = "dev"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def async_database_url(self) -> str:
        """Return ``DATABASE_URL`` rewritten for the asyncpg driver.

        Done as a property (not on parse) so the original value round-trips
        cleanly to logs / diagnostics. See :func:`to_asyncpg_url` for the
        scheme swap + libpq-param stripping rationale.
        """
        return to_asyncpg_url(self.DATABASE_URL)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance.

    Lazy + cached so unit tests can monkeypatch env without colliding with
    import-time evaluation.
    """
    return Settings()  # type: ignore[call-arg]
