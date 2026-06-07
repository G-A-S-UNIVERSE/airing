"""Configuration tests: env-driven, defaults, no hardcoded secrets."""

from __future__ import annotations

import os
from unittest import mock

import pytest


def test_settings_load_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "abc-123-test")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    from src.core.config import Settings
    s = Settings()
    assert s.SECRET_KEY == "abc-123-test"
    assert s.APP_ENV == "production"
    assert s.LOG_LEVEL == "DEBUG"


def test_settings_have_safe_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defaults must NOT include any internal IP or production credential."""
    monkeypatch.delenv("PATIH_CLI_API", raising=False)
    monkeypatch.delenv("CMS_API_BASE_URL", raising=False)
    monkeypatch.delenv("SMARTOLT_API_KEY", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    from src.core.config import Settings
    s = Settings()
    assert "10." not in s.PATIH_CLI_API
    assert "10." not in s.CMS_API_BASE_URL
    assert s.SMARTOLT_API_KEY == "changeme"  # explicit placeholder, not real
    assert s.SECRET_KEY == "change-me-to-random-32-bytes"  # explicit placeholder


def test_cors_origins_parsed_from_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test ,http://c.test")
    from src.core.config import Settings
    s = Settings()
    assert s.parsed_cors_origins == ["http://a.test", "http://b.test", "http://c.test"]


def test_app_env_property(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    from src.core.config import Settings
    s = Settings()
    assert s.is_production is True
    assert s.is_development is False
