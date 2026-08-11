"""Stock quote + indicators service — uses QuoteRouter failover chain"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.symbols import normalize_symbol
from app.infrastructure.cache.redis_client import redis_client
from app.infrastructure.db.models import Company
from app.infrastructure.external.quote_router import QuoteRouter
from app.schemas.stock import IndicatorSnapshot, MarketOverview, StockResponse

logger = logging.getLogger(__name__)


class StockService:
    def __init__(self, db: Session, quotes: QuoteRouter | None = None) -> None:
        self.db = db
        self.quotes = quotes or QuoteRouter()

    async def get_stock(self, symbol: str) -> StockResponse:
        forms = normalize_symbol(symbol)
        company = self.db.scalar(
            select(Company).where(
                (Company.symbol == forms.bare) | (Company.symbol == forms.lseg)
            )
        )
        if company is None:
            raise LookupError(f"Symbol not found: {forms.display}")

        indicators_raw = redis_client.get_json(f"indicators:{forms.bare}:1d") or {}
        indicators = IndicatorSnapshot.model_validate(
            indicators_raw if isinstance(indicators_raw, dict) else {}
        )

        try:
            quote = await self.quotes.get_quote(forms.bare)
            return StockResponse(
                symbol=forms.display,
                name_ar=company.name_ar,
                name_en=company.name_en,
                sector=company.sector,
                price=quote.price,
                change_pct=quote.change_pct,
                volume=quote.volume,
                high=quote.high,
                low=quote.low,
                indicators=indicators,
                updated_at=quote.ts,
                stale=quote.stale,
            )
        except LookupError:
            logger.warning("All quote sources failed for %s", forms.bare)
            return StockResponse(
                symbol=forms.display,
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
