"""FastAPI application factory.

P1 wiring: structlog → middleware → exception handlers → ``/healthz`` router. Uses
the modern :func:`asynccontextmanager` ``lifespan`` (NO ``@app.on_event`` — P1.2
mitigated). Engine startup/shutdown happens here so test code can build its own app
with a different engine without colliding.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from basketball_stats.api.errors import register_exception_handlers
from basketball_stats.api.v1 import health
from basketball_stats.core.config import get_settings
from basketball_stats.core.db import get_engine
from basketball_stats.core.logging import configure_logging
from basketball_stats.core.middleware import RequestIdMiddleware

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize the engine on startup, dispose on shutdown."""
    engine = get_engine()
    log.info("app_startup", url_drivername=engine.url.drivername)
    try:
        yield
    finally:
        log.info("app_shutdown")
        await engine.dispose()


def create_app() -> FastAPI:
    """Build the FastAPI app. Single entry point for prod + tests."""
    settings = get_settings()
    configure_logging(env=settings.ENV, level=settings.LOG_LEVEL)

    app = FastAPI(
        title="Basketball Stats API",
        version="0.1.0",
        description="FastAPI + Postgres pur (Neon) — FCBQ amateur lliga.",
        lifespan=lifespan,
    )
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(health.router)
    return app


# NOTE: NO module-level ``app = create_app()`` — that would require ``DATABASE_URL`` at
# import time, breaking ``pytest --collect-only`` and tests that monkeypatch env.
# Uvicorn uses ``--factory`` so it calls ``create_app()`` after the env is set up.
