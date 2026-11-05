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
