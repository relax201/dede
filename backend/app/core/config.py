"""Application settings / إعدادات تطبيق تاسي فيجن (TASI Vision)"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Brand
    APP_NAME: str = "تاسي فيجن — TASI Vision"
    APP_VERSION: str = "2.4.1"
    BRAND_NAME_AR: str = "تاسي فيجن"
    BRAND_NAME_EN: str = "TASI Vision"
    DEBUG: bool = False
    API_V1_STR: str = "/api"
    TIMEZONE: str = "Asia/Riyadh"

    # Security — override in Railway Variables (do not keep the default in production)
    SECRET_KEY: str = Field(
        default="tasi-vision-dev-only-change-me-32chars",
        min_length=32,
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    RATE_LIMIT_PER_MINUTE: int = 100
    AES_256_KEY_BASE64: str = ""
    AUDIT_RETENTION_YEARS: int = 5  # CMA / حوكمة: 5 سنوات وليس 90 يوماً

    # Databases (Railway injects postgres:// — normalize for SQLAlchemy)
    # SQLite fallback keeps the API usable before Postgres is linked.
    DATABASE_URL: str = "sqlite:////tmp/tasi_vision.db"
    CLICKHOUSE_URL: str = "clickhouse://default:@clickhouse:9000/tasi"
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def normalize_secret_key(cls, v: object) -> object:
        if v is None or (isinstance(v, str) and len(v.strip()) < 32):
            return "tasi-vision-dev-only-change-me-32chars"
        return v

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: object) -> object:
        if v is None or (isinstance(v, str) and not v.strip()):
            return "sqlite:////tmp/tasi_vision.db"
        url = str(v).strip()
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        # Common Railway misconfig: leftover localhost Postgres that refuses connections
        if "postgresql" in url and any(
            host in url for host in ("@localhost", "@127.0.0.1", "@::1", "@0.0.0.0")
        ):
            return "sqlite:////tmp/tasi_vision.db"
        return url

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def normalize_redis_url(cls, v: object) -> object:
        if v is None or (isinstance(v, str) and not v.strip()):
            return "redis://127.0.0.1:6379/0"
        url = str(v).strip()
        # Broken Railway leftover pointing at unreachable local Redis
        if any(h in url for h in ("://localhost", "://127.0.0.1", "://::1", "://0.0.0.0")):
            return "redis://127.0.0.1:6379/0"
        return url

    # Primary live: SAHMK (سهمك) — https://www.sahmk.sa/en/developers/docs
    SAHMK_API_KEY: str = ""
    SAHMK_BASE_URL: str = "https://api.sahmk.sa/api/v1"
    SAHMK_WS_URL: str = "wss://api.sahmk.sa/ws/v1/stocks/"
    SAHMK_RATE_LIMIT_PER_MINUTE: int = 1000
    SAHMK_TICK_INTERVAL_SECONDS: int = 3
    # WebSocket: Enterprise may use symbols=["*"]; Pro max 60/connection
    SAHMK_WS_ENABLED: bool = True
    SAHMK_WS_SUBSCRIBE_ALL: bool = False  # requires Enterprise; Pro → auto-fallback
    SAHMK_WS_AUTO_UNIVERSE: bool = True  # build widest list up to MAX_SYMBOLS
    SAHMK_WS_MAX_SYMBOLS: int = 60
    SAHMK_WS_SEED_SYMBOLS: str = (
        "2222,1120,1180,1010,1050,1060,1150,2010,1211,2020,"
        "7010,7020,7030,2082,2280,4001,4002,4030,5110,7203"
    )
    SAHMK_WS_PING_INTERVAL_SECONDS: float = 20.0

    # LSEG — historical + live failover (every 10s)
    LSEG_API_KEY: str = ""
    LSEG_BASE_URL: str = "https://api.refinitiv.com"
    LSEG_RATE_LIMIT_PER_HOUR: int = 2000
    LSEG_FAILOVER_INTERVAL_SECONDS: int = 10

    # MarketAux — news/sentiment
    MARKETAUX_API_KEY: str = ""
    MARKETAUX_BASE_URL: str = "https://api.marketaux.com/v1"
    MARKETAUX_RATE_LIMIT_PER_MINUTE: int = 200

    # Backup providers
    TADAWUL_API_KEY: str = ""
    TADAWUL_BASE_URL: str = "https://api.tadawul.com.sa"
    ALPHA_VANTAGE_API_KEY: str = ""
    ALPHA_VANTAGE_BASE_URL: str = "https://www.alphavantage.co/query"

    # Coverage
    COVERAGE_BASIC_TARGET: int = 350
    COVERAGE_ADVANCED_TARGET: int = 120

    # Recommendation horizons
    FORWARD_HORIZON_DEFAULT: int = 5
    FORWARD_HORIZONS: str = "5,10,20"  # comma-separated
    RECO_CRON_MORNING: str = "0 6 * * 0-4"  # 06:00 Asia/Riyadh Sun–Thu
    RECO_CRON_MIDDAY: str = "0 12 * * 0-4"

    # Compliance — أدوات تحليل مع إخلاء مسؤولية
    COMPLIANCE_MODE: Literal["analysis_disclaimer"] = "analysis_disclaimer"
    CMA_PRELIMINARY_APPROVAL: bool = True
    LEGAL_DISCLAIMER_AR: str = (
        "تاسي فيجن أداة تحليل مساعدة ولا تشكّل توصية استثمارية شخصية أو عرضاً للشراء أو البيع. "
        "الأداء السابق لا يضمن النتائج المستقبلية. تتحمّل وحدك مسؤولية قراراتك الاستثمارية. "
        "تم الحصول على موافقة مبدئية من هيئة السوق المالية (CMA) لعرض أدوات التحليل مع إخلاء المسؤولية."
    )

    # Cloud
    AWS_REGION_PRIMARY: str = "me-south-1"
    AWS_REGION_DR: str = "eu-central-1"
    MONTHLY_BUDGET_USD_MIN: int = 2000
    MONTHLY_BUDGET_USD_MAX: int = 3000

    # ML
    MLFLOW_TRACKING_URI: str = "http://mlflow:5000"
    MODEL_ENSEMBLE_VERSION: str = "champion"

    # CORS — include Railway preview/custom domains via env
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # Risk defaults
    ATR_STOP_MULTIPLIER: float = 2.0
    REWARD_RISK_RATIO: float = 2.5
    RISK_PER_TRADE: float = 0.015

    # Railway / cloud
    PORT: int = 8000
    RAILWAY_PUBLIC_DOMAIN: str = ""
    RAILWAY_STATIC_URL: str = ""

    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    @property
    def cors_origins(self) -> list[str]:
        origins = [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]
        if self.RAILWAY_STATIC_URL:
            origins.append(self.RAILWAY_STATIC_URL.rstrip("/"))
        # de-dupe preserve order
        seen: set[str] = set()
        out: list[str] = []
        for o in origins:
            if o not in seen:
                seen.add(o)
                out.append(o)
        return out

    @property
    def forward_horizons(self) -> list[int]:
        return [int(x.strip()) for x in self.FORWARD_HORIZONS.split(",") if x.strip()]

    @property
    def sahmk_ws_seed_symbols(self) -> list[str]:
        return [s.strip() for s in self.SAHMK_WS_SEED_SYMBOLS.split(",") if s.strip()]

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
