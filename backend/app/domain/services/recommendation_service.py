"""Recommendation domain service — Ensemble + Risk + SHAP explanation"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.symbols import normalize_symbol
from app.infrastructure.cache.redis_client import redis_client
from app.infrastructure.db.models import Company, Recommendation
from app.schemas.stock import RecommendationResponse, ShapContribution

logger = logging.getLogger(__name__)

# Import ensemble helpers from ML package when available on PYTHONPATH
try:
    from ml.ensemble.ensemble_model import (
        build_arabic_explanation,
        classify_action,
        combine_scores,
        compute_stops,
        sentiment_to_unit_interval,
    )
except ImportError:  # pragma: no cover — lightweight fallback for isolated API tests
    def classify_action(score: float) -> str:
        if score > 0.80:
            return "strong_buy"
        if score >= 0.60:
            return "buy"
        if score >= 0.40:
            return "hold"
        return "sell"

    def combine_scores(xgb: float, lstm: float, prophet: float, sentiment: float, weights=None) -> float:
        return max(0.0, min(1.0, 0.35 * xgb + 0.30 * lstm + 0.15 * prophet + 0.20 * sentiment))

    def sentiment_to_unit_interval(s: float) -> float:
        return max(0.0, min(1.0, (s + 1.0) / 2.0))

    def compute_stops(entry: float, atr: float, action: str, params=None) -> dict[str, float]:
        risk = atr * 2.0
        reward = risk * 2.5
        if action == "sell":
            return {
                "entry_price": entry,
                "stop_loss": entry + risk,
                "take_profit": entry - reward,
                "risk_reward": 2.5,
                "atr_value": atr,
            }
        return {
            "entry_price": entry,
            "stop_loss": entry - risk,
            "take_profit": entry + reward,
            "risk_reward": 2.5,
            "atr_value": atr,
        }

    def build_arabic_explanation(action: str, confidence: float, shap_top: list) -> str:
        return f"التوصية {action} بثقة {confidence:.1%}"


class RecommendationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_symbol(self, symbol: str, horizon_days: int = 5) -> RecommendationResponse:
        forms = normalize_symbol(symbol)
        if horizon_days not in (5, 10, 20):
            raise ValueError("horizon_days must be 5, 10, or 20")

        cache_key = f"reco:{forms.bare}:{horizon_days}"
        cached = redis_client.get_json(cache_key)
        if isinstance(cached, dict):
            return RecommendationResponse.model_validate(cached)

        company = self.db.scalar(
            select(Company).where(
                (Company.symbol == forms.bare) | (Company.symbol_lseg == forms.lseg)
            )
        )
        if company is None:
            raise LookupError(f"Symbol not found: {forms.display}")

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
        if reco is not None:
            response = self._to_response(forms.display, reco)
            redis_client.set_json(cache_key, response.model_dump(mode="json"), ttl_seconds=300)
            return response

        response = self._infer_live(forms.display, horizon_days=horizon_days)
        redis_client.set_json(cache_key, response.model_dump(mode="json"), ttl_seconds=300)
        return response

    def _infer_live(self, symbol: str, horizon_days: int = 5) -> RecommendationResponse:
        """
        Placeholder for Inference Service call.
        في الإنتاج: استدعاء خدمة الاستدلال (MLflow champion) لأفق 5/10/20 + ATR من ClickHouse.
        """
        xgb, lstm, prophet, sentiment = 0.62, 0.58, 0.55, 0.10
        score = combine_scores(xgb, lstm, prophet, sentiment_to_unit_interval(sentiment))
        action = classify_action(score)
        entry = 100.0
        atr = 1.5
        stops = compute_stops(entry, atr, action)
        shap = [
            ShapContribution(feature="rsi_14", shap_value=0.12),
            ShapContribution(feature="macd_hist", shap_value=0.09),
            ShapContribution(feature="volatility_20", shap_value=-0.04),
        ]
        explanation = build_arabic_explanation(
            action, score, [s.model_dump() for s in shap]  # type: ignore[arg-type]
        )
        explanation = f"{explanation} أفق التحليل: {horizon_days} أيام تداول."
        return RecommendationResponse(
            symbol=symbol,
            action=action,  # type: ignore[arg-type]
            confidence=score,
            ensemble_score=score,
            horizon_days=horizon_days,  # type: ignore[arg-type]
            entry_price=stops["entry_price"],
            stop_loss=stops["stop_loss"],
            take_profit=stops["take_profit"],
            risk_reward=stops["risk_reward"],
            atr_value=stops["atr_value"],
            shap=shap,
            explanation_ar=explanation,
            model_version=settings.MODEL_ENSEMBLE_VERSION,
            generated_at=datetime.now(timezone.utc),
            disclaimer_ar=settings.LEGAL_DISCLAIMER_AR,
        )

    @staticmethod
    def _to_response(symbol: str, reco: Recommendation) -> RecommendationResponse:
        shap_raw: Any = reco.shap_summary or {}
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
        )
