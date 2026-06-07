"""OLT vendor adapters (patih, zte_c320, huawei_ma5800, ...).

All adapters implement the `BaseOLTAdapter` interface. To add a new
vendor, subclass `BaseOLTAdapter` and register it in `ADAPTER_REGISTRY`.
See docs/ADAPTER_DEVELOPMENT.md for the full guide.
"""

from src.adapters.base import BaseOLTAdapter, OLTDevice, ONUDevice
from src.adapters.patih_adapter import PatihAdapter
from src.adapters.zte_c320 import ZteC320Adapter

__all__ = [
    "BaseOLTAdapter",
    "OLTDevice",
    "ONUDevice",
    "PatihAdapter",
    "ZteC320Adapter",
    "ADAPTER_REGISTRY",
    "get_adapter",
]


ADAPTER_REGISTRY: dict[str, type[BaseOLTAdapter]] = {
    "patih": PatihAdapter,
    "zte_c320": ZteC320Adapter,
}


def get_adapter(vendor: str) -> BaseOLTAdapter:
    """Factory: return a registered adapter instance by vendor key."""
    cls = ADAPTER_REGISTRY.get(vendor.lower())
    if not cls:
        raise ValueError(
            f"Unknown OLT vendor '{vendor}'. "
            f"Available: {sorted(ADAPTER_REGISTRY.keys())}"
        )
    return cls()
