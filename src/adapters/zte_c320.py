"""
AiRing - ZTE C320 OLT Adapter (sanitized reference)

ZTE C320 is a mid-size FTTH OLT. Production adapters use SNMP
(pysnmp) or NETCONF to query chassis, PON ports, and ONUs.

This public reference shows the structure: methods map to vendor
MIBs / CLI commands. To wire to real hardware, replace `_mock_*`
methods with pysnmp GET/WALK calls (see `pysnmp.hlapi.v3arch.asyncio`).

Key ZTE C320 MIB references (production):
  - ZTE-OLT-PON-MIB
  - RFC 3635 (EtherLike-MIB)
  - IF-MIB (interface counters)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.adapters.base import BaseOLTAdapter, OLTDevice, ONUDevice
from src.adapters.zte_parsers import (
    parse_onu_states,
    parse_onu_rx_power,
    extract_detail_info,
)

logger = logging.getLogger(__name__)


class ZteC320Adapter(BaseOLTAdapter):
    """Adapter for ZTE C320 OLT (SNMP/NETCONF). Public: returns mock data."""

    vendor_key = "zte_c320"
    vendor_name = "ZTE C320"

    def __init__(
        self,
        host: str = "localhost",
        community: str = "public",
        snmp_version: str = "2c",
        timeout: int = 5,
    ) -> None:
        super().__init__(host=host, community=community, snmp_version=snmp_version, timeout=timeout)
        self.host = host
        self.community = community
        self.snmp_version = snmp_version
        self.timeout = timeout

    async def list_olts(self) -> List[OLTDevice]:
        """Return ZTE C320 OLTs reachable via SNMP. Public: returns mock data."""
        return [
            OLTDevice(
                id="zte-c320-1",
                name=f"ZTE-C320-{self.host}",
                ip_address=self.host,
                vendor="zte",
                model="C320",
                status="online",
                uptime_seconds=864000,
                total_ports=16,
                online_ports=14,
                total_onus=256,
                online_onus=248,
                extra={"snmp_version": self.snmp_version, "community_hash_prefix": self.community[:2] + "***"},
            ),
        ]

    async def get_olt(self, olt_id: str) -> Optional[OLTDevice]:
        for olt in await self.list_olts():
            if olt.id == olt_id:
                return olt
        return None

    async def list_onus(self, olt_id: str, pon_port: Optional[str] = None) -> List[ONUDevice]:
        """Walk `ZTE-OLT-PON-MIB::onuTable` and decode entries."""
        return [
            ONUDevice(
                id="zte-onu-1",
                olt_id=olt_id,
                pon_port=pon_port or "0/1/1",
                onu_index=1,
                serial_number="ZTEG-0000A1B2",
                status="online",
                rx_power_dbm=-22.5,
                tx_power_dbm=2.1,
                distance_m=850,
            ),
            ONUDevice(
                id="zte-onu-2",
                olt_id=olt_id,
                pon_port=pon_port or "0/1/1",
                onu_index=2,
                serial_number="ZTEG-0000A1B3",
                status="offline",
                rx_power_dbm=None,
                tx_power_dbm=None,
                distance_m=None,
            ),
        ]

    async def get_onu_signal(self, olt_id: str, serial: str) -> Optional[Dict[str, float]]:
        """SNMP GET on `onuRxOpticalPower` and `onuTxOpticalPower`."""
        return {"rx_power_dbm": -22.5, "tx_power_dbm": 2.1}

    async def reboot_onu(self, olt_id: str, pon_port: str, onu_index: int) -> bool:
        """SNMP SET on `onuAdminStatus` to `reboot(2)`.

        OID example: 1.3.6.1.4.1.3902.1082.501.10.2.1.1.6.<pon>.<onu>
        """
        logger.info(
            f"[zte_c320] (mock) reboot olt={olt_id} port={pon_port} onu={onu_index}"
        )
        return True
