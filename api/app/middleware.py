"""Request-scoped middleware: correlation id, timing, and access logging."""
from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import AppSettings
from app.core.errors import internal_error_response

access_logger = logging.getLogger("app.access")

RequestResponseEndpoint = Callable[[Request], Awaitable[Response]]


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request id, times the request, logs it, and optionally
    emits a ``Server-Timing`` header.

    Installed *inside* CORSMiddleware (added to the app before it, so it
    ends up one layer further from the router -- see ``create_app``'s
    middleware-ordering comment) so that CORSMiddleware can still attach
    Access-Control-* headers to whatever this middleware returns, including
    the structured 500 response built here when a handler raises.
    """

    def __init__(self, app: object, settings: AppSettings) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._settings = settings

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Caught here (inside CORS, which wraps this middleware) rather
            # than left to propagate to Starlette's ServerErrorMiddleware,
            # so the structured error response still passes back out
            # through CORSMiddleware and gets Access-Control-* headers
            # attached, instead of reaching the browser as an opaque
            # CORS-blocked network error.
            duration_ms = (time.perf_counter() - start) * 1000
            access_logger.error(
                "request.failed",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "duration_ms": round(duration_ms, 2),
                    "client_ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                },
            )
            response = internal_error_response(request_id)

        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        if self._settings.include_server_timing:
            response.headers["Server-Timing"] = f"app;dur={duration_ms:.2f}"

        log_fields = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        }
        if response.status_code >= 500:
            access_logger.error("request.completed", extra=log_fields)
        elif response.status_code >= 400:
            access_logger.warning("request.completed", extra=log_fields)
        else:
            access_logger.info("request.completed", extra=log_fields)

        return response
