"""Smoke tests: health, root, readiness."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_root_returns_app_metadata(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "AiRing"
    assert "version" in body
    assert body["env"] == "test"
    assert body["docs"] == "/docs"
    assert body["health"] == "/health"


def test_health_returns_ok(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["app"] == "AiRing"
    assert body["uptime_seconds"] >= 0


def test_readiness_reports_secret_key_loaded(client: TestClient) -> None:
    r = client.get("/health/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("ok", "degraded")
    assert "config" in body["checks"]
    assert body["checks"]["secret_key_loaded"] in ("ok", "default")


def test_metrics_endpoint_format(client: TestClient) -> None:
    r = client.get("/metrics")
    assert r.status_code == 200
    text = r.text
    assert "# HELP airing_alerts_total" in text
    assert "# TYPE airing_alerts_total counter" in text
    assert "airing_uptime_seconds" in text
