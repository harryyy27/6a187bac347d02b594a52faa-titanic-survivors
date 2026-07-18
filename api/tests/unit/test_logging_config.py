"""Unit tests for app.core.logging_config.init_logging."""
from __future__ import annotations

import io
import json
import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.testWrapperTimeout import testWrapperTimeout  # noqa: E402

from app.core.config import AppSettings  # noqa: E402
from app.core.logging_config import _MARKER_ATTR, init_logging  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_root_logger_handlers() -> None:
    """Prevent handlers installed by a test from leaking into the next one."""
    root = logging.getLogger()
    before = list(root.handlers)
    yield
    for handler in list(root.handlers):
        if handler not in before:
            root.removeHandler(handler)


@testWrapperTimeout
def test_json_log_line_contains_required_fields() -> None:
    settings = AppSettings(log_json=True, log_level="INFO", env="dev", app_name="titanic-api")
    stream = io.StringIO()

    init_logging(settings, stream=stream, version="1.2.3")
    logging.getLogger("app.test").info("hello world")

    line = stream.getvalue().strip().splitlines()[-1]
    payload = json.loads(line)

    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.test"
    assert payload["env"] == "dev"
    assert payload["app"] == "titanic-api"
    assert payload["version"] == "1.2.3"
    assert "timestamp" in payload and payload["timestamp"].endswith("Z")


@testWrapperTimeout
def test_extra_request_fields_are_included_when_present() -> None:
    settings = AppSettings(log_json=True, log_level="INFO")
    stream = io.StringIO()

    init_logging(settings, stream=stream)
    logging.getLogger("app.access").info(
        "request.completed",
        extra={
            "request_id": "abc-123",
            "method": "GET",
            "path": "/api/v1/health",
            "status_code": 200,
            "duration_ms": 4.2,
            "client_ip": "127.0.0.1",
            "user_agent": "pytest",
        },
    )

    payload = json.loads(stream.getvalue().strip().splitlines()[-1])

    assert payload["request_id"] == "abc-123"
    assert payload["method"] == "GET"
    assert payload["path"] == "/api/v1/health"
    assert payload["status_code"] == 200
    assert payload["duration_ms"] == 4.2
    assert payload["client_ip"] == "127.0.0.1"
    assert payload["user_agent"] == "pytest"


@testWrapperTimeout
def test_root_logger_level_matches_settings() -> None:
    settings = AppSettings(log_level="WARNING")
    init_logging(settings, stream=io.StringIO())

    assert logging.getLogger().level == logging.WARNING


@testWrapperTimeout
def test_uvicorn_loggers_are_harmonized_and_do_not_propagate() -> None:
    settings = AppSettings(log_json=True, log_level="INFO")
    init_logging(settings, stream=io.StringIO())

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        assert uvicorn_logger.propagate is False
        assert any(getattr(h, _MARKER_ATTR, False) for h in uvicorn_logger.handlers)


@testWrapperTimeout
def test_repeated_init_does_not_duplicate_handlers() -> None:
    settings = AppSettings(log_json=True, log_level="INFO")

    init_logging(settings, stream=io.StringIO())
    root = logging.getLogger()
    managed_after_first = [h for h in root.handlers if getattr(h, _MARKER_ATTR, False)]

    init_logging(settings, stream=io.StringIO())
    managed_after_second = [h for h in root.handlers if getattr(h, _MARKER_ATTR, False)]

    assert len(managed_after_first) == 1
    assert len(managed_after_second) == 1


@testWrapperTimeout
def test_console_formatter_used_when_log_json_false() -> None:
    settings = AppSettings(log_json=False, log_level="INFO", env="dev", app_name="titanic-api")
    stream = io.StringIO()

    init_logging(settings, stream=stream)
    logging.getLogger("app.test").info("plain text line")

    output = stream.getvalue()
    assert "plain text line" in output
    with pytest.raises(json.JSONDecodeError):
        json.loads(output.strip().splitlines()[-1])
