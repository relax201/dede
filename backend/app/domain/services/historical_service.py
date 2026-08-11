"""Fetch and cache daily OHLCV from SAHMK for charts / ML prep"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from app.domain.symbols import normalize_symbol
from app.infrastructure.cache.redis_client import redis_client
from app.infrastructure.external.sahmk_client import SahmkClient

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "ohlcv"


class HistoricalService:
    def __init__(self, client: SahmkClient | None = None) -> None:
        self.client = client or SahmkClient()

    async def get_candles(
        self,
        symbol: str,
        interval: str = "1d",
        limit: int = 365,
        persist: bool = True,
    ) -> dict[str, Any]:
        forms = normalize_symbol(symbol)
        cache_key = f"candles:{forms.bare}:{interval}:{limit}"
        cached = redis_client.get_json(cache_key)
        if isinstance(cached, dict) and cached.get("candles"):
            return cached

        payload = await self.client.get_historical(forms.bare, interval=interval, limit=limit)
        rows = payload.get("data") or []
        candles = [
            {
                "time": str(r.get("date")),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": float(r.get("volume") or 0),
            }
            for r in rows
            if r.get("date") is not None
        ]
        # Charts expect ascending time
        candles.sort(key=lambda c: c["time"])

        result = {
            "symbol": forms.bare,
            "interval": interval,
            "source": "sahmk",
            "count": len(candles),
            "total": payload.get("total"),
            "candles": candles,
        }
        redis_client.set_json(cache_key, result, ttl_seconds=300)

        if persist and candles:
            self._persist_csv(forms.bare, candles)

        return result

    async def warm_universe(self, symbols: list[str], limit: int = 365) -> dict[str, Any]:
        ok = 0
        failed: list[str] = []
        for sym in symbols:
            try:
                out = await self.get_candles(sym, limit=limit, persist=True)
                if out["count"] > 0:
                    ok += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("Historical warm failed for %s: %s", sym, exc)
                failed.append(sym)
        return {"ok": True, "warmed": ok, "failed": failed, "requested": len(symbols)}

    def _persist_csv(self, symbol: str, candles: list[dict[str, Any]]) -> None:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            path = DATA_DIR / f"{symbol}_1d.csv"
            pd.DataFrame(candles).rename(
                columns={"time": "trade_date"}
            ).to_csv(path, index=False)
        except Exception as exc:  # noqa: BLE001
            logger.debug("CSV persist failed for %s: %s", symbol, exc)
