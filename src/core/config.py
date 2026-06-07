"""
AiRing - Configuration Module (sanitized public release)

All secrets are read from environment variables. No internal IPs,
credentials, or vendor endpoints are baked into defaults.

Copy `.env.example` to `.env` and fill in your own values.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings sourced from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_ENV: str = Field(default="development", description="development|production")
    APP_NAME: str = Field(default="AiRing", description="Display name")
    APP_VERSION: str = Field(default="0.1.0")

    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./airing.db",
        description="SQLAlchemy database URL",
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis cache URL",
    )

    SECRET_KEY: str = Field(
        default="change-me-to-random-32-bytes",
        description="HMAC secret for webhook signature verification",
    )
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)

    PATIH_MQTT_HOST: str = Field(default="localhost")
    PATIH_MQTT_PORT: int = Field(default=1883)
    PATIH_CLI_API: str = Field(
        default="http://localhost:8080/execute",
        description="PATIH OLT Manager CLI endpoint (set to your deployment)",
    )

    CMS_API_HOST: str = Field(default="localhost")
    CMS_API_PORT: int = Field(default=9999)
    CMS_API_TOKEN: str = Field(default="changeme")
    CMS_API_BASE_URL: str = Field(default="http://localhost/v1/openapi/cms")

    SMARTOLT_API_KEY: str = Field(default="changeme")
    SMARTOLT_API_URL: str = Field(default="https://api.smartolt.com")

    SNMP_COMMUNITY: str = Field(default="public")
    SNMP_VERSION: str = Field(default="2c")
    SNMP_TIMEOUT: int = Field(default=5)
    SNMP_RETRIES: int = Field(default=3)
    SNMP_POLL_INTERVAL: int = Field(default=60)

    LOG_LEVEL: str = Field(default="INFO")
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Comma-separated list of allowed CORS origins",
    )

    @property
    def parsed_cors_origins(self) -> List[str]:
        if not self.CORS_ORIGINS:
            return ["http://localhost:3000", "http://localhost:8000"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV.lower() == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor (avoid re-reading env on every call)."""
    return Settings()


settings = get_settings()
