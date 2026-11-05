"""
AiRing - OLT Management Endpoints (adapter-backed)

Routes through the adapter layer. The ZTE adapter is still mock-data
internally when `offline=True` (the default), so the response reflects
mock hardware — but the wiring is the real pattern.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from src.adapters import get_adapter
from src.adapters.base import OLTDevice

router = APIRouter()


def _serialize(olt: OLTDevice) -> Dict[str, Any]:
    return {
        "id": olt.id,
        "name": olt.name,
        "ip_address": olt.ip_address,
        "vendor": olt.vendor,
        "model": olt.model,
        "status": olt.status,
        "uptime_seconds": olt.uptime_seconds,
        "total_ports": olt.total_ports,
        "online_ports": olt.online_ports,
        "total_onus": olt.total_onus,
        "online_onus": olt.online_onus,
    }


def _adapter():
    """Factory indirection so tests can override the vendor choice."""
    return get_adapter("zte_c320")


@router.get("")
async def list_olts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    vendor: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    adapter = _adapter()
    olts = await adapter.list_olts()

    items: List[Dict[str, Any]] = [_serialize(o) for o in olts]
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
    adapter = _adapter()
    olt = await adapter.get_olt(olt_id)
    if not olt:
        raise HTTPException(status_code=404, detail="OLT not found")
    return _serialize(olt)


@router.get("/{olt_id}/stats")
async def get_olt_stats(olt_id: str) -> Dict[str, Any]:
    adapter = _adapter()
    olt = await adapter.get_olt(olt_id)
    if not olt:
        raise HTTPException(status_code=404, detail="OLT not found")
    return {
        "olt_id": olt_id,
        "status": olt.status,
        "total_ports": olt.total_ports,
        "online_ports": olt.online_ports,
        "total_onus": olt.total_onus,
        "online_onus": olt.online_onus,
        "offline_onus": olt.total_onus - olt.online_onus,
    }
