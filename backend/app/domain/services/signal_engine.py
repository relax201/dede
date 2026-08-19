"""Technical-signal heuristic used until champion ML models are loaded."""

from __future__ import annotations

from typing import Any

import pandas as pd

from ml.ensemble.ensemble_model import (
    build_arabic_explanation,
    classify_action,
    compute_stops,
)
from ml.features.technical_indicators import (
    compute_atr,
    compute_bollinger,
    compute_macd,
    compute_rsi,
    compute_volatility,
)


def candles_to_frame(candles: list[dict[str, Any]]) -> pd.DataFrame:
    if not candles:
        return pd.DataFrame()
    df = pd.DataFrame(candles)
    rename = {}
    if "time" in df.columns:
        rename["time"] = "trade_date"
    df = df.rename(columns=rename)
    for col in ("open", "high", "low", "close", "volume"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["close"]).reset_index(drop=True)
    return df


def latest_indicators(candles: list[dict[str, Any]]) -> dict[str, float | None]:
    df = candles_to_frame(candles)
    empty = {
        "rsi_14": None,
        "macd": None,
        "macd_signal": None,
        "bb_upper": None,
        "bb_middle": None,
        "bb_lower": None,
        "atr_14": None,
        "sma_20": None,
        "sma_50": None,
        "volatility_20": None,
        "return_horizon": None,
        "close": None,
    }
    if df.empty or len(df) < 5:
        return empty

    close = df["close"].astype(float)
    high = df["high"].astype(float) if "high" in df.columns else close
    low = df["low"].astype(float) if "low" in df.columns else close
    rsi = compute_rsi(close, 14)
    macd, macd_sig, _hist = compute_macd(close)
    bb_u, bb_m, bb_l = compute_bollinger(close)
    atr = compute_atr(high, low, close, 14)
    vol = compute_volatility(close, min(20, max(5, len(df) // 2)))
    sma20 = close.rolling(min(20, len(df)), min_periods=5).mean()
    sma50 = close.rolling(min(50, len(df)), min_periods=5).mean()

    def last(series: pd.Series) -> float | None:
        if series is None or series.empty:
            return None
        value = series.iloc[-1]
        if pd.isna(value):
            return None
        return float(value)

    return {
        "rsi_14": last(rsi),
        "macd": last(macd),
        "macd_signal": last(macd_sig),
        "bb_upper": last(bb_u),
        "bb_middle": last(bb_m),
        "bb_lower": last(bb_l),
        "atr_14": last(atr),
        "sma_20": last(sma20),
        "sma_50": last(sma50),
        "volatility_20": last(vol),
        "return_horizon": None,
        "close": last(close),
    }


def heuristic_score(candles: list[dict[str, Any]], horizon_days: int = 5) -> dict[str, Any]:
    """
    Map RSI / momentum / MACD into an ensemble-like 0–1 score.
    This is an analysis tool, not a trained champion model.
    """
    indicators = latest_indicators(candles)
    df = candles_to_frame(candles)
    close = float(indicators["close"] or 0.0)
    if close <= 0 or df.empty:
        raise LookupError("Insufficient price history for analysis")

    lookback = min(max(horizon_days, 5), max(len(df) - 1, 1))
    past = float(df["close"].iloc[-1 - lookback])
    momentum = (close / past - 1.0) if past else 0.0
    indicators["return_horizon"] = momentum

    rsi = indicators.get("rsi_14")
    rsi_term = 0.5 if rsi is None else max(0.0, min(1.0, 1.0 - abs((rsi - 55.0) / 55.0)))
    if rsi is not None:
        if rsi < 30:
            rsi_term = 0.72
        elif rsi > 75:
            rsi_term = 0.28

    mom_term = max(0.05, min(0.95, 0.5 + momentum / 0.12))
    macd = indicators.get("macd")
    macd_sig = indicators.get("macd_signal")
    macd_term = 0.5
    if macd is not None and macd_sig is not None:
        macd_term = 0.62 if macd > macd_sig else 0.38

    sma20 = indicators.get("sma_20")
    trend_term = 0.5
    if sma20:
        trend_term = 0.64 if close >= sma20 else 0.36

    score = max(
        0.05,
        min(0.95, 0.30 * mom_term + 0.25 * rsi_term + 0.25 * macd_term + 0.20 * trend_term),
    )
    action = classify_action(score)
    atr = float(indicators.get("atr_14") or close * 0.02)
    stops = compute_stops(close, atr, action)
    shap = [
        {"feature": f"return_{horizon_days}d", "shap_value": round(momentum, 4)},
        {"feature": "rsi_14", "shap_value": round((0 if rsi is None else (rsi - 50) / 100), 4)},
        {"feature": "macd_vs_signal", "shap_value": round(macd_term - 0.5, 4)},
        {"feature": "price_vs_sma20", "shap_value": round(trend_term - 0.5, 4)},
    ]
    explanation = build_arabic_explanation(action, score, shap)
    explanation = (
        f"{explanation} أفق التحليل: {horizon_days} أيام تداول. "
        f"العائد خلال الأفق التقريبي {momentum:+.2%}. "
        "إشارة فنية مساعدة وليست نموذجاً مدرّباً نهائياً."
    )
    risk_level = "low" if score >= 0.75 else "medium" if score >= 0.55 else "high"
    return {
        "score": score,
        "action": action,
        "indicators": indicators,
        "stops": stops,
        "shap": shap,
        "explanation_ar": explanation,
        "risk_level": risk_level,
        "model_version": "heuristic-v1",
    }
