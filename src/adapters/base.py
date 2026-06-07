"""
AiRing - OLT Adapter Base Interface (public reference)

Defines the contract every vendor adapter must implement. The adapter
pattern lets AiRing orchestrate heterogeneous OLTs (ZTE C320, Huawei
MA5800, C-DATA, FiberHome, etc.) through a single, uniform API.

Key design rules:
  - All adapters are async (long-running network calls).
  - All adapters return typed dataclasses, not raw vendor payloads.
  - No vendor-specific exception types leak out of an adapter.
  - Configuration is injected via constructor; no env reads inside methods.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class OLTDevice:
    """A managed OLT chassis."""

    id: str
    name: str
    ip_address: str
    vendor: str
    model: str
    status: str = "unknown"
    uptime_seconds: int = 0
    total_ports: int = 0
    online_ports: int = 0
    total_onus: int = 0
    online_onus: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ONUDevice:
    """An ONU (customer premises equipment) attached to an OLT PON port."""

    id: str
    olt_id: str
    pon_port: str
    onu_index: int
    serial_number: str
    status: str = "unknown"
    rx_power_dbm: Optional[float] = None
    tx_power_dbm: Optional[float] = None
    distance_m: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


class BaseOLTAdapter(ABC):
    """Abstract base class for all OLT vendor adapters."""

    vendor_key: str = ""  # subclass MUST set (e.g. "zte_c320")
    vendor_name: str = ""  # subclass MUST set (e.g. "ZTE C320")

    def __init__(self, **config: Any) -> None:
        self.config = config

    @abstractmethod
    async def list_olts(self) -> List[OLTDevice]:
        """Return all OLTs this adapter can manage."""

    @abstractmethod
    async def get_olt(self, olt_id: str) -> Optional[OLTDevice]:
        """Return a single OLT by its adapter-specific ID, or None."""

    @abstractmethod
    async def list_onus(self, olt_id: str, pon_port: Optional[str] = None) -> List[ONUDevice]:
        """Return ONUs under an OLT, optionally filtered by PON port."""

    @abstractmethod
    async def get_onu_signal(self, olt_id: str, serial: str) -> Optional[Dict[str, float]]:
        """Return {'rx_power_dbm': float, 'tx_power_dbm': float} or None."""

    @abstractmethod
    async def reboot_onu(self, olt_id: str, pon_port: str, onu_index: int) -> bool:
        """Trigger an ONU reboot. Return True on success."""

    async def healthcheck(self) -> Dict[str, Any]:
        """Default healthcheck: just confirm adapter loads."""
        return {
            "vendor": self.vendor_key,
            "name": self.vendor_name,
            "status": "loaded",
            "config_keys": sorted(self.config.keys()),
        }
