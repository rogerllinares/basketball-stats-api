"""Integration tests for ``/healthz``.

Hits a real Postgres container (no SQLite, no mocks — D-16) via the ASGI app.
Two tests: happy path (200 + ``db:ok``) and the D-10 contract test (503 + ``db:fail``
when the engine raises).
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from basketball_stats.core import db as db_module
from basketball_stats.main import create_app


@pytest.mark.asyncio
async def test_healthz_returns_ok_when_db_reachable(monkeypatch, database_url_direct):
    """Happy path: real Postgres up, ``SELECT 1`` succeeds, 200 with literal shape."""
    monkeypatch.setenv("DATABASE_URL", database_url_direct)
    monkeypatch.setenv("DATABASE_URL_DIRECT", database_url_direct)
    db_module.get_engine.cache_clear()
    db_module.get_session_factory.cache_clear()
    from basketball_stats.core.config import get_settings

    get_settings.cache_clear()

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "db": "ok"}


@pytest.mark.asyncio
async def test_healthz_returns_503_when_db_unreachable(monkeypatch):
    """D-10 contract: unreachable DB → 503 + ``db:fail`` + sanitized error."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://nope:nope@127.0.0.1:1/none")
    monkeypatch.setenv("DATABASE_URL_DIRECT", "postgresql://nope:nope@127.0.0.1:1/none")
    db_module.get_engine.cache_clear()
    db_module.get_session_factory.cache_clear()
    from basketball_stats.core.config import get_settings

    get_settings.cache_clear()

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/healthz")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["db"] == "fail"
    assert "error" in body
