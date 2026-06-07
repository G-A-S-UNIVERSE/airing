"""
AiRing - FastAPI Application Entry Point (public reference release)

This is the sanitized, portfolio-grade entry point. The production
deployment in the author's private repository extends this with
vendor-specific adapters (ZTE, Huawei, C-DATA, FiberHome), Telegram
alert dispatch, and Zabbix webhook ingestion.

Public release demonstrates:
  - Clean pydantic-settings configuration (no hardcoded secrets)
  - HMAC webhook signature verification
  - Prompt-injection guard on inbound payloads
  - Idempotency deduplication
  - Adapter pattern for OLT vendors
  - Prometheus metrics endpoint
  - Health check
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.api.v1 import health, olts, onus
from src.core.config import settings
from src.core.security import (
    verify_webhook_signature,
    idempotency_guard,
    PromptInjectionGuard,
    get_dedup_key,
)
import json


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(f"[AiRing:{settings.APP_VERSION}] starting up (env={settings.APP_ENV})")
    yield
    logger.info(f"[AiRing:{settings.APP_VERSION}] shutting down")


app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description=(
        "Hybrid CMS-OLT Management System (open-source reference). "
        "See README.md for deployment, ADAPTER_DEVELOPMENT.md for extending."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(olts.router, prefix="/api/v1/olts", tags=["OLTs"])
app.include_router(onus.router, prefix="/api/v1/onus", tags=["ONUs"])


@app.get("/")
async def root() -> dict:
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.APP_ENV,
        "docs": "/docs",
        "health": "/health",
    }


# ============================================================
# Reference webhook endpoint (HMAC + injection-guard + idempotency)
# ============================================================

@app.post("/api/v1/webhook/alert")
async def ingest_alert(request: Request) -> dict:
    """Reference webhook handler showing the security chain.

    Production deployments add downstream side-effects (DB persist,
    Telegram dispatch, SSH remediation). This public version only
    echoes the validated payload.
    """
    body = await verify_webhook_signature(request)
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc

    PromptInjectionGuard.validate_payload(payload)

    dedup_key = get_dedup_key(payload)
    if idempotency_guard.is_duplicate(dedup_key):
        return {"status": "ok", "message": "duplicate-suppressed"}

    logger.info(f"Alert received: keys={list(payload.keys())}")
    return {"status": "ok", "received": True}


# ============================================================
# Minimal Prometheus-style metrics endpoint (text format)
# ============================================================

METRICS_STATE = {
    "alerts_total": 0,
    "proposals_total": 0,
    "triage_seconds_total": 0.0,
    "triage_count": 0,
    "started_at": time.time(),
}


@app.get("/metrics")
async def metrics() -> str:
    """Minimal text-format metrics. Replace with prometheus-client in production."""
    uptime = time.time() - METRICS_STATE["started_at"]
    avg_triage = (
        METRICS_STATE["triage_seconds_total"] / METRICS_STATE["triage_count"]
        if METRICS_STATE["triage_count"] > 0
        else 0.0
    )
    return (
        f"# HELP airing_alerts_total Total webhook alerts received\n"
        f"# TYPE airing_alerts_total counter\n"
        f"airing_alerts_total {METRICS_STATE['alerts_total']}\n"
        f"# HELP airing_proposals_total Total remediation proposals\n"
        f"# TYPE airing_proposals_total counter\n"
        f"airing_proposals_total {METRICS_STATE['proposals_total']}\n"
        f"# HELP airing_triage_seconds_avg Average triage latency\n"
        f"# TYPE airing_triage_seconds_avg gauge\n"
        f"airing_triage_seconds_avg {avg_triage:.4f}\n"
        f"# HELP airing_uptime_seconds Process uptime in seconds\n"
        f"# TYPE airing_uptime_seconds gauge\n"
        f"airing_uptime_seconds {uptime:.2f}\n"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
