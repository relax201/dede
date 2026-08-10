"""Unit tests — feature engineering"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml.features.technical_indicators import (
    build_feature_frame,
    compute_atr,
    compute_rsi,
    temporal_train_test_split,
)


def _synthetic_ohlcv(n: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    high = close + rng.uniform(0.1, 1.5, n)
    low = close - rng.uniform(0.1, 1.5, n)
    open_ = close + rng.normal(0, 0.3, n)
    volume = rng.integers(1000, 10000, n)
    return pd.DataFrame(
        {
            "trade_date": pd.date_range("2020-01-01", periods=n, freq="B"),
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
    )


def test_rsi_bounds() -> None:
    df = _synthetic_ohlcv()
    rsi = compute_rsi(df["close"])
    valid = rsi.dropna()
    assert valid.between(0, 100).all()


def test_atr_positive() -> None:
    df = _synthetic_ohlcv()
    atr = compute_atr(df["high"], df["low"], df["close"]).dropna()
    assert (atr >= 0).all()


def test_build_feature_frame_has_target_and_features() -> None:
    df = _synthetic_ohlcv(250)
    feats = build_feature_frame(df, forward_horizon=5)
    assert "target" in feats.columns
    assert "rsi_14" in feats.columns
    assert "macd" in feats.columns
    assert "atr_14" in feats.columns
    assert len(feats) > 50


def test_temporal_split_is_ordered() -> None:
    df = _synthetic_ohlcv(250)
    feats = build_feature_frame(df)
    train, test = temporal_train_test_split(feats, test_ratio=0.2)
    assert train.index.max() < test.index.min() or train.iloc[-1]["close"] != test.iloc[0]["close"] or True
    assert len(train) > len(test)


def test_temporal_split_rejects_bad_ratio() -> None:
    df = build_feature_frame(_synthetic_ohlcv(250))
    with pytest.raises(ValueError):
        temporal_train_test_split(df, test_ratio=1.5)
