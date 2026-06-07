"""
AiRing - Security Primitives (HMAC + Prompt Injection Guard)

All secrets are read from `settings.SECRET_KEY`. No hardcoded values.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from typing import Any, Dict

from fastapi import HTTPException, Request, status

from src.core.config import settings


# ============================================================
# HMAC Webhook Signature Verification
# ============================================================

def sign_payload(body: bytes, secret: str | None = None) -> str:
    """Compute HMAC-SHA256 hex digest of payload."""
    secret_bytes = (secret or settings.SECRET_KEY).encode("utf-8")
    return hmac.new(secret_bytes, body, hashlib.sha256).hexdigest()


async def verify_webhook_signature(request: Request) -> bytes:
    """Verify `X-Hub-Signature-256` header against raw request body.

    Raises HTTPException(401) if missing or invalid.
    Returns raw body bytes on success.
    """
    signature_header = request.headers.get("X-Hub-Signature-256", "")
    if not signature_header.startswith("sha256="):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed X-Hub-Signature-256 header",
        )

    expected_prefix = "sha256="
    provided_sig = signature_header[len(expected_prefix):]

    body = await request.body()
    if not isinstance(body, bytes):
        body = body.encode("utf-8") if body else b""

    expected_sig = sign_payload(body)

    if not hmac.compare_digest(provided_sig, expected_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signature mismatch",
        )

    return body


# ============================================================
# Idempotency Guard (in-memory, replace with Redis for production)
# ============================================================

class IdempotencyGuard:
    """Sliding-window deduplication. Replace with Redis SETEX for multi-instance."""

    def __init__(self, window_seconds: int = 300):
        self.window_seconds = window_seconds
        self._seen: Dict[str, float] = {}

    def is_duplicate(self, key: str) -> bool:
        import time
        now = time.time()
        cutoff = now - self.window_seconds
        self._seen = {k: t for k, t in self._seen.items() if t >= cutoff}
        if key in self._seen:
            return True
        self._seen[key] = now
        return False


# ============================================================
# Prompt Injection Guard (public sanitized subset)
# ============================================================

INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(?:all\s+)?(?:prior|above)\s+(?:rules|context)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:a|in)\s+", re.IGNORECASE),
    re.compile(r"system\s*:\s*you\s+are", re.IGNORECASE),
    re.compile(r"do\s+not\s+respond\s+to\s+or\s+mention", re.IGNORECASE),
    re.compile(r"no\s+prompt\s+injection\s+has\s+occurred", re.IGNORECASE),
    re.compile(r"simulate\s+(?:a|an)\s+(?:admin|root)\s+override", re.IGNORECASE),
]


class PromptInjectionGuard:
    """Detect and reject prompt-injection patterns in inbound payloads."""

    @staticmethod
    def validate_payload(payload: Dict[str, Any]) -> None:
        """Walk all string fields; raise HTTPException(400) on match."""
        for key, value in payload.items():
            if isinstance(value, str):
                if PromptInjectionGuard._scan_string(value):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Prompt injection detected in field '{key}'",
                    )
            elif isinstance(value, dict):
                PromptInjectionGuard.validate_payload(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        if PromptInjectionGuard._scan_string(item):
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Prompt injection detected in list under '{key}'",
                            )
                    elif isinstance(item, dict):
                        PromptInjectionGuard.validate_payload(item)

    @staticmethod
    def _scan_string(text: str) -> bool:
        for pattern in INJECTION_PATTERNS:
            if pattern.search(text):
                return True
        return False


idempotency_guard = IdempotencyGuard()


def get_dedup_key(payload: Dict[str, Any]) -> str:
    """Compute a stable dedup key from alert payload (event_id fallback to hash)."""
    event_id = payload.get("event_id") or payload.get("eventid") or ""
    if event_id:
        return f"evt:{event_id}"
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
    return f"hash:{digest}"


import json  # noqa: E402  (placed after function to keep top imports tidy)
