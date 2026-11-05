"""Configuration tests: env-driven, defaults, no hardcoded secrets."""

from __future__ import annotations

import os
from unittest import mock

import pytest


def test_settings_load_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "abc-123-test")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    # Production now requires all secrets be set (see _reject_placeholder_secrets_in_prod)
    monkeypatch.setenv("TELNET_PASSWORD", "real-telnet-password")
    monkeypatch.setenv("CMS_API_TOKEN", "real-cms-token")
    monkeypatch.setenv("SMARTOLT_API_KEY", "real-smartolt-key")
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
    monkeypatch.setenv("SECRET_KEY", "real-secret-value")
    # Production now requires all secrets be set
    monkeypatch.setenv("TELNET_PASSWORD", "real-telnet-password")
    monkeypatch.setenv("CMS_API_TOKEN", "real-cms-token")
    monkeypatch.setenv("SMARTOLT_API_KEY", "real-smartolt-key")
    from src.core.config import Settings
    s = Settings()
    assert s.is_production is True
    assert s.is_development is False


# --- Production fail-loud checks (Step A) ---

def test_production_rejects_placeholder_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "change-me-to-random-32-bytes")
    from src.core.config import Settings
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings()


def test_production_rejects_placeholder_telnet_password(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "real-secret-32-bytes-of-entropy-here")
    monkeypatch.setenv("TELNET_PASSWORD", "changeme")
    from src.core.config import Settings
    with pytest.raises(ValueError, match="TELNET_PASSWORD"):
        Settings()


def test_production_accepts_real_secrets(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "a" * 43)
    monkeypatch.setenv("TELNET_PASSWORD", "real-telnet-password")
    monkeypatch.setenv("CMS_API_TOKEN", "real-cms-token")
    monkeypatch.setenv("SMARTOLT_API_KEY", "real-smartolt-key")
    from src.core.config import Settings
    s = Settings()  # must not raise
    assert s.is_production is True


def test_development_allows_placeholders(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    from src.core.config import Settings
    s = Settings()
    assert s.SECRET_KEY.startswith("change-me")
