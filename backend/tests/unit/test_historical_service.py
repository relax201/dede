"""Unit tests — historical candles normalization"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-chars!!")
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost:5432/tasi")

from app.domain.services.historical_service import HistoricalService


@pytest.mark.asyncio
async def test_get_candles_sorted_and_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    client = AsyncMock()
    client.get_historical = AsyncMock(
        return_value={
            "total": 2,
            "data": [
                {
                    "date": "2026-07-14",
                    "open": 1,
                    "high": 2,
                    "low": 0.5,
                    "close": 1.5,
                    "volume": 10,
                },
                {
                    "date": "2026-07-13",
                    "open": 1,
                    "high": 1.2,
                    "low": 0.9,
                    "close": 1.1,
                    "volume": 8,
                },
            ],
        }
    )

    stored: dict = {}

    class DummyRedis:
        def get_json(self, key: str):
            return stored.get(key)

        def set_json(self, key: str, value, ttl_seconds: int) -> None:
            stored[key] = value

    import app.domain.services.historical_service as mod

    monkeypatch.setattr(mod, "redis_client", DummyRedis())

    service = HistoricalService(client=client)
    out = await service.get_candles("2222.SR", limit=10, persist=False)
    assert out["symbol"] == "2222"
    assert out["count"] == 2
    assert out["candles"][0]["time"] == "2026-07-13"
    assert out["candles"][1]["time"] == "2026-07-14"
    assert "candles:2222:1d:10" in stored
