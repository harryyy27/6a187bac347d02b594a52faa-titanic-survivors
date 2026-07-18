"""Structured error schema and global exception handlers."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.core.errors")


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
    details: Any | None = None
    request_id: str | None = None


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _error_payload(*, code: str, message: str, details: Any | None, request_id: str | None) -> dict[str, Any]:
    return ErrorResponse(
        error=ErrorDetail(code=code, message=message),
        details=details,
        request_id=request_id,
    ).model_dump()


async def _handle_http_exception(request: Request, exc: Exception) -> ORJSONResponse:
    assert isinstance(exc, (HTTPException, StarletteHTTPException))  # noqa: S101
    request_id = _request_id(request)
    logger.warning(
        "error.http_exception",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": exc.status_code,
        },
    )
    payload = _error_payload(
        code=f"http_{exc.status_code}",
        message=str(exc.detail),
        details=None,
        request_id=request_id,
    )
    headers = getattr(exc, "headers", None)
    return ORJSONResponse(status_code=exc.status_code, content=payload, headers=headers)


async def _handle_validation_error(request: Request, exc: Exception) -> ORJSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101
    request_id = _request_id(request)
    errors = [
        {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]
    logger.warning(
        "error.validation_failed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
        },
    )
    payload = _error_payload(
        code="validation_error",
        message="Request validation failed",
        details=errors,
        request_id=request_id,
    )
    return ORJSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=payload)


def internal_error_response(request_id: str | None) -> ORJSONResponse:
    """Build the structured 500 body. Shared by the app-level generic
    ``Exception`` handler (registered below, a defense-in-depth safety net
    for anything that escapes the ASGI middleware stack) and by
    ``RequestContextMiddleware`` (which catches exceptions itself so the
    resulting response still passes back through the CORS middleware that
    wraps it, instead of unwinding past it to ``ServerErrorMiddleware``
    where CORS headers would never be attached).
    """
    payload = _error_payload(
        code="internal_error",
        message="Internal server error",
        details=None,
        request_id=request_id,
    )
    return ORJSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload)


async def _handle_unexpected_exception(request: Request, exc: Exception) -> ORJSONResponse:
    request_id = _request_id(request)
    logger.error(
        "error.unhandled_exception",
        exc_info=exc,
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        },
    )
    return internal_error_response(request_id)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the standardized ``ErrorResponse`` handlers to ``app``."""
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(HTTPException, _handle_http_exception)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(Exception, _handle_unexpected_exception)
