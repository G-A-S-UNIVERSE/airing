"""
AiRing - Health Check Endpoint

Provides liveness + readiness probes. The liveness endpoint also
reports `secret_key_loaded` so misconfigured deployments are visible
to monitoring systems without a separate readiness check.
"""

from __future__ import annotations

import time
from typing import Any, Dict

from fastapi import APIRouter

from src.core.config import get_settings

router = APIRouter()

_STARTED_AT = time.time()


def _secret_key_status() -> str:
    """'custom' if SECRET_KEY is non-placeholder, else 'default'."""
    return "default" if get_settings().SECRET_KEY == "change-me-to-random-32-bytes" else "custom"


@router.get("")
async def health() -> Dict[str, Any]:
    """Liveness probe. Always 200 if process is up. Includes secret status."""
    s = get_settings()
    return {
        "status": "ok",
        "app": s.APP_NAME,
        "version": s.APP_VERSION,
        "env": s.APP_ENV,
        "uptime_seconds": round(time.time() - _STARTED_AT, 2),
        "secret_key_loaded": _secret_key_status(),
    }


@router.get("/ready")
async def readiness() -> Dict[str, Any]:
    """Readiness probe. Production: verify DB + Redis + adapters."""
    checks: Dict[str, str] = {
        "config": "ok",
        "secret_key_loaded": _secret_key_status(),
    }
    overall = "ok" if all(v != "fail" for v in checks.values()) else "degraded"
    return {
        "status": overall,
        "checks": checks,
    }
