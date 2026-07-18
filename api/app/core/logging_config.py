"""Structured (JSON) logging setup, shared by the app and uvicorn loggers.

``init_logging`` is idempotent: calling it more than once (e.g. across
``--reload`` cycles, or once per test) never accumulates duplicate handlers
on the root logger.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import IO, Any

from app.core.config import AppSettings

_MARKER_ATTR = "_titanic_api_json_handler"

# Fields the JSON log line should carry when present on the record, in a
# fixed order for readability.
_EXTRA_FIELD_ORDER = (
    "request_id",
    "method",
    "path",
    "status_code",
    "duration_ms",
    "client_ip",
    "user_agent",
)


class JsonLogFormatter(logging.Formatter):
    """Renders a ``logging.LogRecord`` as a single-line JSON object."""

    def __init__(self, *, env: str, app_name: str, version: str) -> None:
        super().__init__()
        self._env = env
        self._app_name = app_name
        self._version = version

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "env": self._env,
            "app": self._app_name,
            "version": self._version,
        }
        for field_name in _EXTRA_FIELD_ORDER:
            if field_name in record.__dict__:
                payload[field_name] = record.__dict__[field_name]

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


class ConsoleLogFormatter(logging.Formatter):
    """Human-friendly formatter used when ``LOG_JSON`` is disabled."""

    def __init__(self, *, env: str, app_name: str) -> None:
        super().__init__(
            fmt=f"%(asctime)s [{app_name}:{env}] %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )


def init_logging(settings: AppSettings, *, stream: IO[str] | None = None, version: str = "unknown") -> None:
    """Configure root + uvicorn logging for structured output.

    Idempotent: repeated calls replace the previously installed handler
    instead of stacking a new one on top, so log lines are never duplicated.
    """
    target_stream = stream if stream is not None else sys.stdout
    level = getattr(logging, settings.log_level, logging.INFO)

    if settings.log_json:
        formatter: logging.Formatter = JsonLogFormatter(
            env=settings.env, app_name=settings.app_name, version=version
        )
    else:
        formatter = ConsoleLogFormatter(env=settings.env, app_name=settings.app_name)

    handler = logging.StreamHandler(target_stream)
    handler.setFormatter(formatter)
    setattr(handler, _MARKER_ATTR, True)

    root_logger = logging.getLogger()
    _replace_managed_handlers(root_logger, handler)
    root_logger.setLevel(level)

    # Harmonize uvicorn's own loggers onto the same handler/format instead of
    # letting them print their own default (non-JSON) access/error lines.
    for uvicorn_logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(uvicorn_logger_name)
        _replace_managed_handlers(uvicorn_logger, handler)
        uvicorn_logger.setLevel(level)
        uvicorn_logger.propagate = False


def _replace_managed_handlers(target_logger: logging.Logger, handler: logging.Handler) -> None:
    """Remove any handler this module previously installed, then add ``handler``."""
    for existing in list(target_logger.handlers):
        if getattr(existing, _MARKER_ATTR, False):
            target_logger.removeHandler(existing)
    target_logger.addHandler(handler)
