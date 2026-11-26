"""Verify /metrics returns Prometheus text format, not JSON-encoded string."""
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_metrics_is_prometheus_text_not_json() -> None:
    r = client.get("/metrics")
    assert r.status_code == 200
    ctype = r.headers.get("content-type", "")
    assert ctype.startswith("text/plain"), f"got {ctype!r}"


def test_metrics_body_has_no_json_quoting() -> None:
    r = client.get("/metrics")
    body = r.text
    assert body.startswith("# HELP"), body[:40]
    assert not body.startswith('"'), "metrics must not be JSON-encoded"
    assert "\\n" not in body, "metrics must contain real newlines, not escaped"
