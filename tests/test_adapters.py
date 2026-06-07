"""Adapter pattern tests: registry, base contract, vendor implementations."""

from __future__ import annotations

import pytest

from src.adapters import (
    ADAPTER_REGISTRY,
    BaseOLTAdapter,
    OLTDevice,
    ONUDevice,
    PatihAdapter,
    ZteC320Adapter,
    get_adapter,
)


def test_registry_contains_expected_vendors() -> None:
    assert "patih" in ADAPTER_REGISTRY
    assert "zte_c320" in ADAPTER_REGISTRY


def test_factory_raises_for_unknown_vendor() -> None:
    with pytest.raises(ValueError, match="Unknown OLT vendor"):
        get_adapter("nokia_7360")


def test_factory_returns_subclass_of_base() -> None:
    adapter = get_adapter("zte_c320")
    assert isinstance(adapter, BaseOLTAdapter)
    assert adapter.vendor_key == "zte_c320"
    assert adapter.vendor_name == "ZTE C320"


@pytest.mark.asyncio
async def test_patih_returns_at_least_one_olt() -> None:
    adapter = PatihAdapter()
    olts = await adapter.list_olts()
    assert len(olts) >= 1
    assert all(isinstance(o, OLTDevice) for o in olts)
    assert all(o.vendor == "zte" for o in olts)


@pytest.mark.asyncio
async def test_zte_c320_list_olts_includes_community_hash_prefix() -> None:
    """Production: ensure community string is never logged in cleartext."""
    adapter = ZteC320Adapter(community="private_xyz")
    olts = await adapter.list_olts()
    assert len(olts) >= 1
    extra = olts[0].extra
    assert "community_hash_prefix" in extra
    assert "private_xyz" not in extra["community_hash_prefix"]


@pytest.mark.asyncio
async def test_patih_signal_returns_dict() -> None:
    adapter = PatihAdapter()
    signal = await adapter.get_onu_signal("olt-1", "ZTEG-0000A1B2")
    assert signal is not None
    assert "rx_power_dbm" in signal
    assert "tx_power_dbm" in signal
    assert -30.0 <= signal["rx_power_dbm"] <= 5.0


@pytest.mark.asyncio
async def test_reboot_returns_bool() -> None:
    adapter = ZteC320Adapter()
    result = await adapter.reboot_onu("olt-1", "0/1/1", 1)
    assert isinstance(result, bool)
    assert result is True


@pytest.mark.asyncio
async def test_healthcheck_default() -> None:
    adapter = get_adapter("patih")
    health = await adapter.healthcheck()
    assert health["vendor"] == "patih"
    assert health["status"] == "loaded"
