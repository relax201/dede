"""Fetch and cache OHLCV from SAHMK for charts / ML prep."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from app.domain.symbols import normalize_symbol
from app.infrastructure.cache.redis_client import redis_client
from app.infrastructure.external.sahmk_client import SahmkClient

logger = logging.getLogger(__name__)

DATA_DIR = Path("/tmp/tasi_ohlcv")
ALLOWED_INTERVALS = frozenset({"1d", "1w", "1m", "30m", "60m"})
INTRADAY = frozenset({"30m", "60m"})


def _bar_time(raw: Any, *, intraday: bool) -> str | int | None:
    """Normalize SAHMK bar time for lightweight-charts."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if not intraday and len(text) >= 10 and text[4] == "-" and "T" not in text[:11]:
        return text[:10]
    # Intraday / ISO → unix seconds (UTC)
    try:
        if text.isdigit():
            ts = int(text)
            return ts // 1000 if ts > 1e12 else ts
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except ValueError:
        return text[:10] if len(text) >= 10 else text


class HistoricalService:
    def __init__(self, client: SahmkClient | None = None) -> None:
        self.client = client or SahmkClient()

    async def get_candles(
        self,
        symbol: str,
        interval: str = "1d",
        limit: int = 365,
        persist: bool = True,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> dict[str, Any]:
        forms = normalize_symbol(symbol)
        interval = interval if interval in ALLOWED_INTERVALS else "1d"
        cache_key = f"candles:{forms.bare}:{interval}:{limit}:{from_date or ''}:{to_date or ''}"
        cached = redis_client.get_json(cache_key)
        if isinstance(cached, dict) and cached.get("candles"):
            return cached

        payload = await self.client.get_historical(
            forms.bare,
            interval=interval,
            limit=limit,
            from_date=from_date,
            to_date=to_date,
        )
        rows = payload.get("data") or []
        intraday = interval in INTRADAY
        candles = []
        for r in rows:
            t = _bar_time(r.get("date"), intraday=intraday)
            if t is None or r.get("open") is None:
                continue
            candles.append(
                {
                    "time": t,
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"]),
                    "volume": float(r.get("volume") or 0),
                }
            )
        # Charts expect ascending time
        candles.sort(key=lambda c: c["time"])

        result = {
            "symbol": forms.bare,
            "interval": interval,
            "source": "sahmk",
            "count": len(candles),
            "total": payload.get("total") or payload.get("count"),
            "from": payload.get("from") or from_date,
            "to": payload.get("to") or to_date,
            "candles": candles,
        }
        ttl = 60 if intraday else 300
        redis_client.set_json(cache_key, result, ttl_seconds=ttl)

        if persist and candles and interval == "1d":
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
