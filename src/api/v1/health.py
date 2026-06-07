"""
AiRing - Health Check Endpoint

Provides liveness + readiness probes. In production, expand
`checks` to verify downstream dependencies (DB, Redis, NATS).
"""

from __future__ import annotations

import time
from typing import Any, Dict

from fastapi import APIRouter

from src.core.config import settings

router = APIRouter()

_STARTED_AT = time.time()


@router.get("")
async def health() -> Dict[str, Any]:
    """Liveness probe. Always returns 200 if process is up."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.APP_ENV,
        "uptime_seconds": round(time.time() - _STARTED_AT, 2),
    }


@router.get("/ready")
async def readiness() -> Dict[str, Any]:
    """Readiness probe. Production: verify DB + Redis + adapters."""
    checks: Dict[str, str] = {
        "config": "ok",
        "secret_key_loaded": "ok" if settings.SECRET_KEY != "change-me-to-random-32-bytes" else "default",
    }
    overall = "ok" if all(v != "fail" for v in checks.values()) else "degraded"
    return {
        "status": overall,
        "checks": checks,
    }
