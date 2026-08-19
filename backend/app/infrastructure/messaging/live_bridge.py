"""Bridge SAHMK WS quotes → Redis cache + Pub/Sub + in-process WS fan-out"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.infrastructure.cache import memory_quotes
from app.infrastructure.cache.redis_client import redis_client

logger = logging.getLogger(__name__)


async def handle_sahmk_quote(message: dict[str, Any]) -> None:
    """
    Normalize a SAHMK quote frame and publish downstream.

    Expected frame:
    {
      "type": "quote",
      "symbol": "2222",
      "data": {"price": 25.86, "bid": ..., "ask": ...},
      "timestamp": "...",
      "latency_ms": 14
    }
    """
    symbol = str(message.get("symbol", "")).upper()
    data = message.get("data") or {}
    if not symbol or "price" not in data:
        logger.debug("Ignoring incomplete SAHMK quote: %s", message)
        return

    price = float(data["price"])
    payload = {
        "type": "quote",
        "source": "sahmk_ws",
        "symbol": symbol,
        "price": price,
        "bid": _opt_float(data.get("bid")),
        "ask": _opt_float(data.get("ask")),
        "bid_size": _opt_float(data.get("bid_size")),
        "ask_size": _opt_float(data.get("ask_size")),
        "change_pct": _opt_float(data.get("change_percent") or data.get("change_pct")),
        "volume": _opt_float(data.get("volume")),
        "high": _opt_float(data.get("high")),
        "low": _opt_float(data.get("low")),
        "latency_ms": message.get("latency_ms"),
        "ts": message.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        "mode": message.get("mode"),
    }

    cached = {
        "price": payload["price"],
        "change_pct": payload["change_pct"] or 0.0,
        "volume": payload["volume"] or 0.0,
        "high": payload["high"],
        "low": payload["low"],
        "bid": payload["bid"],
        "ask": payload["ask"],
        "ts": payload["ts"],
        "source": "sahmk_ws",
    }
    memory_quotes.put_quote(symbol, cached)
    ttl = max(settings.SAHMK_TICK_INTERVAL_SECONDS * 4, 15)
    redis_client.set_json(f"quote:{symbol}", cached, ttl_seconds=ttl)
    redis_client.publish("ws:channel:live", payload)

    # In-process fan-out (works even if Redis is down)
    try:
        from app.websockets.live import manager

        await manager.broadcast(payload)
    except Exception as exc:  # noqa: BLE001
        logger.debug("In-process broadcast skipped: %s", exc)


async def handle_sahmk_event(message: dict[str, Any]) -> None:
    """Forward non-quote control events to live channel (connected/errors)."""
    event = {
        "type": "sahmk_event",
        "source": "sahmk_ws",
        "event": message.get("type"),
        "payload": message,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    redis_client.publish("ws:channel:live", event)
    try:
        from app.websockets.live import manager

        await manager.broadcast(event)
    except Exception:  # noqa: BLE001
        pass


def _opt_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
