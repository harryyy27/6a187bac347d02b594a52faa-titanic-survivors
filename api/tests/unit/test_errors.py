"""Unit tests for app.core.errors: ErrorResponse shape per exception type.

These call our handler coroutines directly with hand-built Starlette
``Request``/exception objects (no TestClient / running app needed), so they
stay fast and only exercise our own error-formatting logic.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import orjson
import pytest
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.testWrapperTimeout import testWrapperTimeout  # noqa: E402

from app.core.errors import (  # noqa: E402
    _handle_http_exception,
    _handle_unexpected_exception,
    _handle_validation_error,
)


def _make_request(request_id: str | None = "req-1") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/boom",
        "headers": [],
        "query_string": b"",
        "client": ("127.0.0.1", 1234),
        "app": None,
        "scheme": "http",
        "server": ("testserver", 80),
        "root_path": "",
    }
    request = Request(scope)
    if request_id is not None:
        request.state.request_id = request_id
    return request


def _run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


@testWrapperTimeout
def test_http_exception_is_mapped_to_structured_error() -> None:
    request = _make_request()
    exc = HTTPException(status_code=404, detail="Not Found")

    response = _run(_handle_http_exception(request, exc))
    body = orjson.loads(response.body)

    assert response.status_code == 404
    assert body["error"]["code"] == "http_404"
    assert body["error"]["message"] == "Not Found"
    assert body["details"] is None
    assert body["request_id"] == "req-1"


@testWrapperTimeout
def test_validation_error_is_mapped_to_structured_error_with_details() -> None:
    request = _make_request(request_id="req-2")

    try:
        from pydantic import BaseModel

        class _Model(BaseModel):
            age: int

        _Model(age="not-a-number")
    except Exception as pydantic_exc:  # noqa: BLE001
        exc = RequestValidationError(errors=pydantic_exc.errors())  # type: ignore[attr-defined]

    response = _run(_handle_validation_error(request, exc))
    body = orjson.loads(response.body)

    assert response.status_code == 422
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["message"] == "Request validation failed"
    assert isinstance(body["details"], list)
    assert body["details"][0]["loc"] == ["age"]
    assert body["request_id"] == "req-2"


@testWrapperTimeout
def test_unexpected_exception_does_not_leak_internal_message() -> None:
    request = _make_request(request_id="req-3")
    exc = RuntimeError("super secret internal stack detail")

    response = _run(_handle_unexpected_exception(request, exc))
    body = orjson.loads(response.body)

    assert response.status_code == 500
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "Internal server error"
    assert "super secret internal stack detail" not in orjson.dumps(body).decode()
    assert body["request_id"] == "req-3"


@testWrapperTimeout
def test_request_id_is_none_when_not_set_on_request_state() -> None:
    request = _make_request(request_id=None)
    exc = HTTPException(status_code=400, detail="Bad Request")

    response = _run(_handle_http_exception(request, exc))
    body = orjson.loads(response.body)

    assert body["request_id"] is None
