"""Unit tests for app.core.config.AppSettings / get_settings.

Covers: env-var driven overrides, validation of ENV/LOG_LEVEL, invalid CORS
origins being dropped (with a warning) rather than raising, and the
wildcard-origin + credentials restriction being enforced automatically.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.testWrapperTimeout import testWrapperTimeout  # noqa: E402

from app.core.config import (  # noqa: E402
    AppSettings,
    _build_settings_from_env,
    clear_settings_cache,
    get_settings,
)


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    clear_settings_cache()


@testWrapperTimeout
def test_defaults_used_when_no_env_vars_set(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("ENV", "APP_NAME", "PORT", "LOG_LEVEL", "CORS_ALLOW_ORIGINS"):
        monkeypatch.delenv(var, raising=False)

    settings = _build_settings_from_env()

    assert settings.env == "dev"
    assert settings.app_name == "titanic-api"
    assert settings.port == 8000
    assert settings.log_level == "INFO"
    assert settings.cors_allow_origins == ["http://localhost:5173"]


@testWrapperTimeout
def test_env_var_overrides_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "staging")
    monkeypatch.setenv("APP_NAME", "custom-api")
    monkeypatch.setenv("PORT", "9090")

    settings = _build_settings_from_env()

    assert settings.env == "staging"
    assert settings.app_name == "custom-api"
    assert settings.port == 9090


@testWrapperTimeout
def test_get_settings_is_cached_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "cached-api")
    first = get_settings()
    monkeypatch.setenv("APP_NAME", "changed-after-first-call")
    second = get_settings()

    assert first is second
    assert second.app_name == "cached-api"


@testWrapperTimeout
def test_invalid_env_raises_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "not-a-real-environment")

    with pytest.raises(ValidationError):
        _build_settings_from_env()


@testWrapperTimeout
def test_invalid_log_level_raises_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "VERY_LOUD")

    with pytest.raises(ValidationError):
        _build_settings_from_env()


@testWrapperTimeout
def test_log_level_is_case_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "debug")

    settings = _build_settings_from_env()

    assert settings.log_level == "DEBUG"


@testWrapperTimeout
def test_invalid_cors_origin_is_dropped_and_warned(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv(
        "CORS_ALLOW_ORIGINS", "http://localhost:5173, not-a-valid-origin, https://app.example.com"
    )

    with caplog.at_level(logging.WARNING, logger="app.core.config"):
        settings = _build_settings_from_env()

    assert settings.cors_allow_origins == ["http://localhost:5173", "https://app.example.com"]
    assert any("not-a-valid-origin" in record.message for record in caplog.records)


@testWrapperTimeout
def test_all_cors_origins_invalid_yields_empty_list_and_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "not-valid, also not valid")

    with caplog.at_level(logging.WARNING, logger="app.core.config"):
        settings = _build_settings_from_env()

    assert settings.cors_allow_origins == []
    assert any("cors_origins_empty" in record.message for record in caplog.records)


@testWrapperTimeout
def test_wildcard_origin_forces_credentials_false(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "*")
    monkeypatch.setenv("CORS_ALLOW_CREDENTIALS", "true")

    with caplog.at_level(logging.WARNING, logger="app.core.config"):
        settings = _build_settings_from_env()

    assert settings.cors_allow_origins == ["*"]
    assert settings.cors_allow_credentials is False
    assert any("cors_wildcard_credentials" in record.message for record in caplog.records)


@testWrapperTimeout
def test_non_wildcard_origin_respects_credentials_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("CORS_ALLOW_CREDENTIALS", "true")

    settings = _build_settings_from_env()

    assert settings.cors_allow_credentials is True


@testWrapperTimeout
def test_testing_env_value_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    """`.env.test` documents ENV=testing; the validator must accept it."""
    monkeypatch.setenv("ENV", "testing")

    settings = _build_settings_from_env()

    assert settings.env == "testing"


@testWrapperTimeout
def test_settings_object_is_frozen() -> None:
    settings = AppSettings()

    with pytest.raises(ValidationError):
        settings.app_name = "mutated"  # type: ignore[misc]


@testWrapperTimeout
def test_legacy_fields_still_present_for_backward_compat(monkeypatch: pytest.MonkeyPatch) -> None:
    """app.ml.model and main.py's TrustedHostMiddleware depend on these."""
    monkeypatch.setenv("MODEL_PATH", "/tmp/custom-model.joblib")
    monkeypatch.setenv("ALLOWED_HOSTS", "example.com,api.example.com")

    settings = _build_settings_from_env()

    assert settings.model_path == "/tmp/custom-model.joblib"
    assert settings.allowed_hosts == ["example.com", "api.example.com"]
    assert "testserver" in AppSettings().allowed_hosts
