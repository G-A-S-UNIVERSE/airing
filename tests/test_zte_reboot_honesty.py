import pytest
from src.adapters.zte_c320 import ZteC320Adapter


@pytest.mark.asyncio
async def test_reboot_offline_returns_false_not_true():
    """Offline mode must not claim success."""
    a = ZteC320Adapter(offline=True)
    assert await a.reboot_onu("x", "0/1/1", 1) is False


@pytest.mark.asyncio
async def test_reboot_online_raises_not_implemented():
    """Online mode must fail loudly until real SNMP is wired."""
    a = ZteC320Adapter(offline=False)
    with pytest.raises(NotImplementedError):
        await a.reboot_onu("x", "0/1/1", 1)
