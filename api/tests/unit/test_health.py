"""Unit tests for app.api.health: the GET {API_V1_PREFIX}/health handler.

These call the ``health()`` coroutine directly against a hand-built
Starlette ``Request``/``Response`` pair carrying a minimal fake ``app.state``
(no TestClient, no full app factory, no ML dependency stubs needed), so they
stay fast and only exercise this handler's own payload-building logic:
uptime calculation, response schema, dependencies payload, and the
Cache-Control header. Full-stack behaviour (routing, CORS, Server-Timing,
access logging) is covered separately by the integration suite.
"""
from __future__ import annotations

import asyncio
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from starlette.requests import Request
from starlette.responses import Response

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.testWrapperTimeout import testWrapperTimeout  # noqa: E402

from app.api.health import health  # noqa: E402
from app.core.config import AppSettings  # noqa: E402


def _make_app_state(
    *,
    process_start: float | None,
    ready: bool = True,
    version: str = "1.2.3",
    settings: AppSettings | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        settings=settings if settings is not None else AppSettings(app_name="titanic-api-test", env="dev"),
        process_start=process_start,
        ready=ready,
        version=version,
    )


def _make_request(app_state: SimpleNamespace) -> Request:
    fake_app = SimpleNamespace(state=app_state)
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/health",
        "headers": [],
        "query_string": b"",
        "client": ("127.0.0.1", 1234),
        "app": fake_app,
        "scheme": "http",
        "server": ("testserver", 80),
        "root_path": "",
    }
    return Request(scope)


def _run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


@testWrapperTimeout
def test_health_returns_expected_schema_and_dependencies() -> None:
    app_state = _make_app_state(process_start=time.perf_counter(), version="9.9.9")
    request = _make_request(app_state)
    response = Response()

    body = _run(health(request, response))

    assert body.status == "ok"
    assert body.service == "titanic-api-test"
    assert body.env == "dev"
    assert body.version == "9.9.9"
    assert body.dependencies == {"ready": True, "model_artifacts": "unknown"}


@testWrapperTimeout
def test_health_sets_cache_control_no_store() -> None:
    app_state = _make_app_state(process_start=time.perf_counter())
    request = _make_request(app_state)
    response = Response()

    _run(health(request, response))

    assert response.headers["Cache-Control"] == "no-store"


@testWrapperTimeout
def test_health_time_is_utc_iso8601_with_z_suffix() -> None:
    app_state = _make_app_state(process_start=time.perf_counter())
    request = _make_request(app_state)
    response = Response()

    before = datetime.now(timezone.utc)
    body = _run(health(request, response))
    after = datetime.now(timezone.utc)

    assert body.time.endswith("Z")
    parsed = datetime.fromisoformat(body.time.replace("Z", "+00:00"))
    assert before <= parsed <= after


@testWrapperTimeout
def test_health_uptime_ms_is_non_negative_when_process_start_known() -> None:
    # process_start set slightly in the past so uptime is deterministically > 0.
    app_state = _make_app_state(process_start=time.perf_counter() - 0.05)
    request = _make_request(app_state)
    response = Response()

    body = _run(health(request, response))

    assert isinstance(body.uptime_ms, float)
    assert body.uptime_ms > 0


@testWrapperTimeout
def test_health_uptime_ms_increases_over_time() -> None:
    app_state = _make_app_state(process_start=time.perf_counter())
    request = _make_request(app_state)

    first_body = _run(health(request, Response()))
    time.sleep(0.05)
    second_body = _run(health(request, Response()))

    assert second_body.uptime_ms > first_body.uptime_ms


@testWrapperTimeout
def test_health_uptime_ms_defaults_to_zero_when_process_start_missing() -> None:
    app_state = _make_app_state(process_start=None)
    request = _make_request(app_state)
    response = Response()

    body = _run(health(request, response))

    assert body.uptime_ms == 0.0


@testWrapperTimeout
def test_health_dependencies_reflect_ready_false_before_startup_completes() -> None:
    app_state = _make_app_state(process_start=time.perf_counter(), ready=False)
    request = _make_request(app_state)
    response = Response()

    body = _run(health(request, response))

    assert body.dependencies["ready"] is False


@testWrapperTimeout
def test_health_version_falls_back_to_unknown_when_unset_on_state() -> None:
    app_state = SimpleNamespace(
        settings=AppSettings(app_name="titanic-api-test", env="dev"),
        process_start=time.perf_counter(),
        ready=True,
        # deliberately no `version` attribute set
    )
    request = _make_request(app_state)
    response = Response()

    body = _run(health(request, response))

    assert body.version == "unknown"
