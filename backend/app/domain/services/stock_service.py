"""Stock quote + indicators service"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.cache.redis_client import redis_client
from app.infrastructure.db.models import Company
from app.schemas.stock import IndicatorSnapshot, MarketOverview, StockResponse

logger = logging.getLogger(__name__)


class StockService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_stock(self, symbol: str) -> StockResponse:
        symbol = symbol.upper()
        cached = redis_client.get_json(f"quote:{symbol}")
        company = self.db.scalar(select(Company).where(Company.symbol == symbol))
        if company is None:
            raise LookupError(f"Symbol not found: {symbol}")

        indicators_raw = redis_client.get_json(f"indicators:{symbol}:1d") or {}
        indicators = IndicatorSnapshot.model_validate(indicators_raw if isinstance(indicators_raw, dict) else {})

        if isinstance(cached, dict) and "price" in cached:
            return StockResponse(
                symbol=symbol,
                name_ar=company.name_ar,
                name_en=company.name_en,
                sector=company.sector,
                price=float(cached["price"]),
                change_pct=float(cached.get("change_pct", 0.0)),
                volume=float(cached.get("volume", 0.0)),
                high=float(cached["high"]) if cached.get("high") is not None else None,
                low=float(cached["low"]) if cached.get("low") is not None else None,
                indicators=indicators,
                updated_at=datetime.now(timezone.utc),
                stale=False,
            )

        # Fallback: last known DB/ClickHouse mirror would be queried here
        logger.warning("Cache miss for %s — returning stale placeholder", symbol)
        return StockResponse(
            symbol=symbol,
            name_ar=company.name_ar,
            name_en=company.name_en,
            sector=company.sector,
            price=0.0,
            change_pct=0.0,
            volume=0.0,
            indicators=indicators,
            updated_at=datetime.now(timezone.utc),
            stale=True,
        )

    def market_overview(self) -> MarketOverview:
        cached = redis_client.get_json("market:overview")
        if isinstance(cached, dict):
            return MarketOverview.model_validate(cached)
        return MarketOverview(
            tasi_index=0.0,
            tasi_change_pct=0.0,
            advancers=0,
            decliners=0,
            volume_total=0.0,
            updated_at=datetime.now(timezone.utc),
        )
