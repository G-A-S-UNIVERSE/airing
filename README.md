# AiRing

> **Hybrid CMS-OLT Management System** — a single API for orchestrating
> heterogeneous FTTH OLTs (ZTE, Huawei, C-DATA, FiberHome) with built-in
> telemetry, security, and an extensible adapter pattern.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688.svg)](https://fastapi.tiangolo.com/)
[![CI](https://img.shields.io/badge/CI-lint%20%2B%20test%20%2B%20build-success-brightgreen.svg)](.github/workflows/ci.yml)
[![code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![lint: ruff](https://img.shields.io/badge/lint-ruff-red.svg)](https://github.com/astral-sh/ruff)
[![security: HMAC + injection guard](https://img.shields.io/badge/security-HMAC%20%2B%20injection%20guard-orange.svg)](src/core/security.py)

---

## What is it?

A real ISP network has OLTs from multiple vendors, each with its own
proprietary management interface. **AiRing** wraps them all in one
vendor-neutral HTTP API with first-class security, observability, and
extensibility.

The public release is a **sanitized reference implementation** — the
adapter pattern, security chain, configuration model, and CI
pipeline. The production deployment in the author's private
repository extends it with vendor-specific telemetry ingestion,
Telegram alert dispatch, and SSH-based remediation.

```
          ┌─────────────┐   ┌───────────────┐   ┌───────────┐   ┌──────────────┐
          │  ZTE C320   │   │ Huawei MA5800 │   │  C-Data   │   │  FiberHome   │
          └──────┬──────┘   └───────┬───────┘   └─────┬─────┘   └──────┬───────┘
                 │                  │                 │                │
   ┌─────────────┴──────────────────┴─────────────────┴────────────────┴────────────┐
   │                            Adapter Layer                                      │
   │                                                                               │
   │  ZteC320Adapter        HuaweiMA5800Adapter       CDataAdapter   FhAdapter     │
   │  (Telnet / CLI)        (NETCONF / SNMP)          (Telnet/CLI)   (Telnet/CLI)  │
   └──────────────────────────────────┬────────────────────────────────────────────┘
                                      │
                                      │  typed dataclasses
                                      │  OLTDevice / ONUDevice
                                      ▼
                    ┌────────────────────────────────────┐
                    │           AiRing FastAPI           │
                    │                                    │
                    │   /api/v1/olts                     │
                    │   /api/v1/onus                     │
                    │   /api/v1/webhook/alert            │
                    │   /health , /health/ready          │
                    │   /metrics   (Prometheus text)     │
                    └────────────────┬───────────────────┘
                                     │
                                     │  JSON over HTTP(S)
                                     ▼
                    ┌────────────────────────────────────┐
                    │   Clients: NOC · bots · dashboards │
                    │   Prometheus · Grafana · Zabbix    │
                    └────────────────────────────────────┘

```

## Why?

Three problems AiRing solves:

1. **Vendor fragmentation.** Every OLT vendor uses a different
   protocol (SNMPv2c, NETCONF, REST, proprietary CLI). Operators end
   up writing glue code per vendor. AiRing collapses that to one
   interface.
2. **Insecure webhook ingress.** Monitoring systems (Zabbix, LibreNMS,
   Observium) push alerts to arbitrary endpoints. Without HMAC
   verification and injection guards, an attacker who knows the
   URL can poison the alert pipeline. AiRing ships a hardened
   chain out of the box.
3. **Auditability.** Network changes need to be attributable and
   reversible. AiRing treats every action as a proposal that must
   be approved before execution, with hash-chained audit logs.


## Current state — what's real, what's still mocked

This repo is a **public reference implementation** that has been
**validated against real ZTE C320 hardware** for the two operations that
matter most in the NOC: listing ONUs and reading their optical Rx power.
The table below is an honest inventory so you know exactly what you're
getting.

| Component | Status | Notes |
|---|---|---|
| **`/metrics`** | ✅ Real | Prometheus text format, counters/gauges, scraped by Prometheus |
| **`/health`, `/health/ready`** | ✅ Real | Reports `secret_key_loaded: default/custom` so misconfig is visible |
| **Production config validation** | ✅ Real | Startup fails if `SECRET_KEY`, `TELNET_PASSWORD`, `CMS_API_TOKEN`, or `SMARTOLT_API_KEY` are placeholders when `APP_ENV=production` |
| **Security chain** (`/api/v1/webhook/alert`) | ✅ Real | HMAC-SHA256 + injection guard + 5-min idempotency window, all tested |
| **`ZteC320Adapter.get_onu_signal()`** | ✅ **Real, hardware-validated** | Telnet query + regex parse; returns actual Rx in dBm |
| **`ZteC320Adapter.list_onus()`** | ✅ **Real, hardware-validated** | Per-ONU `detail-info` queries, hardware serial → CLI-ID cache |
| **`ZteC320Adapter.list_olts()`** | 🟡 Mocked | Returns one chassis with static counters — real impl would query `show card` / `show gpon olt state` |
| **`ZteC320Adapter.reboot_onu()`** | 🟡 Mocked | Logs a message and returns `True` — real impl would run `configure terminal` → `interface` → `onu reset` |
| **`CDataAdapter`** | 🟡 Stub | Registry entry exists; methods return minimal mock data |
| **`/api/v1/olts`** | ✅ Real routing | Calls `get_adapter(...).list_olts()`, not hardcoded fakes — data reflects adapter state |
| **`/api/v1/onus`** | 🟡 Stub | Router exists but endpoints are placeholders |
| **Persistent storage** | ❌ Not included | SQLAlchemy wiring exists in config; no migrations or ORM models yet |
| **Redis-backed idempotency** | ❌ Not included | In-memory dict for development; production needs `SETEX` (see roadmap) |
| **Audit log persistence** | ❌ Not included | Hash-chained audit log lives in private repo |
| **Telegram alert dispatch** | ❌ Not included | Private-repo feature |

**The honest headline:** this repo demonstrates a real, tested, hardware-
validated adapter pattern for the two most valuable ONU read paths, and
scaffolding for everything else. It is not a production-ready orchestrator
out of the box — see [Roadmap](#roadmap) for what that would require.

---


## Features

- **Vendor-neutral adapter pattern** — add a new OLT vendor in
  ~150 lines; the rest of AiRing doesn't change.
- **HMAC-SHA256 webhook verification** with constant-time comparison.
- **Prompt-injection guard** that recursively walks nested
  payloads and rejects known attack patterns with HTTP 400.
- **Idempotency deduplication** (5-minute sliding window).
- **Health + readiness probes** that report config state
  (e.g., `secret_key_loaded: default` makes misconfig visible).
- **Prometheus-style metrics endpoint** (`/metrics`) — counters,
  gauges, histograms.
- **CORS, structured logging (loguru), graceful shutdown**.
- **Multi-stage Docker build** with non-root user, healthcheck,
  and `docker compose` orchestration for api + Postgres + Redis.
  
  
---

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full diagram
and layering rationale.

Key principles:

1. **No hardcoded secrets.** Every setting comes from an environment
   variable. Defaults are explicit placeholders
   (`change-me-to-random-32-bytes`, `changeme`) — never a real IP or key.
   In production mode, placeholders cause startup to fail.

2. **Adapter pattern isolates vendor quirks.** The API layer never knows
   whether `olt-7` is a ZTE C320 or a Huawei MA5800. It calls
   `list_onus(olt_id, pon_port)` and receives typed `ONUDevice` objects.

3. **Security chain runs first.** Every inbound webhook passes through
   HMAC verify → injection guard → idempotency check → business logic.
   Failures are rejected before any side effect.

4. **`offline` flag keeps unit tests hermetic.** Every adapter's
   constructor takes `offline: bool = True`. When `True` (default for
   tests), methods return mocks. When `False`, methods use the real
   protocol (Telnet for ZTE). This means the same class serves both the
   test suite and production with one switch.

---


## Quick Start

```bash
# 1. Clone
git clone https://github.com/your-username/airing.git
cd airing

# 2. Configure
cp .env.example .env
# edit .env — at minimum set SECRET_KEY to a random 32-byte value:
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 3. Install + run
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
uvicorn src.main:app --reload

# 4. Try it
curl http://localhost:8000/health | python -m json.tool
curl http://localhost:8000/api/v1/olts | python -m json.tool
curl http://localhost:8000/metrics | head
open http://localhost:8000/docs
```

You should see secret_key_loaded: "default" in /health until you set a
real SECRET_KEY — that's the misconfiguration visibility feature.

## Pointing the adapter at a real OLT

Set these in .env:

```bash

APP_ENV=development                # don't flip to production until secrets are set
ZTE_DEFAULT_HOST=10.42.0.11        # your OLT's IP
ZTE_DEFAULT_PORT=23
ZTE_PROMPT_MARKER=ZXAN             # ZTE CLI prompt
TELNET_USERNAME=your_olt_user
TELNET_PASSWORD=your_olt_password

```

Then use offline=False in Python (the API layer keeps offline=True
by default — flip it in _adapter() in src/api/v1/olts.py when you're
ready for the API to talk to hardware):

```python

from src.adapters import get_adapter

adapter = get_adapter("zte_c320")
adapter.offline = False
onus = await adapter.list_onus("olt-1", pon_port="gpon-olt_1/1/1")
for onu in onus:
    print(onu.serial_number, onu.status, onu.extra.get("name"))

sig = await adapter.get_onu_signal("olt-1", onus[0].serial_number)
print(f"Rx power: {sig['rx_power_dbm']} dBm")


```


### Docker (full stack)

```bash
docker compose up              # api + postgres + redis
docker compose --profile with-proxy up    # + Caddy reverse proxy

```

## Validating against real hardware

The ZTE adapter has been validated against a live ZTE C320 running
firmware that uses the gpon-onu_X/Y/Z:N command grammar (some firmware
variants accept gpon-olt_X/Y/Z for port-level detail — ours did not).
The validated behaviors:

- list_onus("olt-1", pon_port="gpon-olt_1/1/1") returns every working
ONU on the port, with real hardware serials and subscriber names
populated from show gpon onu detail-info gpon-onu_1/1/1:N.

- serial → cli cache maps each returned hardware serial to its
1/1/1:N CLI identifier.

- get_onu_signal("olt-1", "ZTEG…") resolves the hardware serial via the
cache, runs show pon power attenuation gpon-onu_1/1/1:N, and parses
the downstream Rx value as a float (e.g. -26.576 dBm) that matches
what the OLT's own console reports.

Serial numbers, subscriber names, and the OLT's IP address are not
included in this repo — the test fixtures use synthetic Star Wars /
Star Trek-themed data. To validate against your own hardware, run the
diagnostic script embedded in the last commit message, or:


```python

import asyncio
from src.adapters.zte_c320 import ZteC320Adapter

async def main():
    a = ZteC320Adapter(host="<olt-ip>", username="<user>",
                       password="<pass>", offline=False)
    onus = await a.list_onus("olt-1", pon_port="gpon-olt_1/1/1")
    print(f"{len(onus)} ONUs")
    if onus:
        sig = await a.get_onu_signal("olt-1", onus[0].serial_number)
        print(f"Rx: {sig['rx_power_dbm']} dBm")

asyncio.run(main())

```


## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Web framework | **FastAPI 0.109** | Async-native, Pydantic validation, auto OpenAPI |
| Config | **pydantic-settings 2.1** | Type-safe, .env-aware, fail-loud on bad input |
| Database | **SQLAlchemy 2 + asyncpg** (prod) / **aiosqlite** (dev) | Same ORM, two backends |
| Cache | **Redis 7** (prod) / in-memory (dev) | Idempotency, telemetry buffers |
| Lint/format | **ruff + black** | Fast, opinionated, CI-friendly |
| Tests | **pytest + httpx** | Real TestClient, async-aware |
| Container | **python:3.11-slim** + **Caddy 2** | Small image, easy reverse proxy |

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full
diagram and layering rationale.

Key principles:

- **No hardcoded secrets.** Every setting comes from an env var.
  Defaults are explicit placeholders (`changeme`,
  `change-me-to-random-32-bytes`) — never a real internal IP or key.
- **Adapter pattern isolates vendor quirks.** The API layer never
  knows if `olt-7` is a ZTE C320 or a Huawei MA5800.
- **Security chain runs first.** HMAC verify → injection guard →
  idempotency check → business logic.

## Adding a new OLT vendor

See [`docs/ADAPTER_DEVELOPMENT.md`](docs/ADAPTER_DEVELOPMENT.md) —
it's a 6-step recipe (subclass, implement 5 methods, register,
configure, test, document). Reference implementations in this repo:
`PatihAdapter` (HTTP CLI bridge) and `ZteC320Adapter` (SNMP).

```python
# 30-second example
from src.adapters import get_adapter
adapter = get_adapter("zte_c320")
olts = await adapter.list_olts()
for o in olts:
    print(o.name, o.ip_address, o.status)
```

## Security

The `/api/v1/webhook/alert` endpoint runs every inbound request
through a three-layer chain:

1. **HMAC-SHA256 signature** — must be present in
   `X-Hub-Signature-256` header and match the body.
2. **Prompt-injection guard** — recursive scan of all string
   fields; rejects with HTTP 400 if any match `INJECTION_PATTERNS`.
3. **Idempotency dedup** — duplicate `event_id`s within a
   5-minute window are suppressed.

See `src/core/security.py` and `tests/test_security.py` for the
full surface. The private repository extends this with a
hash-chained audit log and Prometheus metrics.

## Project Status

This is the **public reference release (v0.1.0)**. It is feature-
complete for the patterns it demonstrates (adapter abstraction,
security chain, CI pipeline, deployment). It is **not** a
production-ready OLT orchestrator on its own — production
deployments need:

- Real adapter implementations (private repo) with MIB/CONF maps.
- Persistent storage (Postgres + Alembic migrations).
- TLS termination + reverse proxy.
- Distributed idempotency (Redis SETEX, not in-memory dict).
- Operator RBAC + audit log persistence.

## Configuration

All configuration comes from environment variables (.env in
development). See .env.example for the full list.

Critical settings:

| Variable | Required in prod? | Default | Notes |
|---|---|---|---|
| `APP_ENV` | yes | `development` | Set to `production` to enable fail-loud validation |
| `SECRET_KEY` | **yes** | `change-me-to-random-32-bytes` | Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `TELNET_USERNAME` | yes | `admin` | OLT CLI username |
| `TELNET_PASSWORD` | **yes** | `changeme` | OLT CLI password |
| `CMS_API_TOKEN` | if using CMS | `changeme` | CMS API bearer token |
| `SMARTOLT_API_KEY` | if using SmartOLT | `changeme` | SmartOLT API key |
| `DATABASE_URL` | yes in prod | `sqlite+aiosqlite:///./airing.db` | Use `postgresql+asyncpg://…` in prod |
| `REDIS_URL` | yes in prod | `redis://localhost:6379/0` | For idempotency and telemetry buffers |
| `ZTE_DEFAULT_HOST` | yes for ZTE | `localhost` | Real OLT IP |
| `ZTE_DEFAULT_PORT` | no | `23` | Telnet port |
| `ZTE_PROMPT_MARKER` | no | `ZXAN` | CLI prompt substring for detection |

## Repo Layout

```
airing/
├── src/
│   ├── main.py                    # FastAPI entry — routes, webhook, metrics
│   ├── api/v1/
│   │   ├── health.py              # /health, /health/ready (secret_key_loaded)
│   │   ├── olts.py                # /api/v1/olts (adapter-backed)
│   │   └── onus.py                # /api/v1/onus (stub)
│   ├── adapters/
│   │   ├── base.py                # BaseOLTAdapter, OLTDevice, ONUDevice
│   │   ├── _telnet.py             # Reusable async Telnet session
│   │   ├── zte_parsers.py         # Pure CLI-output parsers (testable)
│   │   ├── zte_c320.py            # ZTE adapter — real Telnet/CLI
│   │   ├── patih_adapter.py       # PATIH bridge (mock in public release)
│   │   └── __init__.py            # ADAPTER_REGISTRY, get_adapter()
│   └── core/
│       ├── config.py              # Pydantic Settings + production validator
│       └── security.py            # HMAC, injection guard, idempotency
├── tests/
│   ├── test_adapters.py           # 8 — registry, contract, mocks
│   ├── test_config.py             # 8 — env, defaults, production validation
│   ├── test_health.py             # 3 — liveness, secret_key_loaded (default/custom)
│   ├── test_metrics.py            # 2 — Prometheus content-type, no JSON wrapping
│   ├── test_olts_api.py           # 1 — /api/v1/olts sources from adapter
│   ├── test_security.py           # 12 — HMAC, injection, idempotency
│   └── test_zte_parse.py          # 17 — parsers, list_onus, get_onu_signal
├── examples/
│   ├── config.zte.starwars.json   # Fictional ZTE config (safe to commit)
│   ├── config.cdata.startrek.json # Fictional C-Data config
│   └── README.md                  # Explains the fictional-data convention
├── docker/                        # Dockerfile, compose, Caddyfile
├── docs/
│   ├── ARCHITECTURE.md
│   └── ADAPTER_DEVELOPMENT.md
├── .github/workflows/ci.yml       # lint (ruff) + format (black) + test (3.11/3.12) + build
├── .env.example
├── .gitignore                     # excludes .env, credentials.json, *.pem, *.key, *.bak*
├── pyproject.toml
├── requirements.txt
├── LICENSE                        # MIT
└── README.md

```

## Development

```bash

# Install with dev deps
pip install -e ".[dev]"

# Run tests
pytest -q                          # 51 passing, ~0.3s

# Lint and format
ruff check src/ tests/
black src/ tests/

# Run app locally (with auto-reload)
uvicorn src.main:app --reload --port 8001

# Verify endpoint manually
curl -s http://localhost:8001/health | python -m json.tool
curl -s http://localhost:8001/metrics | head

```
## Test conventions

- Every test is hermetic. No network, no database. Adapters use
offline=True by default; mocks patch TelnetSession methods.


- TDD discipline. Each feature was added with a failing test first,
then implementation, then green suite.

- Fixtures are synthetic. Test data uses Star Wars / Star Trek
placeholder values — no real serials, subscriber names, or IPs.


- except Exception is banned in the adapter layer. Only specific
exceptions (asyncio.TimeoutError, ConnectionError) are caught, so
code bugs surface immediately instead of being silently swallowed.


## License

[MIT](LICENSE) — use it, fork it, ship it. Attribution appreciated.

## Author Note

**This is a portfolio piece — but parts of it have been validated against
real ZTE C320 hardware, not just mocks.**

The repo started as a sanitized reference implementation. Over the course
of development, two methods were promoted from mocked to genuinely
functional:

- **`ZteC320Adapter.list_onus()`** — was validated against a live ZTE
  C320 at `gpon-olt_1/1/1`. It returned the 3 working ONUs on that port
  with real hardware serials, subscriber names, and a populated
  `serial → CLI-ID` cache.
- **`ZteC320Adapter.get_onu_signal()`** — was validated against the same
  OLT. It resolved a hardware serial to its CLI identifier via the cache,
  ran `show pon power attenuation gpon-onu_1/1/1:N`, and parsed a real
  Rx value (`-26.576 dBm` in one run) that matched what the OLT's own
  console reported.

Everything else — `list_olts()`, `reboot_onu()`, the `CDataAdapter`
stub — is still mocked, and honestly labeled as such in the
[Current state](#current-state--whats-real-whats-still-mocked) table
above. The test suite (49 tests, all green) exercises both paths: the
mocked one for hermetic CI, the real one against recorded hardware
output for parser correctness.

The private production deployment extends this with:

- Live vendor adapters for Huawei MA5800, C-Data EPON, FiberHome
- Telegram alert dispatch with an approval workflow
- Zabbix / LibreNMS webhook ingestion
- SSH-based remediation with rollback
- Hash-chained audit log with a proposal → approval → execution state machine
- Operator RBAC + persistent audit log

**What you see in this repo is the pattern, proven against real hardware
for its two highest-value read paths, with scaffolding for everything
else.** If you're building something similar, or want to discuss the
production architecture, open an issue.
