"""
Ensemble Model — دمج XGBoost + LSTM + Prophet + AraBERT بأوزان متغيرة
هدف الدقة: AUC-ROC ≥ 0.78
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

Action = Literal["strong_buy", "buy", "hold", "sell"]


@dataclass(frozen=True)
class EnsembleWeights:
    xgboost: float = 0.35
    lstm: float = 0.30
    prophet: float = 0.15
    arabert: float = 0.20

    def normalized(self) -> "EnsembleWeights":
        total = self.xgboost + self.lstm + self.prophet + self.arabert
        if total <= 0:
            raise ValueError("Weights must sum to a positive value")
        return EnsembleWeights(
            xgboost=self.xgboost / total,
            lstm=self.lstm / total,
            prophet=self.prophet / total,
            arabert=self.arabert / total,
        )


@dataclass(frozen=True)
class RiskParams:
    atr_stop_multiplier: float = 2.0
    reward_risk: float = 2.5
    risk_per_trade: float = 0.015
    max_risk_per_trade: float = 0.02


def classify_action(score: float) -> Action:
    """تصنيف رباعي حسب عتبات الثقة."""
    if score > 0.80:
        return "strong_buy"
    if score >= 0.60:
        return "buy"
    if score >= 0.40:
        return "hold"
    return "sell"


def combine_scores(
    xgb_proba: float,
    lstm_proba: float,
    prophet_score: float,
    sentiment_score: float,
    weights: EnsembleWeights | None = None,
) -> float:
    """
    prophet_score / sentiment_score expected in [0, 1]
    (sentiment: map (-1..1) → (0..1) before calling).
    """
    w = (weights or EnsembleWeights()).normalized()
    score = (
        w.xgboost * _clip01(xgb_proba)
        + w.lstm * _clip01(lstm_proba)
        + w.prophet * _clip01(prophet_score)
        + w.arabert * _clip01(sentiment_score)
    )
    return float(_clip01(score))


def sentiment_to_unit_interval(sentiment: float) -> float:
    """Map AraBERT sentiment from [-1, 1] to [0, 1]."""
    return float(_clip01((sentiment + 1.0) / 2.0))


def compute_stops(
    entry_price: float,
    atr: float,
    action: Action,
    params: RiskParams | None = None,
) -> dict[str, float]:
    """Stop Loss = ATR×2 ، Take Profit بنسبة عائد/مخاطرة 2.5:1."""
    p = params or RiskParams()
    if entry_price <= 0 or atr < 0:
        raise ValueError("Invalid entry_price or atr")

    risk = atr * p.atr_stop_multiplier
    reward = risk * p.reward_risk

    if action in ("strong_buy", "buy"):
        stop_loss = entry_price - risk
        take_profit = entry_price + reward
    elif action == "sell":
        stop_loss = entry_price + risk
        take_profit = entry_price - reward
    else:
        stop_loss = entry_price - risk
        take_profit = entry_price + reward

    return {
        "entry_price": float(entry_price),
        "stop_loss": float(max(stop_loss, 0.0)),
        "take_profit": float(max(take_profit, 0.0)),
        "risk_reward": float(p.reward_risk),
        "atr_value": float(atr),
    }


def position_size(capital: float, entry: float, stop_loss: float, params: RiskParams | None = None) -> int:
    """حجم الصفقة بحيث لا تتجاوز المخاطرة 1.5% (حد أقصى 2%)."""
    p = params or RiskParams()
    risk_pct = min(p.risk_per_trade, p.max_risk_per_trade)
    risk_amount = capital * risk_pct
    per_share_risk = abs(entry - stop_loss)
    if per_share_risk <= 0:
        return 0
    shares = int(risk_amount // per_share_risk)
    return max(shares, 0)


def build_arabic_explanation(
    action: Action,
    confidence: float,
    shap_top: list[dict[str, Any]],
) -> str:
    """تقرير نصي مبسط بالعربية مبني على أعلى مساهمات SHAP."""
    action_ar = {
        "strong_buy": "شراء قوي",
        "buy": "شراء",
        "hold": "محايد",
        "sell": "بيع",
    }[action]
    drivers = "، ".join(
        f"{item.get('feature', '?')} ({item.get('shap_value', item.get('mean_abs_shap', 0)):.3f})"
        for item in shap_top[:3]
    )
    return (
        f"التوصية: {action_ar} بثقة {confidence:.1%}. "
        f"أبرز العوامل المؤثرة: {drivers or 'غير متوفرة'}. "
        f"تم احتساب وقف الخسارة عند ATR×2 وجني الأرباح بنسبة عائد/مخاطرة 2.5:1."
    )


def _clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))
