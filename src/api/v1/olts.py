"""
AiRing - OLT Management Endpoints (public reference)

Public release uses in-memory mock data to demonstrate the API
contract. Production deployments swap `_FAKE_OLTS` for a SQLAlchemy
query via `Depends(get_db)` (see private repo for ORM models).
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


_FAKE_OLTS: List[Dict[str, Any]] = [
    {
        "id": str(uuid.uuid4()),
        "name": "OLT-C320-PAPUA-01",
        "ip_address": "10.0.0.1",
        "vendor": "zte",
        "model": "C320",
        "status": "online",
        "uptime_seconds": 864000,
        "total_ports": 16,
        "online_ports": 14,
        "total_onus": 256,
        "online_onus": 248,
    },
    {
        "id": str(uuid.uuid4()),
        "name": "OLT-MA5800-JKT-02",
        "ip_address": "10.0.0.2",
        "vendor": "huawei",
        "model": "MA5800-X7",
        "status": "online",
        "uptime_seconds": 1728000,
        "total_ports": 8,
        "online_ports": 8,
        "total_onus": 512,
        "online_onus": 502,
    },
]


@router.get("")
async def list_olts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    vendor: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """List all OLTs (paginated, filterable)."""
    items = _FAKE_OLTS
    if vendor:
        items = [o for o in items if o["vendor"] == vendor]
    if status:
        items = [o for o in items if o["status"] == status]
    total = len(items)
    page_items = items[skip : skip + limit]
    return {
        "items": page_items,
        "total": total,
        "page": skip // limit + 1 if limit else 1,
        "per_page": limit,
    }


@router.get("/{olt_id}")
async def get_olt(olt_id: str) -> Dict[str, Any]:
    """Get a single OLT by ID."""
    olt = next((o for o in _FAKE_OLTS if o["id"] == olt_id), None)
    if not olt:
        raise HTTPException(status_code=404, detail="OLT not found")
    return olt


@router.get("/{olt_id}/stats")
async def get_olt_stats(olt_id: str) -> Dict[str, Any]:
    """Get aggregated stats for an OLT (port + ONU health)."""
    olt = next((o for o in _FAKE_OLTS if o["id"] == olt_id), None)
    if not olt:
        raise HTTPException(status_code=404, detail="OLT not found")
    return {
        "olt_id": olt_id,
        "status": olt["status"],
        "total_ports": olt["total_ports"],
        "online_ports": olt["online_ports"],
        "total_onus": olt["total_onus"],
        "online_onus": olt["online_onus"],
        "offline_onus": olt["total_onus"] - olt["online_onus"],
    }
