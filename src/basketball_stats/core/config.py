"""Pydantic Settings — single source of runtime config.

Rewrites Neon's ``postgresql://`` to ``postgresql+asyncpg://`` for SQLAlchemy 2.0 async
engine (RESEARCH §2.3 Q3 — Strategy A: rewrite in code, keep Neon dashboard URLs intact).

Two database URLs are required:
- ``DATABASE_URL``      → pooled connection (PgBouncer, used by the FastAPI app).
- ``DATABASE_URL_DIRECT`` → direct connection (used by Alembic — pgbouncer transaction
  mode silently corrupts migration state, RESEARCH R3).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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

        Neon hands out ``postgresql://...`` URLs; SQLAlchemy 2.0 async engine needs
        ``postgresql+asyncpg://...``. Done as a property (not on parse) so the original
        value round-trips cleanly to logs / diagnostics.
        """
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance.

    Lazy + cached so unit tests can monkeypatch env without colliding with
    import-time evaluation.
    """
    return Settings()  # type: ignore[call-arg]
