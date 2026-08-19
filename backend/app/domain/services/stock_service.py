"""Stock quote + indicators service — uses QuoteRouter / SAHMK"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.symbols import normalize_symbol
from app.infrastructure.cache.redis_client import redis_client
from app.infrastructure.db.models import Company
from app.infrastructure.external.quote_router import QuoteRouter
from app.infrastructure.external.sahmk_client import SahmkClient
from app.schemas.stock import IndicatorSnapshot, MarketOverview, StockResponse

logger = logging.getLogger(__name__)


class StockService:
    def __init__(
        self,
        db: Session | None = None,
        quotes: QuoteRouter | None = None,
        sahmk: SahmkClient | None = None,
    ) -> None:
        self.db = db
        self.quotes = quotes or QuoteRouter()
        self.sahmk = sahmk or SahmkClient()

    async def get_stock(self, symbol: str) -> StockResponse:
        forms = normalize_symbol(symbol)
        company = None
        if self.db is not None:
            try:
                company = self.db.scalar(
                    select(Company).where(
                        (Company.symbol == forms.bare) | (Company.symbol_lseg == forms.lseg)
                    )
                )
            except Exception as exc:  # noqa: BLE001 — DB may be empty before migrations
                logger.warning("Company lookup skipped for %s: %s", forms.bare, exc)
                try:
                    self.db.rollback()
                except Exception:  # noqa: BLE001
                    pass

        # Enrich from SAHMK even if company row missing (first-time symbol)
        name_ar = company.name_ar if company else forms.display
        name_en = company.name_en if company else forms.display
        sector = company.sector if company else "غير محدد"

        if not company:
            from app.domain.services.company_sync_service import CompanySyncService

            for row in CompanySyncService(db=None).list_cached():
                if str(row.get("symbol")) == forms.bare:
                    name_ar = str(row.get("name_ar") or name_ar)
                    name_en = str(row.get("name_en") or name_en)
                    sector = str(row.get("sector") or sector)
                    break

        indicators_raw = redis_client.get_json(f"indicators:{forms.bare}:1d") or {}
        indicators = IndicatorSnapshot.model_validate(
            indicators_raw if isinstance(indicators_raw, dict) else {}
        )

        try:
            quote = await self.quotes.get_quote(forms.bare)
            raw = quote.raw or {}
            if raw.get("name"):
                name_ar = str(raw["name"])
            if raw.get("name_en"):
                name_en = str(raw["name_en"])
            return StockResponse(
                symbol=forms.display,
                name_ar=name_ar,
                name_en=name_en,
                sector=sector,
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
            if company is None:
                raise LookupError(f"Symbol not found: {forms.display}") from None
            logger.warning("All quote sources failed for %s", forms.bare)
            return StockResponse(
                symbol=forms.display,
                name_ar=name_ar,
                name_en=name_en,
                sector=sector,
                price=0.0,
                change_pct=0.0,
                volume=0.0,
                indicators=indicators,
                updated_at=datetime.now(timezone.utc),
                stale=True,
            )

    async def market_overview(self) -> MarketOverview:
        cached = redis_client.get_json("market:overview")
        if isinstance(cached, dict):
            return MarketOverview.model_validate(cached)

        if self.sahmk.configured:
            try:
                summary = await self.sahmk.get_market_summary("TASI")
                overview = MarketOverview(
                    tasi_index=float(summary.get("index_value", 0.0)),
                    tasi_change_pct=float(summary.get("index_change_percent", 0.0)),
                    advancers=int(summary.get("advancing", 0)),
                    decliners=int(summary.get("declining", 0)),
                    volume_total=float(summary.get("total_volume", 0.0)),
                    updated_at=_parse_ts(summary.get("timestamp")),
                )
                redis_client.set_json(
                    "market:overview",
                    overview.model_dump(mode="json"),
                    ttl_seconds=15,
                )
                return overview
            except Exception as exc:  # noqa: BLE001
                logger.warning("SAHMK market summary failed: %s", exc)

        return MarketOverview(
            tasi_index=0.0,
            tasi_change_pct=0.0,
            advancers=0,
            decliners=0,
            volume_total=0.0,
            updated_at=datetime.now(timezone.utc),
        )


def _parse_ts(value: object) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)
