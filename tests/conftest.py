"""Shared pytest fixtures."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Make `src` importable from tests
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Set test-friendly env BEFORE importing the app
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-prod")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

from src.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient (sync, in-process)."""
    return TestClient(app)


@pytest.fixture
def secret_key() -> str:
    return os.environ["SECRET_KEY"]
