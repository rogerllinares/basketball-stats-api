"""Unit tests for :class:`basketball_stats.core.config.Settings`."""

from basketball_stats.core.config import Settings, to_asyncpg_url


def test_settings_reads_env_vars(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    monkeypatch.setenv("DATABASE_URL_DIRECT", "postgresql://u:p@h/db")
    s = Settings()  # type: ignore[call-arg]
    assert s.DATABASE_URL == "postgresql://u:p@h/db"
    assert s.ENV == "dev"
    assert s.LOG_LEVEL == "INFO"


def test_async_database_url_strips_libpq_params():
    """``sslmode`` / ``channel_binding`` are libpq syntax; asyncpg rejects them."""
    s = Settings(  # type: ignore[call-arg]
        DATABASE_URL="postgresql://u:p@h/db?sslmode=require&channel_binding=require",
        DATABASE_URL_DIRECT="postgresql://u:p@h/db",
    )
    assert s.async_database_url == "postgresql+asyncpg://u:p@h/db"


def test_to_asyncpg_url_idempotent_on_already_async_scheme():
    src = "postgresql+asyncpg://u:p@h/db?sslmode=require"
    assert to_asyncpg_url(src) == "postgresql+asyncpg://u:p@h/db"


def test_to_asyncpg_url_preserves_unknown_query_params():
    src = "postgresql://u:p@h/db?sslmode=require&application_name=svc"
    assert to_asyncpg_url(src) == "postgresql+asyncpg://u:p@h/db?application_name=svc"
