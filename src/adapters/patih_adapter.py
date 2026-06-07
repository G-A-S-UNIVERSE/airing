"""
AiRing - PATIH OLT Manager Adapter (sanitized reference)

PATIH is a local CLI/HTTP service that brokers commands to multiple
OLT vendors. This adapter shows how to talk to PATIH via its REST CLI
API. Public release returns mock data; production reads/writes go
through `httpx.AsyncClient`.

Configuration (via constructor or `src.core.config.settings`):
  - patih_cli_api:  str   (e.g. "http://localhost:8080/execute")
  - patih_timeout:  int   (seconds, default 30)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.adapters.base import BaseOLTAdapter, OLTDevice, ONUDevice

logger = logging.getLogger(__name__)


class PatihAdapter(BaseOLTAdapter):
    """Adapter for PATIH OLT Manager CLI commands."""

    vendor_key = "patih"
    vendor_name = "PATIH OLT Manager"

    def __init__(self, base_url: str = "http://localhost:8080/execute", timeout: int = 30) -> None:
        super().__init__(base_url=base_url, timeout=timeout)
        self.base_url = base_url
        self.timeout = timeout

    async def list_olts(self) -> List[OLTDevice]:
        """Return all OLTs brokered by PATIH. Public: returns mock data."""
        return [
            OLTDevice(
                id="patih-olt-1",
                name="OLT-C320-PAPUA-01",
                ip_address="10.0.0.1",
                vendor="zte",
                model="C320",
                status="online",
                uptime_seconds=864000,
                total_ports=16,
                online_ports=14,
                total_onus=256,
                online_onus=248,
            ),
        ]

    async def get_olt(self, olt_id: str) -> Optional[OLTDevice]:
        """Return a single OLT by PATIH-assigned ID."""
        for olt in await self.list_olts():
            if olt.id == olt_id:
                return olt
        return None

    async def list_onus(self, olt_id: str, pon_port: Optional[str] = None) -> List[ONUDevice]:
        """Return ONUs under an OLT, optionally filtered by PON port."""
        return [
            ONUDevice(
                id="patih-onu-1",
                olt_id=olt_id,
                pon_port=pon_port or "0/1/1",
                onu_index=1,
                serial_number="ZTEG-0000A1B2",
                status="online",
                rx_power_dbm=-22.5,
                tx_power_dbm=2.1,
                distance_m=850,
            ),
        ]

    async def get_onu_signal(self, olt_id: str, serial: str) -> Optional[Dict[str, float]]:
        """Return {'rx_power_dbm', 'tx_power_dbm'} for an ONU."""
        return {"rx_power_dbm": -22.5, "tx_power_dbm": 2.1}

    async def reboot_onu(self, olt_id: str, pon_port: str, onu_index: int) -> bool:
        """Trigger an ONU reboot via PATIH CLI."""
        logger.info(
            f"[patih] (mock) reboot olt={olt_id} port={pon_port} onu={onu_index}"
        )
        return True
