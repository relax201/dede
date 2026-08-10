"""
Feature Engineering for TASI stocks / استخراج الميزات الفنية
RSI, MACD, Bollinger Bands, Moving Averages, ATR, Volatility
"""

from __future__ import annotations

from typing import Final

import numpy as np
import pandas as pd

EPS: Final[float] = 1e-12


def _validate_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and sort OHLCV by time ascending (required for temporal ML)."""
    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {sorted(missing)}")

    out = df.copy()
    if "ts" in out.columns:
        out = out.sort_values("ts")
    elif "trade_date" in out.columns:
        out = out.sort_values("trade_date")
    else:
        out = out.sort_index()
    return out.reset_index(drop=True)


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder)."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / (avg_loss + EPS)
    return 100.0 - (100.0 / (1.0 + rs))


def compute_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD line, signal line, histogram."""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - macd_signal
    return macd, macd_signal, hist


def compute_bollinger(
    close: pd.Series,
    period: int = 20,
    num_std: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands: upper, middle (SMA), lower."""
    middle = close.rolling(window=period, min_periods=period).mean()
    std = close.rolling(window=period, min_periods=period).std()
    upper = middle + num_std * std
    lower = middle - num_std * std
    return upper, middle, lower


def compute_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """Average True Range — used for Stop Loss = ATR × 2."""
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def compute_volatility(close: pd.Series, period: int = 20) -> pd.Series:
    """Annualized-ish rolling volatility of log returns (daily scale)."""
    log_ret = np.log(close / close.shift(1).replace(0, np.nan))
    return log_ret.rolling(window=period, min_periods=period).std() * np.sqrt(252)


def build_feature_frame(df: pd.DataFrame, forward_horizon: int = 5) -> pd.DataFrame:
    """
    Build full feature matrix + binary target.
    الهدف: هل يغلق السعر أعلى بعد `forward_horizon` أيام؟
    Target: 1 if close[t+h] > close[t], else 0.
    """
    data = _validate_ohlcv(df)
    close = data["close"].astype(float)
    high = data["high"].astype(float)
    low = data["low"].astype(float)

    data["rsi_14"] = compute_rsi(close, 14)
    macd, macd_sig, macd_hist = compute_macd(close)
    data["macd"] = macd
    data["macd_signal"] = macd_sig
    data["macd_hist"] = macd_hist

    bb_u, bb_m, bb_l = compute_bollinger(close)
    data["bb_upper"] = bb_u
    data["bb_middle"] = bb_m
    data["bb_lower"] = bb_l
    data["bb_pct_b"] = (close - bb_l) / ((bb_u - bb_l) + EPS)

    data["sma_20"] = close.rolling(20).mean()
    data["sma_50"] = close.rolling(50).mean()
    data["ema_12"] = close.ewm(span=12, adjust=False).mean()
    data["ema_26"] = close.ewm(span=26, adjust=False).mean()
    data["price_to_sma20"] = close / (data["sma_20"] + EPS) - 1.0
    data["price_to_sma50"] = close / (data["sma_50"] + EPS) - 1.0

    data["atr_14"] = compute_atr(high, low, close, 14)
    data["atr_pct"] = data["atr_14"] / (close + EPS)
    data["volatility_20"] = compute_volatility(close, 20)

    data["return_1d"] = close.pct_change(1)
    data["return_5d"] = close.pct_change(5)
    data["volume_z"] = (
        (data["volume"] - data["volume"].rolling(20).mean())
        / (data["volume"].rolling(20).std() + EPS)
    )

    future_close = close.shift(-forward_horizon)
    data["target"] = (future_close > close).astype("float")

    feature_cols = [
        "rsi_14",
        "macd",
        "macd_signal",
        "macd_hist",
        "bb_upper",
        "bb_middle",
        "bb_lower",
        "bb_pct_b",
        "sma_20",
        "sma_50",
        "ema_12",
        "ema_26",
        "price_to_sma20",
        "price_to_sma50",
        "atr_14",
        "atr_pct",
        "volatility_20",
        "return_1d",
        "return_5d",
        "volume_z",
    ]
    data = data.dropna(subset=feature_cols + ["target"]).reset_index(drop=True)
    return data


FEATURE_COLUMNS: Final[list[str]] = [
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_hist",
    "bb_upper",
    "bb_middle",
    "bb_lower",
    "bb_pct_b",
    "sma_20",
    "sma_50",
    "ema_12",
    "ema_26",
    "price_to_sma20",
    "price_to_sma50",
    "atr_14",
    "atr_pct",
    "volatility_20",
    "return_1d",
    "return_5d",
    "volume_z",
]


def temporal_train_test_split(
    df: pd.DataFrame,
    test_ratio: float = 0.2,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    تقسيم زمني صارم (وليس عشوائياً) لمنع تسرب المستقبل.
    Strict chronological split — never shuffle financial time series.
    """
    if not 0.0 < test_ratio < 1.0:
        raise ValueError("test_ratio must be between 0 and 1")
    split_idx = int(len(df) * (1.0 - test_ratio))
    if split_idx < 50 or len(df) - split_idx < 20:
        raise ValueError("Insufficient rows for temporal split")
    return df.iloc[:split_idx].copy(), df.iloc[split_idx:].copy()
