"""Unit tests — ensemble + risk engine"""

from __future__ import annotations

import pytest

from ml.ensemble.ensemble_model import (
    classify_action,
    combine_scores,
    compute_stops,
    position_size,
    sentiment_to_unit_interval,
)


def test_classify_action_thresholds() -> None:
    assert classify_action(0.85) == "strong_buy"
    assert classify_action(0.70) == "buy"
    assert classify_action(0.50) == "hold"
    assert classify_action(0.20) == "sell"


def test_combine_scores_range() -> None:
    score = combine_scores(0.9, 0.8, 0.7, 0.6)
    assert 0.0 <= score <= 1.0


def test_sentiment_mapping() -> None:
    assert sentiment_to_unit_interval(-1.0) == 0.0
    assert sentiment_to_unit_interval(1.0) == 1.0
    assert sentiment_to_unit_interval(0.0) == 0.5


def test_compute_stops_buy_rr() -> None:
    stops = compute_stops(entry_price=100.0, atr=2.0, action="buy")
    risk = 100.0 - stops["stop_loss"]
    reward = stops["take_profit"] - 100.0
    assert risk == pytest.approx(4.0)
    assert reward / risk == pytest.approx(2.5)


def test_position_size_respects_risk_cap() -> None:
    shares = position_size(capital=100_000, entry=50.0, stop_loss=48.0)
    # risk amount = 1500, per share = 2 → 750 shares
    assert shares == 750
