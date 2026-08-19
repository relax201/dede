"""Recommendation domain service — heuristic from SAHMK candles + live quote."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.services.company_sync_service import CompanySyncService
from app.domain.services.historical_service import HistoricalService
from app.domain.services.signal_engine import heuristic_score, latest_indicators
from app.domain.symbols import normalize_symbol
from app.infrastructure.cache.redis_client import redis_client
from app.infrastructure.db.models import Company, Recommendation
from app.infrastructure.external.quote_router import QuoteRouter
from app.schemas.stock import RecommendationResponse, ShapContribution
from ml.ensemble.ensemble_model import compute_stops

logger = logging.getLogger(__name__)


class RecommendationService:
    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    async def get_by_symbol(self, symbol: str, horizon_days: int = 5) -> RecommendationResponse:
        forms = normalize_symbol(symbol)
        if horizon_days not in (5, 10, 20):
            raise ValueError("horizon_days must be 5, 10, or 20")

        cache_key = f"reco:{forms.bare}:{horizon_days}"
        cached = redis_client.get_json(cache_key)
        if isinstance(cached, dict):
            return RecommendationResponse.model_validate(cached)

        stored = self._from_db(forms.bare, forms.lseg, horizon_days)
        if stored is not None:
            redis_client.set_json(cache_key, stored.model_dump(mode="json"), ttl_seconds=300)
            return stored

        response = await self._infer_from_market(forms.bare, horizon_days=horizon_days)
        redis_client.set_json(cache_key, response.model_dump(mode="json"), ttl_seconds=180)
        return response

    async def list_live(self, symbols: list[str], horizon_days: int = 5) -> list[RecommendationResponse]:
        sem = asyncio.Semaphore(3)

        async def _one(sym: str) -> RecommendationResponse | None:
            async with sem:
                try:
                    return await asyncio.wait_for(
                        self.get_by_symbol(sym, horizon_days=horizon_days),
                        timeout=12.0,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Reco skipped for %s: %s", sym, exc)
                    return None

        rows = await asyncio.gather(*[_one(s) for s in symbols])
        out = [r for r in rows if r is not None]
        return sorted(out, key=lambda r: r.confidence, reverse=True)

    def _company_meta(self, bare: str) -> tuple[str | None, str | None]:
        if self.db is not None:
            try:
                company = self.db.scalar(select(Company).where(Company.symbol == bare))
                if company is not None:
                    return company.name_ar, company.sector
            except Exception:  # noqa: BLE001
                try:
                    self.db.rollback()
                except Exception:  # noqa: BLE001
                    pass
        for row in CompanySyncService(db=None).list_cached():
            if str(row.get("symbol")) == bare:
                return (
                    str(row.get("name_ar") or "") or None,
                    str(row.get("sector") or "") or None,
                )
        return None, None

    def _from_db(self, bare: str, lseg: str, horizon_days: int) -> RecommendationResponse | None:
        if self.db is None:
            return None
        try:
            company = self.db.scalar(
                select(Company).where((Company.symbol == bare) | (Company.symbol_lseg == lseg))
            )
            if company is None:
                return None
            reco = self.db.scalar(
                select(Recommendation)
                .where(
                    Recommendation.company_id == company.id,
                    Recommendation.status == "active",
                    Recommendation.horizon_days == horizon_days,
                )
                .order_by(Recommendation.generated_at.desc())
                .limit(1)
            )
            if reco is None:
                return None
            return self._to_response(bare, reco, company.name_ar, company.sector)
        except Exception as exc:  # noqa: BLE001
            logger.debug("DB reco lookup skipped: %s", exc)
            try:
                self.db.rollback()
            except Exception:  # noqa: BLE001
                pass
            return None

    async def _infer_from_market(self, symbol: str, horizon_days: int = 5) -> RecommendationResponse:
        history = HistoricalService()
        payload = await history.get_candles(symbol, interval="1d", limit=60, persist=False)
        candles = payload.get("candles") or []
        analysis = heuristic_score(candles, horizon_days=horizon_days)

        # Cache indicators for stock endpoint
        ind = latest_indicators(candles)
        redis_client.set_json(
            f"indicators:{symbol}:1d",
            {k: v for k, v in ind.items() if k != "close" and k != "return_horizon"},
            ttl_seconds=300,
        )

        entry = float(analysis["stops"]["entry_price"])
        try:
            quote = await QuoteRouter().get_quote(symbol)
            if quote.price:
                entry = float(quote.price)
                atr = float(analysis["indicators"].get("atr_14") or entry * 0.02)
                analysis["stops"] = compute_stops(entry, atr, analysis["action"])
        except Exception as exc:  # noqa: BLE001
            logger.debug("Live quote not applied to reco %s: %s", symbol, exc)

        name_ar, sector = self._company_meta(symbol)
        shap = [
            ShapContribution(feature=str(item["feature"]), shap_value=float(item["shap_value"]))
            for item in analysis["shap"]
        ]
        return RecommendationResponse(
            symbol=symbol,
            action=analysis["action"],
            confidence=float(analysis["score"]),
            ensemble_score=float(analysis["score"]),
            horizon_days=horizon_days,  # type: ignore[arg-type]
            entry_price=float(analysis["stops"]["entry_price"]),
            stop_loss=float(analysis["stops"]["stop_loss"]),
            take_profit=float(analysis["stops"]["take_profit"]),
            risk_reward=float(analysis["stops"]["risk_reward"]),
            atr_value=float(analysis["stops"].get("atr_value") or 0),
            shap=shap,
            explanation_ar=str(analysis["explanation_ar"]),
            model_version=str(analysis["model_version"]),
            generated_at=datetime.now(timezone.utc),
            disclaimer_ar=settings.LEGAL_DISCLAIMER_AR,
            risk_level=analysis.get("risk_level"),
            name_ar=name_ar,
            sector=sector or "غير محدد",
        )

    @staticmethod
    def _to_response(
        symbol: str,
        reco: Recommendation,
        name_ar: str | None = None,
        sector: str | None = None,
    ) -> RecommendationResponse:
        shap_raw = reco.shap_summary or {}
        contributions = shap_raw.get("contributions", shap_raw.get("top_features", []))
        shap = [
            ShapContribution(
                feature=str(item.get("feature", "unknown")),
                shap_value=float(item.get("shap_value", item.get("mean_abs_shap", 0.0))),
            )
            for item in contributions
        ]
        return RecommendationResponse(
            symbol=symbol,
            action=reco.action,  # type: ignore[arg-type]
            confidence=float(reco.confidence),
            ensemble_score=float(reco.ensemble_score),
            horizon_days=int(reco.horizon_days),  # type: ignore[arg-type]
            entry_price=float(reco.entry_price),
            stop_loss=float(reco.stop_loss),
            take_profit=float(reco.take_profit),
            risk_reward=float(reco.risk_reward),
            atr_value=float(reco.atr_value) if reco.atr_value is not None else None,
            shap=shap,
            explanation_ar=reco.explanation_ar,
            model_version=reco.model_version,
            generated_at=reco.generated_at,
            disclaimer_ar=settings.LEGAL_DISCLAIMER_AR,
            name_ar=name_ar,
            sector=sector,
        )
