# Adapter Development Guide

This guide walks through adding a new OLT vendor adapter to AiRing.
The adapter pattern keeps vendor quirks isolated so adding (say) a
**Nokia 7360** ISAM should require no changes outside one new file
plus a registry entry.

## What an Adapter Is (and Isn't)

An adapter is a thin async wrapper around a vendor's management
protocol. It translates between vendor-native calls and AiRing's
neutral data model.

| It IS | It IS NOT |
|-------|-----------|
| Protocol-specific (SNMP/NETCONF/REST) | Business-logic (alert routing, RBAC) |
| Async by convention | Coupled to FastAPI |
| Self-contained (config via constructor) | A persistent connection pool |
| Returns typed dataclasses | Free to raise vendor exceptions |

## Step 1 — Subclass `BaseOLTAdapter`

```python
# src/adapters/nokia_7360.py
from src.adapters.base import BaseOLTAdapter, OLTDevice, ONUDevice
from typing import List, Optional, Dict, Any

class Nokia7360Adapter(BaseOLTAdapter):
    vendor_key = "nokia_7360"
    vendor_name = "Nokia 7360 ISAM FX"

    def __init__(self, host: str, community: str = "public", **kwargs):
        super().__init__(host=host, community=community, **kwargs)
        # vendor-specific client setup goes here
        ...
```

## Step 2 — Implement the Required Methods

| Method | Returns | Notes |
|--------|---------|-------|
| `list_olts()` | `List[OLTDevice]` | One entry per chassis this adapter manages. |
| `get_olt(olt_id)` | `Optional[OLTDevice]` | Lookup; `None` if not found. |
| `list_onus(olt_id, pon_port=None)` | `List[ONUDevice]` | Optional PON port filter. |
| `get_onu_signal(olt_id, serial)` | `Optional[Dict[str, float]]` | `{rx_power_dbm, tx_power_dbm}`. |
| `reboot_onu(olt_id, pon_port, onu_index)` | `bool` | True on success. |

Override `healthcheck()` only if you need a deeper probe (e.g. SNMP
GET on `sysUpTime`).

## Step 3 — Register the Adapter

```python
# src/adapters/__init__.py
from src.adapters.nokia_7360 import Nokia7360Adapter

ADAPTER_REGISTRY["nokia_7360"] = Nokia7360Adapter

__all__ = [..., "Nokia7360Adapter"]
```

`get_adapter("nokia_7360")` will now return an instance.

## Step 4 — Add Config to `Settings`

```python
# src/core/config.py
class Settings(BaseSettings):
    ...
    NOKIA_7360_SNMP_COMMUNITY: str = "public"
    NOKIA_7360_SNMP_VERSION: str = "2c"
```

Then read it in your adapter's constructor:

```python
from src.core.config import settings
class Nokia7360Adapter(BaseOLTAdapter):
    def __init__(self, host: str, **kwargs):
        super().__init__(
            host=host,
            community=settings.NOKIA_7360_SNMP_COMMUNITY,
            version=settings.NOKIA_7360_SNMP_VERSION,
            **kwargs,
        )
```

## Step 5 — Write Tests

Add `tests/test_nokia_7360.py`:

```python
import pytest
from src.adapters import get_adapter

@pytest.mark.asyncio
async def test_nokia_list_olts():
    adapter = get_adapter("nokia_7360")
    olts = await adapter.list_olts()
    assert len(olts) >= 1
    assert all(o.vendor == "nokia" for o in olts)
```

The test should run against mock data (the public reference
adapters in this repo are all mocked). For a real-hardware smoke
test, gate it behind a marker:

```python
@pytest.mark.integration
async def test_nokia_reboot_real_olt():
    ...  # requires NOKIA_7360_TEST_HOST env var
```

## Step 6 — Update `.env.example`

Append:

```
# Nokia 7360 ISAM
NOKIA_7360_SNMP_COMMUNITY=public
NOKIA_7360_SNMP_VERSION=2c
```

## Common Pitfalls

- **Don't leak the SNMP community string.** Either hash it for
  display, or omit it from the `OLTDevice.extra` dict.
  See `ZteC320Adapter` for a `community_hash_prefix` pattern.
- **Don't raise vendor-specific exceptions.** Wrap them in a
  generic `AdapterError` and let the API layer map to HTTP status.
- **Don't read env vars inside methods.** Inject everything through
  the constructor — makes unit testing trivial.
- **Don't block the event loop.** Use `asyncio.to_thread` around
  blocking SDK calls (paramiko, some SNMP clients).
- **Don't store mutable state on `self` for inventory.** The
  inventory belongs in the database; the adapter is a query
  translator, not a cache.

## Reference: Vendor-Specific Notes

| Vendor | Protocol | Library | Notes |
|--------|----------|---------|-------|
| ZTE C300/C320 | SNMPv2c + TELNET | `pysnmp` + `paramiko` | ZTE-OLT-PON-MIB |
| Huawei MA5800 | SNMPv3 + NETCONF | `pysnmp` + `ncclient` | HUAWEI-XPON-MIB |
| C-DATA / FD11xx | SNMPv2c + HTTP | `pysnmp` + `httpx` | Vendor MIB is partial |
| FiberHome AN5516 | SNMPv2c + TELNET | `pysnmp` + `paramiko` | FH-OLT-PON-MIB |
| Nokia 7360 ISAM | SNMPv2c + TL1 | `pysnmp` + custom TL1 | ISAM-MIB |

The public reference includes `PatihAdapter` (HTTP CLI bridge) and
`ZteC320Adapter` (SNMP) as worked examples.
