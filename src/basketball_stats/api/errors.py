"""Global exception handlers.

Mitigates PITFALLS P1.6 (Python tracebacks leaked to clients). Established in P1 so
every future endpoint inherits sanitized error responses by default.

Two handlers:

- :class:`fastapi.exceptions.RequestValidationError` → 422 ``{detail, code}``.
- :class:`Exception`                                → 500 ``{detail, code, request_id}``,
  full traceback logged via structlog (never serialized).
"""

from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

log = structlog.get_logger(__name__)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Translate Pydantic validation errors into a sanitized 422 payload."""
    return JSONResponse(
        status_code=422,
        content={
            "detail": "request validation failed",
            "code": "validation_error",
            "errors": exc.errors(),
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Translate any uncaught exception into a sanitized 500 payload.

    The full traceback is logged via structlog (``log.exception`` captures it) but never
    serialized to the response body — only the exception class name leaks.
    """
    log.exception("unhandled_exception", exc_class=exc.__class__.__name__)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "internal error",
            "code": "internal_error",
            "exc_class": exc.__class__.__name__,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Install the global handlers on ``app``. Call once during :func:`create_app`."""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)


__all__: list[Any] = [
    "register_exception_handlers",
    "validation_exception_handler",
    "unhandled_exception_handler",
]
