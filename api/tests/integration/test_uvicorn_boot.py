"""End-to-end test of workflow steps 1 & 10: a real uvicorn server binds a
real TCP port and serves the app -- not just an in-process TestClient.

Runs uvicorn in a background thread against the app factory (with stubbed
unused ML deps, same as the other integration tests) on a free localhost
port, hits it with a real HTTP client (`requests`), then shuts it down
gracefully with an explicit timeout so a hang can never stall the suite.
"""
from __future__ import annotations

import socket
import sys
import threading
import time
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.testWrapperTimeout import testWrapperTimeout  # noqa: E402

SERVER_START_TIMEOUT_SECONDS = 10
SERVER_SHUTDOWN_TIMEOUT_SECONDS = 10
HTTP_REQUEST_TIMEOUT_SECONDS = 5


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@testWrapperTimeout(timeout=30)
def test_uvicorn_binds_host_port_and_serves_health(stub_unused_ml_dependencies) -> None:  # noqa: ANN001
    import uvicorn

    from app.core.config import AppSettings
    from app.main import create_app

    port = _free_port()
    settings = AppSettings(host="127.0.0.1", port=port, cors_allow_origins=["http://localhost:5173"])
    application = create_app(settings=settings)

    config = uvicorn.Config(application, host=settings.host, port=settings.port, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    try:
        deadline = time.monotonic() + SERVER_START_TIMEOUT_SECONDS
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.05)
        assert server.started, "uvicorn server did not report started within timeout"

        response = requests.get(
            f"http://127.0.0.1:{port}/api/v1/health", timeout=HTTP_REQUEST_TIMEOUT_SECONDS
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["dependencies"]["ready"] is True

        legacy_response = requests.get(
            f"http://127.0.0.1:{port}/api/healthz", timeout=HTTP_REQUEST_TIMEOUT_SECONDS
        )
        assert legacy_response.status_code == 200
    finally:
        server.should_exit = True
        thread.join(timeout=SERVER_SHUTDOWN_TIMEOUT_SECONDS)
        if thread.is_alive():  # pragma: no cover - defensive, should not happen
            pytest.fail("uvicorn server thread did not shut down within timeout")
