"""
AiRing - ONU (Optical Network Unit) Endpoints (public reference)

Public release uses in-memory mock data. Production: replace with
SQLAlchemy queries against the `onus` table (see private repo).
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


_FAKE_ONUS: List[Dict[str, Any]] = [
    {
        "id": str(uuid.uuid4()),
        "olt_id": "olt-c320-papua-01",
        "pon_port": "0/1/1",
        "onu_index": 1,
        "serial_number": "ZTEG-0000A1B2",
        "status": "online",
        "rx_power_dbm": -22.5,
        "tx_power_dbm": 2.1,
        "distance_m": 850,
    },
    {
        "id": str(uuid.uuid4()),
        "olt_id": "olt-c320-papua-01",
        "pon_port": "0/1/1",
        "onu_index": 2,
        "serial_number": "ZTEG-0000A1B3",
        "status": "offline",
        "rx_power_dbm": None,
        "tx_power_dbm": None,
        "distance_m": None,
    },
    {
        "id": str(uuid.uuid4()),
        "olt_id": "olt-ma5800-jkt-02",
        "pon_port": "0/1/0",
        "onu_index": 1,
        "serial_number": "HWTC-1234ABCD",
        "status": "online",
        "rx_power_dbm": -19.8,
        "tx_power_dbm": 2.3,
        "distance_m": 420,
    },
]


@router.get("")
async def list_onus(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    olt_id: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """List all ONUs (paginated, filterable by OLT + status)."""
    items = _FAKE_ONUS
    if olt_id:
        items = [u for u in items if u["olt_id"] == olt_id]
    if status:
        items = [u for u in items if u["status"] == status]
    total = len(items)
    return {
        "items": items[skip : skip + limit],
        "total": total,
        "page": skip // limit + 1 if limit else 1,
        "per_page": limit,
    }


@router.get("/{onu_id}")
async def get_onu(onu_id: str) -> Dict[str, Any]:
    """Get a single ONU by ID."""
    onu = next((u for u in _FAKE_ONUS if u["id"] == onu_id), None)
    if not onu:
        raise HTTPException(status_code=404, detail="ONU not found")
    return onu


@router.post("/{onu_id}/reboot")
async def reboot_onu(onu_id: str) -> Dict[str, Any]:
    """Trigger an ONU reboot (mock; production: call adapter)."""
    onu = next((u for u in _FAKE_ONUS if u["id"] == onu_id), None)
    if not onu:
        raise HTTPException(status_code=404, detail="ONU not found")
    return {
        "onu_id": onu_id,
        "action": "reboot",
        "status": "queued",
        "adapter": onu["olt_id"].split("-")[0] if "-" in onu["olt_id"] else "generic",
    }
