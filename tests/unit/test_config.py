"""Unit tests for :class:`basketball_stats.core.config.Settings`."""

from basketball_stats.core.config import Settings


def test_settings_reads_env_vars(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    monkeypatch.setenv("DATABASE_URL_DIRECT", "postgresql://u:p@h/db")
    s = Settings()  # type: ignore[call-arg]
    assert s.DATABASE_URL == "postgresql://u:p@h/db"
    assert s.ENV == "dev"
    assert s.LOG_LEVEL == "INFO"


def test_async_database_url_rewrites_scheme():
    s = Settings(  # type: ignore[call-arg]
        DATABASE_URL="postgresql://u:p@h/db?sslmode=require",
        DATABASE_URL_DIRECT="postgresql://u:p@h/db",
    )
    assert s.async_database_url == "postgresql+asyncpg://u:p@h/db?sslmode=require"
