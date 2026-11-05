"""Unit tests for ZTE CLI output parsers.

These parsers are extracted from the original Streamlit monitor script
and ported verbatim (same regexes, same fallbacks). They operate on
recorded sample output, never a live OLT.
"""

from __future__ import annotations

import pytest

from src.adapters.zte_parsers import (
    parse_onu_states,
    parse_onu_rx_power,
    extract_detail_info,
)


# --- Fixtures: recorded sample output (synthetic; same shape as real) ---

SAMPLE_STATE_OUTPUT = """\
  ONU    Admin    OMCC     Phase
  ID     State    State    State
------- -------- -------- --------
0/1/1:1  enable   enable   working
0/1/1:2  enable   enable   working
0/1/1:3  enable   enable   offline
0/1/1:4  enable   enable   working
0/1/1:5  disable  disable  offline
"""

SAMPLE_ATTENUATION_OUTPUT = """\
OLT: 1/1/1:1
ONU: 1/1/1:1
    Down    Tx : 2.48(dbm)    Rx : -22.53(dbm)
    Up      Tx : -23.10(dbm)  Rx : 2.10(dbm)
"""

SAMPLE_DETAIL_INFO_OUTPUT = """\
OLT: 1/1/1
ONU ID: 1
Admin State: enable
Phase state: Working
Name: john_doe
Serial number: ZTEG-0000A1B2
Online Duration: 5d 4h 23m 12s
Authpass Time: 2024-01-01 12:00:00
"""

SAMPLE_DETAIL_INFO_OFFLINE = """\
OLT: 1/1/1
ONU ID: 3
Phase state: Offline
Name: jane_doe
Serial number: ZTEG-0000A1B3
Online Duration: N/A
Authpass Time          OfflineTime               Cause
2024-01-01 12:00:00    2024-01-02 14:30:15      dying-gasp
"""


# --- Tests ---

def test_parse_onu_states_identifies_working_and_offline():
    grouped, working = parse_onu_states(SAMPLE_STATE_OUTPUT, onu_type="gpon")
    assert "1" in working
    assert "2" in working
    assert "4" in working
    assert "3" not in working
    assert "5" not in working
    # offline group contains the ones not working
    offline_ids = {x for ids in grouped.values() for x in ids}
    assert "3" in offline_ids
    assert "5" in offline_ids


def test_parse_onu_rx_power_extracts_float():
    rx = parse_onu_rx_power(SAMPLE_ATTENUATION_OUTPUT)
    assert rx is not None
    assert rx == pytest.approx(-22.53, abs=0.01)


def test_parse_onu_rx_power_returns_none_for_garbage():
    assert parse_onu_rx_power("random output") is None


def test_extract_detail_info_online():
    info = extract_detail_info(SAMPLE_DETAIL_INFO_OUTPUT)
    assert info["name"] == "john_doe"
    assert info["serial"] == "ZTEG-0000A1B2"
    assert info["status"] == "Online"
    assert "5d" in info["uptime"]


def test_extract_detail_info_offline_captures_cause():
    info = extract_detail_info(SAMPLE_DETAIL_INFO_OFFLINE)
    assert info["serial"] == "ZTEG-0000A1B3"
    assert info["status"].lower() != "online"
    # cause must be extracted from history table
    assert "dying-gasp" in info["downtime_cause"].lower() or info["downtime_cause"] == "N/A"


# --- Integration: adapter.get_onu_signal() uses Telnet when offline=False ---

@pytest.mark.asyncio
async def test_get_onu_signal_uses_telnet_when_offline_false(monkeypatch):
    """Adapter must call TelnetSession and parse the Rx power."""
    from src.adapters import zte_c320

    async def fake_connect(self):
        pass

    async def fake_close(self):
        pass

    async def fake_login(self, user, pw, **kw):
        # Adapter passes username_prompt_markers etc. as kwargs — accept them.
        pass

    async def fake_run(self, command, *, prompt_markers, timeout=None):
        assert "show pon power attenuation" in command
        assert "gpon-onu_1/1/1:1" in command, command
        return SAMPLE_ATTENUATION_OUTPUT

    monkeypatch.setattr(zte_c320.TelnetSession, "connect", fake_connect)
    monkeypatch.setattr(zte_c320.TelnetSession, "close", fake_close)
    monkeypatch.setattr(zte_c320.TelnetSession, "login", fake_login)
    monkeypatch.setattr(zte_c320.TelnetSession, "run", fake_run)

    adapter = zte_c320.ZteC320Adapter(
        host="10.42.0.11",
        username="force_ghost",
        password="may_the_force_be_with_you",
        offline=False,
    )
    signal = await adapter.get_onu_signal("olt-1", "1/1/1:1")
    assert signal is not None
    assert signal["rx_power_dbm"] == pytest.approx(-22.53, abs=0.01)


@pytest.mark.asyncio
async def test_get_onu_signal_still_uses_mock_when_offline_true():
    """Default offline=True must keep the mock path for hermetic tests."""
    from src.adapters.zte_c320 import ZteC320Adapter

    adapter = ZteC320Adapter()  # offline defaults to True
    signal = await adapter.get_onu_signal("olt-1", "1/1/1:1")
    assert signal == {"rx_power_dbm": -22.5, "tx_power_dbm": 2.1}


# --- parse_bulk_detail_info (C.1) ---

SAMPLE_DETAIL_INFO_BULK = """\
OLT: 1/1/1
ONU ID: 1
Phase state: Working
Name: john_doe
Serial number: ZTEG-0000A1B2
Online Duration: 5d 4h 23m 12s

OLT: 1/1/1
ONU ID: 2
Phase state: Working
Name: jane_doe
Serial number: ZTEG-0000A1B3
Online Duration: 2d 11h 5m 44s

OLT: 1/1/1
ONU ID: 3
Phase state: Offline
Name: offline_user
Serial number: ZTEG-0000A1B4
Online Duration: N/A
"""


def test_parse_bulk_detail_info_splits_records():
    from src.adapters.zte_parsers import parse_bulk_detail_info
    records = parse_bulk_detail_info(SAMPLE_DETAIL_INFO_BULK)
    assert len(records) == 3
    by_serial = {r["serial"]: r for r in records}
    assert "ZTEG-0000A1B2" in by_serial
    assert by_serial["ZTEG-0000A1B2"]["name"] == "john_doe"
    assert by_serial["ZTEG-0000A1B2"]["status"] == "Online"
    assert by_serial["ZTEG-0000A1B4"]["status"].lower() != "online"


def test_parse_bulk_detail_info_handles_empty():
    from src.adapters.zte_parsers import parse_bulk_detail_info
    assert parse_bulk_detail_info("") == []


def test_parse_bulk_detail_info_single_record():
    from src.adapters.zte_parsers import parse_bulk_detail_info
    single = """\
OLT: 1/1/1
ONU ID: 1
Phase state: Working
Name: solo
Serial number: ZTEG-SOLO
Online Duration: 1d
"""
    records = parse_bulk_detail_info(single)
    assert len(records) == 1
    assert records[0]["serial"] == "ZTEG-SOLO"


# --- list_onus + serial→cli cache (C.2) ---

@pytest.mark.asyncio
async def test_list_onus_populates_serial_to_cli(monkeypatch):
    """list_onus(offline=False) runs state + per-ONU detail and caches serial→cli.

    Fixture data is synthetic. The command grammar and output shape match
    real ZTE C320 hardware (validated against live OLTs), but serials and
    subscriber names here are fictional.
    """
    from src.adapters import zte_c320

    state_output = (
        "OnuIndex   Admin State  OMCC State  Phase State  Channel    \n"
        "--------------------------------------------------------------\n"
        "1/1/1:1     enable       disable     OffLine      1(GPON)\n"
        "1/1/1:2     enable       disable     OffLine      1(GPON)\n"
        "1/1/1:3     enable       disable     DyingGasp    1(GPON)\n"
        "1/1/1:4     enable       enable      working      1(GPON)\n"
        "1/1/1:5     enable       disable     OffLine      1(GPON)\n"
        "1/1/1:6     enable       enable      working      1(GPON)\n"
        "1/1/1:12    enable       enable      working      1(GPON)\n"
        "ONU Number: 3/12       \n"
        "ZXAN#\n"
    )

    detail_by_onu = {
        "1/1/1:4": (
            "\nONU interface:         gpon-onu_1/1/1:4\n"
            "  Name:                tatooine_user_1\n"
            "  Phase state:         working\n"
            "  Serial number:       ZTEGAAAA0004\n"
            "  Online Duration:     1h 45m 53s\n"
            "ZXAN#\n"
        ),
        "1/1/1:6": (
            "\nONU interface:         gpon-onu_1/1/1:6\n"
            "  Name:                coruscant_user_2\n"
            "  Phase state:         working\n"
            "  Serial number:       ZTEGAAAA0006\n"
            "  Online Duration:     2h 15m 30s\n"
            "ZXAN#\n"
        ),
        "1/1/1:12": (
            "\nONU interface:         gpon-onu_1/1/1:12\n"
            "  Name:                mandalore_user_3\n"
            "  Phase state:         working\n"
            "  Serial number:       ZTEGAAAA0012\n"
            "  Online Duration:     45m 12s\n"
            "ZXAN#\n"
        ),
    }

    commands_seen = []

    async def fake_connect(self): pass
    async def fake_close(self): pass
    async def fake_login(self, user, pw, **kw): pass
    async def fake_run(self, command, *, prompt_markers, timeout=None):
        commands_seen.append(command)
        if "onu state" in command:
            return state_output
        if "detail-info" in command:
            m = re.search(r"gpon-onu_(\d+/\d+/\d+:\d+)", command)
            if m and m.group(1) in detail_by_onu:
                return detail_by_onu[m.group(1)]
            return "\n%Error 20202: Invalid input\nZXAN#\n"
        return "\nZXAN#\n"

    monkeypatch.setattr(zte_c320.TelnetSession, "connect", fake_connect)
    monkeypatch.setattr(zte_c320.TelnetSession, "close", fake_close)
    monkeypatch.setattr(zte_c320.TelnetSession, "login", fake_login)
    monkeypatch.setattr(zte_c320.TelnetSession, "run", fake_run)

    adapter = zte_c320.ZteC320Adapter(
        host="10.42.0.11", username="u", password="p", offline=False,
    )
    onus = await adapter.list_onus("olt-1", pon_port="gpon-olt_1/1/1")
    assert len(onus) == 3, f"expected 3, got {len(onus)}"
    serials = {o.serial_number for o in onus}
    assert "ZTEGAAAA0004" in serials

    assert adapter._serial_to_cli["ZTEGAAAA0004"] == "1/1/1:4"
    assert adapter._serial_to_cli["ZTEGAAAA0006"] == "1/1/1:6"

    detail_cmds = [c for c in commands_seen if "detail-info" in c]
    assert len(detail_cmds) == 3
    assert all("gpon-onu_1/1/1:" in c for c in detail_cmds)


@pytest.mark.asyncio
async def test_list_onus_offline_returns_mock():
    """Default offline=True keeps the mock path hermetic."""
    from src.adapters.zte_c320 import ZteC320Adapter
    a = ZteC320Adapter()
    onus = await a.list_onus("olt-1")
    assert len(onus) == 2
    assert onus[0].serial_number.startswith("ZTEG-")


@pytest.mark.asyncio
async def test_get_onu_signal_resolves_serial_to_cli(monkeypatch):
    """After list_onus populates the cache, get_onu_signal(serial) uses CLI ID."""
    from src.adapters import zte_c320

    state_output = """\
OnuIndex   Admin State  OMCC State  Phase State  Channel
--------------------------------------------------------------
1/1/1:1     enable       enable      working      1(GPON)
ZXAN#
"""
    detail_output = """\
ONU interface:         gpon-onu_1/1/1:1
  Name:                target_user
  Phase state:         working
  Serial number:       ZTEG-TARGET001
  Online Duration:     1d 0h 0m 0s
ZXAN#
"""
    commands_seen = []

    async def fake_connect(self): pass
    async def fake_close(self): pass
    async def fake_login(self, user, pw, **kw): pass
    async def fake_run(self, command, *, prompt_markers, timeout=None):
        commands_seen.append(command)
        if "onu state" in command:
            return state_output
        if "detail-info" in command:
            return detail_output
        if "power attenuation" in command:
            return SAMPLE_ATTENUATION_OUTPUT
        return "\nZXAN#\n"

    monkeypatch.setattr(zte_c320.TelnetSession, "connect", fake_connect)
    monkeypatch.setattr(zte_c320.TelnetSession, "close", fake_close)
    monkeypatch.setattr(zte_c320.TelnetSession, "login", fake_login)
    monkeypatch.setattr(zte_c320.TelnetSession, "run", fake_run)

    adapter = zte_c320.ZteC320Adapter(
        host="10.42.0.11", username="u", password="p", offline=False,
    )
    await adapter.list_onus("olt-1", pon_port="gpon-olt_1/1/1")
    assert "ZTEG-TARGET001" in adapter._serial_to_cli
    assert adapter._serial_to_cli["ZTEG-TARGET001"] == "1/1/1:1"

    sig = await adapter.get_onu_signal("olt-1", "ZTEG-TARGET001")
    assert sig is not None
    assert sig["rx_power_dbm"] == pytest.approx(-22.53, abs=0.01)

    power_cmd = commands_seen[-1]
    assert "gpon-onu_1/1/1:" in power_cmd, power_cmd
    assert "ZTEG-" not in power_cmd, power_cmd
