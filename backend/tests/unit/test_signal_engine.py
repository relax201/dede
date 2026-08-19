"""Unit tests — technical heuristic signal engine"""

from __future__ import annotations

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-chars!!")
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost:5432/tasi")

from app.domain.services.signal_engine import heuristic_score, latest_indicators


def _candles(n: int = 40, start: float = 20.0, step: float = 0.15) -> list[dict]:
    rows = []
    price = start
    for i in range(n):
        rows.append(
            {
                "time": f"2026-01-{i+1:02d}",
                "open": price,
                "high": price + 0.2,
                "low": price - 0.1,
                "close": price + step,
                "volume": 1000 + i,
            }
        )
        price += step
    return rows


def test_uptrend_scores_as_buy() -> None:
    analysis = heuristic_score(_candles(), horizon_days=5)
    assert analysis["score"] >= 0.5
    assert analysis["action"] in {"buy", "strong_buy", "hold"}
    assert analysis["stops"]["entry_price"] > 0
    assert analysis["stops"]["take_profit"] > 0


def test_indicators_populated() -> None:
    ind = latest_indicators(_candles())
    assert ind["close"] is not None
    assert ind["rsi_14"] is None or 0 <= ind["rsi_14"] <= 100
