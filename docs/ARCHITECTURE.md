# Architecture

AiRing is a **hybrid CMS-OLT management system** that unifies multiple
vendor OLTs (ZTE, Huawei, C-DATA, FiberHome) under a single,
vendor-neutral HTTP API. The reference design favors explicit
boundaries, environment-driven configuration, and an adapter pattern
that lets new vendors be added without touching core code.

## High-Level Diagram

```
                  ┌─────────────────────────────────────────────┐
                  │                  Clients                    │
                  │  NOC Dashboard · Telegram Bot · Webhooks    │
                  └──────────────────────┬──────────────────────┘
                                         │ HTTPS / HMAC-signed
                                         ▼
        ┌────────────────────────────────────────────────────────────┐
        │                    FastAPI Application                      │
        │                                                            │
        │   ┌────────────┐  ┌────────────┐  ┌──────────────────┐    │
        │   │ /health    │  │ /api/v1/   │  │ /api/v1/webhook/ │    │
        │   │ /metrics   │  │ {olts,onus}│  │       alert      │    │
        │   └─────┬──────┘  └─────┬──────┘  └────────┬─────────┘    │
        │         │              │                   │              │
        │         └──────┬───────┴───────────┬───────┘              │
        │                ▼                   ▼                       │
        │   ┌──────────────────┐   ┌────────────────────┐           │
        │   │  Adapter Layer   │   │  Security Chain    │           │
        │   │  (BaseOLTAdapter)│   │  • HMAC verify     │           │
        │   │  ├ PatihAdapter  │   │  • Injection guard │           │
        │   │  ├ ZteC320Adapter│   │  • Idempotency     │           │
        │   │  └ ... (vendor)  │   │  • Audit log       │           │
        │   └────────┬─────────┘   └────────────────────┘           │
        │            │                                                │
        │            ▼                                                │
        │   ┌──────────────────┐                                       │
        │   │  Core Services   │                                       │
        │   │  Config · Auth   │                                       │
        │   │  Metrics · DB    │                                       │
        │   └──────────────────┘                                       │
        └─────────────┬──────────────────────────────────────────────┘
                      │
       ┌──────────────┼──────────────┬──────────────┐
       ▼              ▼              ▼              ▼
   ┌───────┐    ┌─────────┐    ┌─────────┐    ┌──────────┐
   │  ZTE  │    │  Huawei │    │ C-DATA  │    │ FiberHome│
   │ C320  │    │ MA5800  │    │  CMS    │    │  AN5516  │
   └───────┘    └─────────┘    └─────────┘    └──────────┘
       SNMP/Telnet/SSH/NETCONF (vendor-specific)
```

## Layered Design

| Layer | Responsibility | Files |
|-------|----------------|-------|
| **Edge / API** | HTTP routing, request validation, response shaping | `src/main.py`, `src/api/v1/*.py` |
| **Security** | HMAC verification, prompt-injection guard, idempotency | `src/core/security.py` |
| **Adapter** | Vendor-specific protocol translation, OLT/ONU access | `src/adapters/*.py` |
| **Core** | Configuration, observability, lifecycle | `src/core/config.py`, `src/core/*.py` |
| **Persistence** | (Production) Postgres / Redis via SQLAlchemy | `requirements.txt` (prod extras) |

## Why an Adapter Pattern?

OLT vendors speak different protocols (SNMP v2c/v3, NETCONF, REST,
proprietary CLI) and return data in incompatible shapes. A naive
implementation would scatter `if vendor == "zte"` checks across the
codebase, multiplying with each new vendor. The adapter pattern
isolates vendor quirks to a single file per vendor, with a uniform
async interface (`list_olts`, `list_onus`, `reboot_onu`, …).

```python
# Every adapter exposes the same surface
async def list_olts(self) -> List[OLTDevice]: ...
async def get_onu_signal(self, olt_id: str, serial: str) -> Optional[Dict[str, float]]: ...
async def reboot_onu(self, olt_id: str, pon_port: str, onu_index: int) -> bool: ...
```

This means the API layer never has to know whether `olt-7` is a ZTE
C320 or a Huawei MA5800 — it just calls `adapter.get_olt("olt-7")` and
gets back a typed `OLTDevice`.

## Configuration Philosophy

**No secret or internal endpoint ever appears in source defaults.**

Every setting is sourced from an environment variable (with a safe
placeholder default that is explicitly labeled "change me" or
"localhost"). The startup config check `health/ready` reports
`secret_key_loaded: default` if `.env` hasn't been configured — making
misconfiguration visible in dashboards, not silent in production.

## Security Chain

Inbound webhook requests pass through three layers before any
business logic runs:

1. **HMAC-SHA256 signature verification** (`X-Hub-Signature-256` header)
   - Constant-time comparison; rejects malformed or missing headers with 401.
2. **Prompt-injection guard**
   - Walks every string field (including nested dicts/lists) and rejects
     requests containing known injection patterns with 400.
3. **Idempotency deduplication**
   - 5-minute sliding window; duplicate `event_id`s are suppressed.

See `tests/test_security.py` for the full coverage matrix.

## Deployment Topologies

| Mode | Use Case | Components |
|------|----------|------------|
| **Local dev** | Single laptop, SQLite | `uvicorn src.main:app --reload` |
| **Container (full)** | Local multi-service test | `docker compose up` (api + db + redis) |
| **Container + proxy** | Local HTTPS test | `docker compose --profile with-proxy up` |
| **Bare-metal / VM** | Production (LXC, K8s node) | `docker compose` or systemd unit |

Production deployments add:
- Prometheus scraper → `/metrics`
- Reverse proxy (Caddy / Nginx / Cloudflare Tunnel) → `/api/v1/*`
- Log shipper (Loki / Datadog) → `stdout` JSON via `loguru`

## Extending AiRing

See [`ADAPTER_DEVELOPMENT.md`](ADAPTER_DEVELOPMENT.md) for the
step-by-step guide to adding a new OLT vendor (estimated: 1–2 days
for a CLI/SNMP device, 1 week for a NETCONF/SOAP device with full
MIB mapping).
