"""Unit tests for app.middleware.RequestContextMiddleware.

Exercises the middleware directly against a minimal ASGI app (not the full
`app.main` factory / TestClient, and no ML dependency stubs needed), so these
stay fast and only assert on this middleware's own behaviour: request-id
generation/propagation, the Server-Timing header, and the structured
`request.completed` access-log record's fields (method, path, status_code,
duration_ms, client_ip, user_agent) required by the "per-request logging"
workflow step.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.testWrapperTimeout import testWrapperTimeout  # noqa: E402

from app.core.config import AppSettings  # noqa: E402
from app.middleware import RequestContextMiddleware  # noqa: E402


async def _ok(request):  # type: ignore[no-untyped-def]  # noqa: ARG001, ANN001
    return PlainTextResponse("ok")


async def _boom(request):  # type: ignore[no-untyped-def]  # noqa: ARG001, ANN001
    raise RuntimeError("kaboom")


def _make_client(*, include_server_timing: bool = True) -> TestClient:
    settings = AppSettings(include_server_timing=include_server_timing)
    app = Starlette(routes=[Route("/ok", _ok), Route("/boom", _boom)])
    app.add_middleware(RequestContextMiddleware, settings=settings)
    return TestClient(app, raise_server_exceptions=False)


@testWrapperTimeout
def test_generates_request_id_when_absent() -> None:
    client = _make_client()

    response = client.get("/ok")

    assert response.status_code == 200
    assert len(response.headers["x-request-id"]) > 0


@testWrapperTimeout
def test_propagates_incoming_request_id() -> None:
    client = _make_client()

    response = client.get("/ok", headers={"X-Request-ID": "caller-supplied-id"})

    assert response.headers["x-request-id"] == "caller-supplied-id"


@testWrapperTimeout
def test_server_timing_header_present_when_enabled() -> None:
    client = _make_client(include_server_timing=True)

    response = client.get("/ok")

    assert response.headers["server-timing"].startswith("app;dur=")


@testWrapperTimeout
def test_server_timing_header_absent_when_disabled() -> None:
    client = _make_client(include_server_timing=False)

    response = client.get("/ok")

    assert "server-timing" not in response.headers


@testWrapperTimeout
def test_access_log_contains_required_structured_fields(caplog: pytest.LogCaptureFixture) -> None:
    client = _make_client()

    with caplog.at_level(logging.INFO, logger="app.access"):
        client.get("/ok", headers={"User-Agent": "pytest-agent/1.0"})

    records = [r for r in caplog.records if r.name == "app.access" and r.message == "request.completed"]
    assert len(records) == 1
    record = records[0]

    assert record.request_id
    assert record.method == "GET"
    assert record.path == "/ok"
    assert record.status_code == 200
    assert isinstance(record.duration_ms, float)
    assert record.duration_ms >= 0
    assert record.client_ip is not None
    assert record.user_agent == "pytest-agent/1.0"


@testWrapperTimeout
def test_access_log_level_is_info_for_2xx(caplog: pytest.LogCaptureFixture) -> None:
    client = _make_client()

    with caplog.at_level(logging.INFO, logger="app.access"):
        client.get("/ok")

    record = next(r for r in caplog.records if r.name == "app.access")
    assert record.levelname == "INFO"


@testWrapperTimeout
def test_unhandled_exception_is_converted_to_structured_500(caplog: pytest.LogCaptureFixture) -> None:
    client = _make_client()

    with caplog.at_level(logging.ERROR, logger="app.access"):
        response = client.get("/boom")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert "kaboom" not in response.text

    error_records = [r for r in caplog.records if r.name == "app.access" and r.message == "request.failed"]
    assert len(error_records) == 1
    assert error_records[0].status_code == 500
