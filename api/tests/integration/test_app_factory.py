"""Integration tests for the full app factory: CORS, routing, error
handling, and startup/shutdown lifecycle, driven end-to-end through
FastAPI's TestClient against a real (in-process) ASGI app.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.testWrapperTimeout import testWrapperTimeout  # noqa: E402


@pytest.fixture
def client(stub_unused_ml_dependencies):  # noqa: ANN001, ARG001
    """Build a real app (via the factory) against explicit test settings.

    Imports happen here, *after* `stub_unused_ml_dependencies` has patched
    `sys.modules`, so `app.main` -> `app.api.routes` -> `app.ml.model`
    resolve their unused pandas/joblib/... imports against the stubs
    instead of requiring those heavy packages to be installed in the test
    image.
    """
    from fastapi.testclient import TestClient

    from app.core.config import AppSettings
    from app.main import create_app

    settings = AppSettings(
        env="dev",
        app_name="titanic-api-test",
        cors_allow_origins=["http://localhost:5173"],
        include_server_timing=True,
    )
    application = create_app(settings=settings)
    with TestClient(application) as test_client:
        yield test_client


@testWrapperTimeout
def test_health_endpoint_returns_expected_schema(client) -> None:  # noqa: ANN001
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"

    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "titanic-api-test"
    assert body["env"] == "dev"
    assert body["time"].endswith("Z")
    assert isinstance(body["uptime_ms"], (int, float))
    assert body["uptime_ms"] >= 0
    assert body["dependencies"]["ready"] is True


@testWrapperTimeout
def test_server_timing_header_present(client) -> None:  # noqa: ANN001
    response = client.get("/api/v1/health")

    assert "server-timing" in response.headers
    assert response.headers["server-timing"].startswith("app;dur=")


@testWrapperTimeout
def test_request_id_header_present(client) -> None:  # noqa: ANN001
    response = client.get("/api/v1/health")

    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) > 0


@testWrapperTimeout
def test_readiness_flag_true_after_lifespan_startup(client) -> None:  # noqa: ANN001
    assert client.app.state.ready is True
    assert client.app.state.process_start is not None


@testWrapperTimeout
def test_cors_preflight_allows_configured_origin(client) -> None:  # noqa: ANN001
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


@testWrapperTimeout
def test_cors_preflight_rejects_unconfigured_origin(client) -> None:  # noqa: ANN001
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


@testWrapperTimeout
def test_unknown_route_returns_structured_404(client) -> None:  # noqa: ANN001
    response = client.get("/this/route/does/not/exist")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "http_404"
    assert "request_id" in body


@testWrapperTimeout
def test_predict_validation_error_returns_structured_422(client) -> None:  # noqa: ANN001
    response = client.post("/api/predict", json={"Pclass": 99, "Sex": "male"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["message"] == "Request validation failed"
    assert isinstance(body["details"], list)
    assert len(body["details"]) >= 1


@testWrapperTimeout
def test_unexpected_exception_returns_structured_500_without_leaking(client) -> None:  # noqa: ANN001
    async def _boom() -> None:
        raise RuntimeError("super secret internal stack detail")

    client.app.add_api_route("/__test-only/boom", _boom, methods=["GET"])

    response = client.get("/__test-only/boom")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "Internal server error"
    assert "super secret internal stack detail" not in response.text


@testWrapperTimeout
def test_legacy_healthz_and_readyz_still_reachable(client) -> None:  # noqa: ANN001
    """Regression guard: this feature must not break the pre-existing
    /api/healthz and /api/readyz endpoints from the predict feature.
    """
    healthz = client.get("/api/healthz")
    readyz = client.get("/api/readyz")

    assert healthz.status_code == 200
    assert healthz.json() == {"status": "ok"}
    assert readyz.status_code == 200
    assert readyz.json() == {"status": "ready"}


@testWrapperTimeout
def test_docs_disabled_in_prod_settings(stub_unused_ml_dependencies) -> None:  # noqa: ANN001
    from fastapi.testclient import TestClient

    from app.core.config import AppSettings
    from app.main import create_app

    prod_settings = AppSettings(env="prod", cors_allow_origins=["https://titanic.example.com"])
    prod_app = create_app(settings=prod_settings)

    with TestClient(prod_app) as prod_client:
        assert prod_client.get("/docs").status_code == 404
        assert prod_client.get("/openapi.json").status_code == 404


@testWrapperTimeout
def test_docs_enabled_outside_prod(client) -> None:  # noqa: ANN001
    response = client.get("/openapi.json")

    assert response.status_code == 200
