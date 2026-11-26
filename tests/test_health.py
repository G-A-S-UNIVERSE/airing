"""Health endpoint tests — verifies secret_key_loaded visibility."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.core.config import get_settings
from src.main import app

client = TestClient(app)


def _clear_settings_cache():
    """Invalidate the get_settings() lru_cache so new env vars take effect."""
    get_settings.cache_clear()


def test_health_reports_ok():
    _clear_settings_cache()
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["app"] == "AiRing"


def test_health_reports_secret_key_loaded_default(monkeypatch):
    """With placeholder SECRET_KEY, /health must report 'default'."""
    monkeypatch.setenv("SECRET_KEY", "change-me-to-random-32-bytes")
    _clear_settings_cache()
    body = client.get("/health").json()
    assert "secret_key_loaded" in body, body
    assert body["secret_key_loaded"] == "default"


def test_health_reports_secret_key_loaded_custom(monkeypatch):
    """With a real SECRET_KEY, /health must report 'custom'."""
    monkeypatch.setenv("SECRET_KEY", "real-secret-value")
    _clear_settings_cache()
    body = client.get("/health").json()
    assert body["secret_key_loaded"] == "custom"
