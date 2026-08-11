"""Unit tests — SAHMK WebSocket client message handling"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-chars!!")
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost:5432/tasi")

from app.infrastructure.external.sahmk_ws import SahmkStockStream
from app.infrastructure.messaging.live_bridge import handle_sahmk_quote


@pytest.mark.asyncio
async def test_connected_and_subscribe_flow() -> None:
    on_quote = AsyncMock()
    on_event = AsyncMock()
    stream = SahmkStockStream(
        api_key="shmk_test_dummy",
        on_quote=on_quote,
        on_event=on_event,
        seed_symbols=["2222"],
        subscribe_all=False,
    )

    sent: list[dict] = []

    async def fake_send(payload: dict) -> None:
        sent.append(payload)

    stream._send = fake_send  # type: ignore[method-assign]
    stream._ws = object()  # mark as connected for subscribe sends

    await stream._handle_message(
        '{"type":"connected","plan":"pro","limits":{"max_symbols_per_call":2,"max_symbols_per_connection":60}}'
    )
    assert stream.stats["connected"] is True
    assert stream.stats["plan"] == "pro"
    assert any(p.get("action") == "subscribe" for p in sent)

    await stream._handle_message(
        '{"type":"quote","symbol":"2222","data":{"price":26.5,"bid":26.4,"ask":26.6},"latency_ms":12}'
    )
    on_quote.assert_awaited()
    assert stream.stats["quotes_received"] == 1


@pytest.mark.asyncio
async def test_handle_sahmk_quote_writes_redis_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    stored: dict = {}
    published: list = []

    class DummyRedis:
        def set_json(self, key: str, value: dict, ttl_seconds: int) -> None:
            stored["key"] = key
            stored["value"] = value
            stored["ttl"] = ttl_seconds

        def publish(self, channel: str, payload: dict) -> None:
            published.append((channel, payload))

    import app.infrastructure.messaging.live_bridge as bridge

    monkeypatch.setattr(bridge, "redis_client", DummyRedis())

    await handle_sahmk_quote(
        {
            "type": "quote",
            "symbol": "2222",
            "data": {"price": 26.62, "bid": 26.6, "ask": 26.64, "change_percent": 0.08},
            "timestamp": "2026-08-10T12:20:00+00:00",
            "latency_ms": 14,
        }
    )

    assert stored["key"] == "quote:2222"
    assert stored["value"]["price"] == 26.62
    assert stored["value"]["source"] == "sahmk_ws"
    assert published and published[0][0] == "ws:channel:live"
    assert published[0][1]["type"] == "quote"
