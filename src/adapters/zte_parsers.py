"""Pure parsers for ZTE C320 CLI output.

Extracted from the production Streamlit monitor script. No dependency on
the adapter class, no network calls. Takes strings, returns data.
"""

from __future__ import annotations

import re
from collections import defaultdict


# Downstream power line: "Tx : 2.48 (dbm)" then "Rx : -22.53 (dbm)"
_ONU_RX_POWER_REGEX = re.compile(
    r"down(?:stream)?\s+tx\s*:\s*[\-\d\.]+\s*\(dbm\)\s+rx\s*:\s*([\-\d\.]+)\s*\(dbm\)",
    re.IGNORECASE,
)

# State table row: "0/1/1:1  enable   enable   working"
_STATE_ROW_REGEX = re.compile(
    r"(\d+/\d+/\d+):(\d+)\s+\w+\s+\w+\s+(\w+)"
)


def parse_onu_states(raw_output: str, onu_type: str = "gpon"):
    """Parse `show gpon onu state` output.

    Returns (grouped, working):
      grouped: {STATE_UPPER: [onu_id, ...]}
      working: [onu_id, ...]  (state == working/online)
    """
    grouped = defaultdict(list)
    working = []
    for match in _STATE_ROW_REGEX.findall(raw_output):
        onu_id = match[1]
        state = match[2]
        if state.lower() in ("working", "online"):
            working.append(onu_id)
        else:
            grouped[state.upper()].append(onu_id)
    return dict(grouped), working


def parse_onu_rx_power(raw_output: str):
    """Extract downstream Rx power (dBm) from `show pon power attenuation`."""
    match = _ONU_RX_POWER_REGEX.search(raw_output)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def extract_detail_info(detail_output: str) -> dict:
    """Parse `show gpon onu detail-info` output into a dict."""
    info = {
        "name": "Unknown",
        "serial": "N/A",
        "status": "unknown",
        "uptime": "N/A",
        "downtime_cause": "N/A",
        "last_down": None,
        "rx_power": "N/A",
    }

    m = re.search(r"Name:\s*(\S.+)", detail_output)
    if m:
        info["name"] = m.group(1).strip()

    m = re.search(r"Serial number:\s*(\S+)", detail_output, re.IGNORECASE)
    if m:
        info["serial"] = m.group(1).strip()

    m = re.search(r"Phase state:\s*(\w+)", detail_output)
    if m:
        state = m.group(1)
        info["status"] = "Online" if state.lower() == "working" else state

    m = re.search(r"Online Duration:\s*([^\n]+)", detail_output)
    if m:
        info["uptime"] = m.group(1).strip()

    # History table: "Authpass Time  OfflineTime  Cause" then data rows.
    history = re.search(
        r"Authpass Time\s+OfflineTime\s+Cause(.*?)(?:\Z|ZXAN)",
        detail_output,
        re.DOTALL,
    )
    if history:
        for line in history.group(1).strip().splitlines():
            parts = line.strip().split()
            if len(parts) >= 6:
                offline_time = f"{parts[3]} {parts[4]}"
                cause = " ".join(parts[5:])
                if offline_time != "0000-00-00 00:00:00":
                    info["downtime_cause"] = cause
                    break

    return info


def parse_bulk_detail_info(raw_output: str) -> list[dict]:
    """Split concatenated `show gpon onu detail-info` output into records.

    ZTE emits one record per ONU, separated by blank lines. Each record
    starts with "OLT:" or "ONU ID:". This splits on blank lines followed
    by a record start, parses each block via `extract_detail_info`, and
    returns a list. Empty input returns an empty list.
    """
    if not raw_output.strip():
        return []

    blocks = re.split(r"\n\s*\n(?=OLT:|ONU ID:)", raw_output.strip())
    return [extract_detail_info(b) for b in blocks if b.strip()]
