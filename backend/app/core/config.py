"""Application settings / إعدادات التطبيق"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "منصة تحليل الأسهم السعودية — TASI AI"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    API_V1_STR: str = "/api"
    TIMEZONE: str = "Asia/Riyadh"

    # Security
    SECRET_KEY: str = Field(..., min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    RATE_LIMIT_PER_MINUTE: int = 100

    # Databases
    DATABASE_URL: str
    CLICKHOUSE_URL: str = "clickhouse://default:@clickhouse:9000/tasi"
    REDIS_URL: str = "redis://redis:6379/0"

    # External APIs
    SAHMK_API_KEY: str = ""
    SAHMK_BASE_URL: str = "https://api.sahmk.example/v1"
    LSEG_API_KEY: str = ""
    LSEG_BASE_URL: str = "https://api.refinitiv.com"
    MARKETAUX_API_KEY: str = ""
    MARKETAUX_BASE_URL: str = "https://api.marketaux.com/v1"

    # ML
    MLFLOW_TRACKING_URI: str = "http://mlflow:5000"
    MODEL_ENSEMBLE_VERSION: str = "champion"

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # Risk defaults
    ATR_STOP_MULTIPLIER: float = 2.0
    REWARD_RISK_RATIO: float = 2.5
    RISK_PER_TRADE: float = 0.015

    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @field_validator("RISK_PER_TRADE")
    @classmethod
    def validate_risk(cls, v: float) -> float:
        if not 0 < v <= 0.02:
            raise ValueError("RISK_PER_TRADE must be in (0, 0.02]")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
