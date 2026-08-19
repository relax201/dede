"""Unit tests — market depth + trades normalization"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-chars!!")
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost:5432/tasi")

from app.domain.services.market_book_service import MarketBookService


@pytest.mark.asyncio
async def test_get_depth_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    client = AsyncMock()
    client.get_depth = AsyncMock(
        return_value={
            "symbol": "2222",
            "updated_at": "2026-08-19T10:00:00Z",
            "session": "regular",
            "book_state": "open",
            "levels": 2,
            "best_bid": 27.0,
            "best_ask": 27.1,
            "spread": 0.1,
            "spread_bps": 37.0,
            "entitled_levels": 10,
            "bids": [{"level": 1, "price": 27.0, "quantity": 1000, "order_count": 3}],
            "asks": [{"level": 1, "price": 27.1, "quantity": 800, "order_count": 2}],
        }
    )
    stored: dict = {}

    class DummyRedis:
        def get_json(self, key: str):
            return stored.get(key)

        def set_json(self, key: str, value, ttl_seconds: int) -> None:
            stored[key] = value

    import app.domain.services.market_book_service as mod
    from app.infrastructure.cache.memory_cache import memory_cache

    memory_cache.clear()
    monkeypatch.setattr(mod, "redis_client", DummyRedis())

    service = MarketBookService(client=client)
    out = await service.get_depth("2222.SR", levels=5)
    assert out["symbol"] == "2222"
    assert out["source"] == "sahmk"
    assert out["best_bid"] == 27.0
    assert out["bids"][0]["quantity"] == 1000
    assert "depth:2222:5" in stored


@pytest.mark.asyncio
async def test_get_trades_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    client = AsyncMock()
    client.get_trades = AsyncMock(
        return_value={
            "symbol": "2222",
            "updated_at": "2026-08-19T10:01:00Z",
            "count": 1,
            "summary": {
                "event_count": 1,
                "trade_quantity": 500,
                "trade_value": 13500.0,
                "latest_event_time": "2026-08-19T10:00:55Z",
            },
            "events": [
                {
                    "event_time": "2026-08-19T10:00:55Z",
                    "price": 27.0,
                    "quantity": 500,
                    "value": 13500.0,
                    "side": "buy",
                }
            ],
        }
    )
    stored: dict = {}

    class DummyRedis:
        def get_json(self, key: str):
            return stored.get(key)

        def set_json(self, key: str, value, ttl_seconds: int) -> None:
            stored[key] = value

    import app.domain.services.market_book_service as mod
    from app.infrastructure.cache.memory_cache import memory_cache

    memory_cache.clear()
    monkeypatch.setattr(mod, "redis_client", DummyRedis())

    service = MarketBookService(client=client)
    out = await service.get_trades("2222", limit=10)
    assert out["count"] == 1
    assert out["events"][0]["price"] == 27.0
    assert out["summary"]["trade_quantity"] == 500
