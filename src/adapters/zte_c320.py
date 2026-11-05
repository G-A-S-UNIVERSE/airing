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

import asyncio

import logging
from typing import Any, Dict, List, Optional

from src.adapters.base import BaseOLTAdapter, OLTDevice, ONUDevice
from src.adapters._telnet import TelnetSession
from src.adapters.zte_parsers import (
    parse_onu_states,
    parse_onu_rx_power,
    extract_detail_info,
    parse_bulk_detail_info,
)

logger = logging.getLogger(__name__)


class ZteC320Adapter(BaseOLTAdapter):
    """Adapter for ZTE C320 OLT (CLI over Telnet).

    Methods implemented against real hardware:
      - get_onu_signal()   : queries downstream Rx power via CLI

    Methods still mocked (return static data):
      - list_olts()
      - list_onus()
      - reboot_onu()

    Set `offline=True` (default) for hermetic unit tests;
    set `offline=False` to talk to a real OLT.
    """

    vendor_key = "zte_c320"
    vendor_name = "ZTE C320"

    def __init__(
        self,
        host: str = "localhost",
        community: str = "public",
        snmp_version: str = "2c",
        timeout: int = 5,
        *,
        username: str | None = None,
        password: str | None = None,
        port: int = 23,
        prompt_marker: str = "ZXAN",
        offline: bool = True,
    ) -> None:
        super().__init__(
            host=host,
            community=community,
            snmp_version=snmp_version,
            timeout=timeout,
            port=port,
            offline=offline,
        )
        self.host = host
        self.community = community
        self.snmp_version = snmp_version
        self.timeout = timeout
        self.port = port
        self.prompt_marker = prompt_marker
        self.offline = offline
        # serial_number -> CLI identifier (e.g. '1/1/1:1'), populated by list_onus()
        self._serial_to_cli: dict[str, str] = {}
        # Credentials resolve at construction time from settings by default,
        # overridable per-instance for tests / multi-tenant use.
        from src.core.config import settings as _settings
        self.username = username if username is not None else _settings.TELNET_USERNAME
        self.password = password if password is not None else _settings.TELNET_PASSWORD

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
        """List ONUs under an OLT (optionally filtered by PON port).

        When `offline=True` (default), returns mock data for unit tests.
        When `offline=False`, uses the real ZTE C320 CLI:

          1. `show gpon onu state gpon-olt_<port>` — enumerate ONU indices
          2. `show gpon onu detail-info gpon-onu_<port>:<N>` — per-ONU detail

        Populates `self._serial_to_cli` so subsequent `get_onu_signal`
        calls can resolve a hardware serial to the CLI identifier.
        """
        if self.offline:
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

        # Accept both "gpon-olt_1/1/1" and "1/1/1" as input; normalize to board/port.
        raw = pon_port or "gpon-olt_1/1/1"
        # Extract the "1/1/1" portion
        import re as _re
        m = _re.search(r"(\d+/\d+/\d+)", raw)
        board_port = m.group(1) if m else "1/1/1"

        state_arg = f"gpon-olt_{board_port}"

        async with TelnetSession(
            self.host, self.port, paging_char=" ", paging_markers=("--More--",),
        ) as session:
            await session.login(
                self.username, self.password,
                username_prompt_markers=("Username:", "login:"),
                password_prompt_markers=("Password:",),
                post_login_markers=(self.prompt_marker,),
            )

            state_out = await session.run(
                f"show gpon onu state {state_arg}",
                prompt_markers=(self.prompt_marker,),
            )
            _grouped, working = parse_onu_states(state_out, onu_type="gpon")

            # Per-ONU detail query. Each response parses to one record.
            onus: List[ONUDevice] = []
            for idx, onu_idx in enumerate(working, start=1):
                onu_iface = f"gpon-onu_{board_port}:{onu_idx}"
                try:
                    detail_out = await session.run(
                        f"show gpon onu detail-info {onu_iface}",
                        prompt_markers=(self.prompt_marker,),
                    )
                except (asyncio.TimeoutError, ConnectionError):
                    # Network-level failure for this ONU — skip it, keep the rest.
                    # Do NOT use bare `except Exception` here: it would hide
                    # code bugs (NameError, AttributeError, etc.) as "no ONUs".
                    continue

                info = extract_detail_info(detail_out)
                serial = info["serial"]
                if serial != "N/A":
                    self._serial_to_cli[serial] = f"{board_port}:{onu_idx}"
                onus.append(ONUDevice(
                    id=f"zte-{serial}",
                    olt_id=olt_id,
                    pon_port=state_arg,
                    onu_index=int(onu_idx) if onu_idx.isdigit() else idx,
                    serial_number=serial,
                    status="online" if info["status"] == "Online" else "offline",
                    rx_power_dbm=None,
                    tx_power_dbm=None,
                    distance_m=None,
                    extra={
                        "name": info["name"],
                        "uptime": info["uptime"],
                        "downtime_cause": info["downtime_cause"],
                    },
                ))
        return onus
    async def get_onu_signal(self, olt_id: str, serial: str) -> Optional[Dict[str, float]]:
        """Query downstream Rx power via CLI (`show pon power attenuation`).

        `serial` may be either a hardware serial (e.g. "ZTEG-0000A1B2") or
        a CLI identifier (e.g. "1/1/1:1"). Hardware serials are resolved
        via the cache populated by `list_onus()`.

        When `offline=True` (default), returns a mock so unit tests stay
        hermetic. When `offline=False`, performs a real Telnet query.
        """
        if self.offline:
            return {"rx_power_dbm": -22.5, "tx_power_dbm": 2.1}

        # Resolve hardware serial -> CLI identifier via the cache populated
        # by list_onus(). Falls back to treating the input as a CLI ID when
        # it isn't in the cache (useful when the caller already knows it).
        onu_cli_id = self._serial_to_cli.get(serial, serial)

        async with TelnetSession(
            self.host,
            self.port,
            paging_char=" ",
            paging_markers=("--More--",),
        ) as session:
            await session.login(
                self.username,
                self.password,
                username_prompt_markers=("Username:", "login:"),
                password_prompt_markers=("Password:",),
                post_login_markers=(self.prompt_marker,),
            )
            output = await session.run(
                f"show pon power attenuation gpon-onu_{onu_cli_id}",
                prompt_markers=(self.prompt_marker,),
            )

        rx = parse_onu_rx_power(output)
        if rx is None:
            return None
        return {"rx_power_dbm": rx, "tx_power_dbm": 2.1}

    async def reboot_onu(self, olt_id: str, pon_port: str, onu_index: int) -> bool:
        """SNMP SET on `onuAdminStatus` to `reboot(2)`.

        OID example: 1.3.6.1.4.1.3902.1082.501.10.2.1.1.6.<pon>.<onu>
        """
        logger.info(
            f"[zte_c320] (mock) reboot olt={olt_id} port={pon_port} onu={onu_index}"
        )
        return True
