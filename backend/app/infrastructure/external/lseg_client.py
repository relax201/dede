"""LSEG Pro — daily history + live failover (every 10s). Symbol: 2222.SR"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.domain.symbols import to_provider_symbol
from app.infrastructure.external.base import LiveQuote

logger = logging.getLogger(__name__)


class LsegClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 8.0,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.LSEG_API_KEY
        self.base_url = (base_url or settings.LSEG_BASE_URL).rstrip("/")
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def get_quote(self, symbol: str) -> LiveQuote:
        if not self.configured:
            raise RuntimeError("LSEG_API_KEY is not configured")
        ric = to_provider_symbol(symbol, "lseg")
        url = f"{self.base_url}/data/quotes"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"symbols": ric}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=headers, params=params)
                resp.raise_for_status()
                payload = resp.json()
        except httpx.HTTPError as exc:
            logger.error("LSEG quote failed for %s: %s", ric, exc)
            raise

        row = _first_row(payload)
        bare = ric.replace(".SR", "")
        return LiveQuote(
            symbol_bare=bare,
            price=float(row["price"] if "price" in row else row["close"]),
            change_pct=float(row.get("change_pct", 0.0)),
            volume=float(row.get("volume", 0.0)),
            high=float(row["high"]) if row.get("high") is not None else None,
            low=float(row["low"]) if row.get("low") is not None else None,
            ts=datetime.now(timezone.utc),
            source="lseg",
            stale=False,
            raw=row,
        )

    async def get_daily_history(
        self,
        symbol: str,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Historical OHLCV for ClickHouse ohlcv_daily."""
        if not self.configured:
            raise RuntimeError("LSEG_API_KEY is not configured")
        ric = to_provider_symbol(symbol, "lseg")
        url = f"{self.base_url}/data/historical/ohlc"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {
            "symbol": ric,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "interval": "1d",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
        rows = data if isinstance(data, list) else data.get("data", [])
        return list(rows)


def _first_row(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list) and payload:
        return payload[0]
    if isinstance(payload, dict):
        if "data" in payload and payload["data"]:
            return payload["data"][0]
        return payload
    raise ValueError("Unexpected LSEG payload shape")
