"""Health endpoint — single ``/healthz`` with real DB probe (D-09 / D-10).

Returns 200 ``{"status":"ok","db":"ok"}`` on success; 503 ``{"status":"degraded",
"db":"fail","error":"<class-name>"}`` if ``SELECT 1`` raises. The status code is the
contract Koyeb's HTTP health check reads (auto-restarts after 5 consecutive failures);
the body is for humans (D-10).
"""

import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from basketball_stats.api.v1.deps import get_db

router = APIRouter(tags=["health"])
log = structlog.get_logger(__name__)


@router.get("/healthz")
async def healthz(session: AsyncSession = Depends(get_db)) -> JSONResponse:
    """Probe DB with ``SELECT 1``; return 200 or 503."""
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        log.warning("healthz_db_fail", exc_class=exc.__class__.__name__)
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "db": "fail",
                "error": exc.__class__.__name__,
            },
        )
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "db": "ok"},
    )
