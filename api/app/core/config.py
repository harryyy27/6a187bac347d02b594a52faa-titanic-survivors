"""Application configuration loaded from environment variables.

Loads variables from a ``.env`` file (via python-dotenv) into the process
environment, then exposes them through a validated, frozen ``AppSettings``
model so the rest of the application never has to touch ``os.environ``
directly.

Precedence: process environment variables > ``.env`` file values (loaded by
python-dotenv at import time, which never overrides a variable already
present in ``os.environ``) > the field defaults below.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

# Loaded once at import time, as early in process startup as possible.
# ``override=False`` (the default) means already-set environment variables
# always win over values found in the .env file.
load_dotenv()

logger = logging.getLogger("app.core.config")

# "test"/"testing" are accepted alongside the three primary runtime
# environments because the test harness's `.env.test` documents
# ``ENV=testing`` as the value used for automated test runs.
_VALID_ENVS = {"dev", "staging", "prod", "test", "testing"}
_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}
_TRUE_VALUES = {"1", "true", "yes", "on"}


def _parse_csv_list(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _is_valid_origin(origin: str) -> bool:
    """A CORS origin must be ``*`` or an absolute ``http(s)://host[:port]``."""
    if origin == "*":
        return True
    return origin.startswith("http://") or origin.startswith("https://")


def _as_bool(raw: str) -> bool:
    return raw.strip().lower() in _TRUE_VALUES


class AppSettings(BaseModel):
    """Centralized, validated application configuration."""

    model_config = {"frozen": True}

    # --- core service identity -------------------------------------------------
    env: str = Field(default="dev")
    app_name: str = Field(default="titanic-api")
    api_v1_prefix: str = Field(default="/api/v1")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)

    # --- logging -----------------------------------------------------------
    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=True)

    # --- CORS ----------------------------------------------------------------
    cors_allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    cors_allow_credentials: bool = Field(default=False)
    cors_allow_methods: list[str] = Field(default_factory=lambda: ["GET", "POST", "OPTIONS"])
    cors_allow_headers: list[str] = Field(default_factory=lambda: ["*"])

    # --- misc operational knobs ---------------------------------------------
    request_max_body_size: int = Field(default=2_000_000, ge=1)
    timeout_startup_ms: int = Field(default=15_000, ge=1)
    include_server_timing: bool = Field(default=True)
    trusted_proxies: list[str] = Field(default_factory=list)
    sentry_dsn: str | None = Field(default=None)

    # --- legacy fields (predate this feature; still relied upon by
    # app.ml.model and TrustedHostMiddleware) ---------------------------------
    secret_key: str = Field(default="dev-secret-change-me")
    model_path: str = Field(default="./models/titanic_clf.joblib")
    # "testserver" is the fixed Host header Starlette/FastAPI's TestClient
    # sends by default; allowing it here (harmless -- it never appears on a
    # real inbound connection) keeps TrustedHostMiddleware from rejecting
    # in-process test requests with 400 Invalid host header.
    allowed_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "0.0.0.0", "testserver"]
    )

    @field_validator("env")
    @classmethod
    def _validate_env(cls, value: str) -> str:
        if value not in _VALID_ENVS:
            raise ValueError(f"ENV must be one of {sorted(_VALID_ENVS)}, got {value!r}")
        return value

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        upper = value.upper()
        if upper not in _VALID_LOG_LEVELS:
            raise ValueError(f"LOG_LEVEL must be one of {sorted(_VALID_LOG_LEVELS)}, got {value!r}")
        return upper

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"


def _build_settings_from_env() -> AppSettings:
    """Read ``os.environ`` and materialize a validated ``AppSettings``.

    Only variables actually present in the environment are passed through,
    so unset variables fall back to the ``AppSettings`` field defaults
    rather than a hard-coded "unset" sentinel.
    """
    kwargs: dict[str, object] = {}

    _copy_if_set(kwargs, "env", "ENV")
    _copy_if_set(kwargs, "app_name", "APP_NAME")
    _copy_if_set(kwargs, "api_v1_prefix", "API_V1_PREFIX")
    _copy_if_set(kwargs, "host", "HOST")
    if "PORT" in os.environ:
        kwargs["port"] = int(os.environ["PORT"])
    _copy_if_set(kwargs, "log_level", "LOG_LEVEL")
    if "LOG_JSON" in os.environ:
        kwargs["log_json"] = _as_bool(os.environ["LOG_JSON"])

    cors_allow_credentials = _as_bool(os.environ["CORS_ALLOW_CREDENTIALS"]) if "CORS_ALLOW_CREDENTIALS" in os.environ else None

    if "CORS_ALLOW_ORIGINS" in os.environ:
        candidates = _parse_csv_list(os.environ["CORS_ALLOW_ORIGINS"])
        valid = [origin for origin in candidates if _is_valid_origin(origin)]
        invalid = [origin for origin in candidates if not _is_valid_origin(origin)]
        for origin in invalid:
            logger.warning(
                "config.cors_origin_invalid: ignoring malformed CORS_ALLOW_ORIGINS "
                "entry %r (expected '*' or an absolute http(s):// URL)",
                origin,
            )
        kwargs["cors_allow_origins"] = valid
        if not valid:
            logger.warning(
                "config.cors_origins_empty: no valid CORS origins configured; "
                "browser cross-origin requests from the web SPA will fail preflight."
            )

    if "CORS_ALLOW_METHODS" in os.environ:
        kwargs["cors_allow_methods"] = _parse_csv_list(os.environ["CORS_ALLOW_METHODS"])
    if "CORS_ALLOW_HEADERS" in os.environ:
        kwargs["cors_allow_headers"] = _parse_csv_list(os.environ["CORS_ALLOW_HEADERS"])
    if "REQUEST_MAX_BODY_SIZE" in os.environ:
        kwargs["request_max_body_size"] = int(os.environ["REQUEST_MAX_BODY_SIZE"])
    if "TIMEOUT_STARTUP_MS" in os.environ:
        kwargs["timeout_startup_ms"] = int(os.environ["TIMEOUT_STARTUP_MS"])
    if "INCLUDE_SERVER_TIMING" in os.environ:
        kwargs["include_server_timing"] = _as_bool(os.environ["INCLUDE_SERVER_TIMING"])
    if "TRUSTED_PROXIES" in os.environ:
        kwargs["trusted_proxies"] = _parse_csv_list(os.environ["TRUSTED_PROXIES"])
    if "SENTRY_DSN" in os.environ:
        kwargs["sentry_dsn"] = os.environ["SENTRY_DSN"] or None

    _copy_if_set(kwargs, "secret_key", "SECRET_KEY")
    _copy_if_set(kwargs, "model_path", "MODEL_PATH")
    if "ALLOWED_HOSTS" in os.environ:
        kwargs["allowed_hosts"] = _parse_csv_list(os.environ["ALLOWED_HOSTS"])

    origins = kwargs.get("cors_allow_origins")
    resolved_credentials = cors_allow_credentials if cors_allow_credentials is not None else False
    if origins is not None and "*" in origins and resolved_credentials:
        logger.warning(
            "config.cors_wildcard_credentials: CORS_ALLOW_ORIGINS contains '*' with "
            "credentials enabled, which Starlette disallows; forcing "
            "cors_allow_credentials=False."
        )
        resolved_credentials = False
    if cors_allow_credentials is not None or (origins is not None and "*" in origins):
        kwargs["cors_allow_credentials"] = resolved_credentials

    return AppSettings(**kwargs)


def _copy_if_set(kwargs: dict[str, object], field_name: str, env_var: str) -> None:
    if env_var in os.environ:
        kwargs[field_name] = os.environ[env_var]


@lru_cache
def get_settings() -> AppSettings:
    """Return the process-wide cached settings singleton."""
    return _build_settings_from_env()


def clear_settings_cache() -> None:
    """Clear the cached settings singleton (used by tests and hot-reload)."""
    get_settings.cache_clear()
