"""Custom ASGI middleware binding ``request_id`` to structlog contextvars.

Pre-OpenTelemetry pattern (D-20): demonstrates distributed-tracing awareness without
importing the full otel stack (scope creep for an MVP). Accepts an inbound
``X-Request-Id`` header when present (cross-service correlation), generates a UUID4
fallback otherwise; binds to :func:`structlog.contextvars.bind_contextvars` so every log
line within the request automatically includes ``request_id``; echoes the value back
through the response header.
"""

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "x-request-id"


class RequestIdMiddleware:
    """Bind ``request_id`` to structlog contextvars + echo header on response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers: list[tuple[bytes, bytes]] = scope.get("headers", [])
        inbound: bytes | None = None
        for name, value in headers:
            if name.lower() == REQUEST_ID_HEADER.encode():
                inbound = value
                break
        request_id = inbound.decode() if inbound else uuid.uuid4().hex

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                msg_headers: list[tuple[bytes, bytes]] = list(message.get("headers", []))
                msg_headers.append((REQUEST_ID_HEADER.encode(), request_id.encode()))
                message["headers"] = msg_headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        finally:
            structlog.contextvars.clear_contextvars()


__all__: list[Any] = ["RequestIdMiddleware", "REQUEST_ID_HEADER"]


# Keep these imports for type-checker happiness with Starlette versions that vary.
_ = (Awaitable, Callable)
