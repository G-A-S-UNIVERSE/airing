"""Tests that /api/v1/olts serves data sourced via the adapter layer."""

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_list_olts_sources_data_from_adapter():
    """Verify /api/v1/olts reflects adapter output, not hardcoded fakes.

    The ZTE adapter mock returns name=f"ZTE-C320-{host}" with default
    host="localhost". The hardcoded fakes had names like
    "OLT-C320-PAPUA-01". If we see adapter-shaped names, the wiring works.
    """
    r = client.get("/api/v1/olts")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    names = [item["name"] for item in body["items"]]
    assert any("ZTE-C320-" in n for n in names), (
        f"Expected adapter-sourced name, got: {names}"
    )
    # The hardcoded fake names must NOT appear anymore
    assert "OLT-C320-PAPUA-01" not in names
    assert "OLT-MA5800-JKT-02" not in names
