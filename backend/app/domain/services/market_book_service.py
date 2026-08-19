"""SAHMK market depth (order book) + live trades tape — normalize & cache."""

from __future__ import annotations

import logging
from typing import Any

from app.domain.symbols import normalize_symbol
from app.infrastructure.cache.redis_client import redis_client
from app.infrastructure.external.sahmk_client import SahmkClient

logger = logging.getLogger(__name__)


def _level(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "level": row.get("level"),
        "price": float(row["price"]) if row.get("price") is not None else None,
        "quantity": int(row["quantity"]) if row.get("quantity") is not None else 0,
        "order_count": int(row["order_count"]) if row.get("order_count") is not None else None,
    }


class MarketBookService:
    def __init__(self, client: SahmkClient | None = None) -> None:
        self.client = client or SahmkClient()

    async def get_depth(self, symbol: str, levels: int = 10) -> dict[str, Any]:
        forms = normalize_symbol(symbol)
        levels = max(1, min(int(levels), 20))
        cache_key = f"depth:{forms.bare}:{levels}"
        cached = redis_client.get_json(cache_key)
        if isinstance(cached, dict) and cached.get("bids") is not None:
            return cached

        raw = await self.client.get_depth(forms.bare, levels=levels)
        bids = [_level(b) for b in (raw.get("bids") or []) if isinstance(b, dict)]
        asks = [_level(a) for a in (raw.get("asks") or []) if isinstance(a, dict)]
        result = {
            "symbol": forms.bare,
            "source": "sahmk",
            "updated_at": raw.get("updated_at"),
            "session": raw.get("session"),
            "book_state": raw.get("book_state"),
            "levels": raw.get("levels") or len(bids) or levels,
            "entitled_levels": raw.get("entitled_levels"),
            "best_bid": raw.get("best_bid"),
            "best_ask": raw.get("best_ask"),
            "spread": raw.get("spread"),
            "spread_bps": raw.get("spread_bps"),
            "total_bid_quantity_top5": raw.get("total_bid_quantity_top5"),
            "total_ask_quantity_top5": raw.get("total_ask_quantity_top5"),
            "level_imbalance": raw.get("level_imbalance"),
            "bids": bids,
            "asks": asks,
        }
        # Short TTL — book moves quickly during session
        redis_client.set_json(cache_key, result, ttl_seconds=3)
        return result

    async def get_trades(self, symbol: str, limit: int = 50) -> dict[str, Any]:
        forms = normalize_symbol(symbol)
        limit = max(1, min(int(limit), 200))
        cache_key = f"trades:{forms.bare}:{limit}"
        cached = redis_client.get_json(cache_key)
        if isinstance(cached, dict) and cached.get("events") is not None:
            return cached

        raw = await self.client.get_trades(forms.bare, limit=limit)
        events: list[dict[str, Any]] = []
        for e in raw.get("events") or []:
            if not isinstance(e, dict):
                continue
            events.append(
                {
                    "event_time": e.get("event_time") or e.get("timestamp"),
                    "price": float(e["price"]) if e.get("price") is not None else None,
                    "quantity": int(e["quantity"]) if e.get("quantity") is not None else 0,
                    "value": float(e["value"]) if e.get("value") is not None else None,
                    "side": e.get("side"),
                    "market_session": e.get("market_session"),
                }
            )
        summary = raw.get("summary") if isinstance(raw.get("summary"), dict) else {}
        result = {
            "symbol": forms.bare,
            "source": "sahmk",
            "updated_at": raw.get("updated_at"),
            "count": raw.get("count") if raw.get("count") is not None else len(events),
            "summary": {
                "event_count": summary.get("event_count"),
                "trade_quantity": summary.get("trade_quantity"),
                "trade_value": summary.get("trade_value"),
                "latest_event_time": summary.get("latest_event_time"),
            },
            "events": events,
        }
        redis_client.set_json(cache_key, result, ttl_seconds=2)
        return result
