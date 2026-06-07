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
            ZTE C300/C320    Huawei MA5800    C-DATA    FiberHome
                  │                │             │           │
            ┌─────┴────────────────┴─────────────┴───────────┴─────┐
            │              Adapter Layer (ZteC320, Patih, …)       │
            └────────────────────────┬──────────────────────────────┘
                                     │
                          ┌──────────▼──────────┐
                          │   AiRing FastAPI    │
                          │   /api/v1/olts      │
                          │   /api/v1/onus      │
                          │   /webhook/alert    │
                          │   /metrics          │
                          └─────────────────────┘
                                     │
                          ┌──────────▼──────────┐
                          │  Clients: NOC, Bot  │
                          └─────────────────────┘
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
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/olts
open http://localhost:8000/docs    # interactive OpenAPI
```

### Docker (full stack)

```bash
docker compose up              # api + postgres + redis
docker compose --profile with-proxy up    # + Caddy reverse proxy
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

## Repo Layout

```
airing/
├── src/
│   ├── main.py              # FastAPI entry
│   ├── api/v1/              # HTTP routers (olts, onus, health)
│   ├── adapters/            # Vendor OLT adapters (base, patih, zte_c320)
│   └── core/                # Config, security, audit
├── tests/                   # pytest suite (health, security, adapters, config)
├── docker/                  # Dockerfile, compose, Caddyfile
├── docs/
│   ├── ARCHITECTURE.md
│   └── ADAPTER_DEVELOPMENT.md
├── .github/workflows/ci.yml # lint + test (3.11/3.12) + build
├── pyproject.toml
├── requirements.txt
├── .env.example
├── LICENSE                  # MIT
└── README.md
```

## License

[MIT](LICENSE) — use it, fork it, ship it. Attribution appreciated.

## Author Note

This repo is a portfolio piece. The full production system — with
live vendor adapters, Telegram bot, Zabbix/LibreNMS scrapers, and
SSH remediation — lives in a private repository. Reach out if
you're interested in discussing the production architecture.
