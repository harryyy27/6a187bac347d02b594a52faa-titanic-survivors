"""Application configuration loaded from environment variables.

Loads variables from a ``.env`` file (via python-dotenv) into the process
environment, then exposes them through a small, cached ``Settings`` object
so the rest of the application never has to touch ``os.environ`` directly.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _parse_allowed_hosts(raw: str) -> list[str]:
    return [host.strip() for host in raw.split(",") if host.strip()]


@dataclass(frozen=True)
class Settings:
    """Typed view over the environment variables the API depends on."""

    app_name: str = field(default_factory=lambda: os.environ.get("APP_NAME", "Titanic Survivors API"))
    env: str = field(default_factory=lambda: os.environ.get("ENV", "development"))
    log_level: str = field(default_factory=lambda: os.environ.get("LOG_LEVEL", "info"))
    secret_key: str = field(default_factory=lambda: os.environ.get("SECRET_KEY", "dev-secret-change-me"))
    model_path: str = field(default_factory=lambda: os.environ.get("MODEL_PATH", "./models/titanic_clf.joblib"))
    allowed_hosts: list[str] = field(
        default_factory=lambda: _parse_allowed_hosts(
            os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0")
        )
    )
    port: int = field(default_factory=lambda: int(os.environ.get("PORT", "8000")))


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide cached ``Settings`` singleton."""
    return Settings()
