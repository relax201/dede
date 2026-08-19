"""
SAHMK (سهمك) Enterprise — primary live quotes
Docs: https://www.sahmk.sa/en/developers/docs
Auth: X-API-Key header (shmk_live_* / shmk_test_*)
Base: https://api.sahmk.sa/api/v1
WS:   wss://api.sahmk.sa/ws/v1/stocks/?api_key=...
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.domain.symbols import to_provider_symbol
from app.infrastructure.external.base import LiveQuote

logger = logging.getLogger(__name__)


class SahmkClient:
    """Primary realtime provider. Symbol form: bare code e.g. 2222."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 8.0,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.SAHMK_API_KEY
        self.base_url = (base_url or settings.SAHMK_BASE_URL).rstrip("/")
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key, "Accept": "application/json"}

    async def get_quote(self, symbol: str) -> LiveQuote:
        if not self.configured:
            raise RuntimeError("SAHMK_API_KEY is not configured")
        bare = to_provider_symbol(symbol, "sahmk")
        url = f"{self.base_url}/quote/{bare}/"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=self._headers())
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()
        except httpx.HTTPError as exc:
            logger.error("SAHMK quote failed for %s: %s", bare, exc)
            raise

        return LiveQuote(
            symbol_bare=str(data.get("symbol", bare)),
            price=float(data["price"]),
            change_pct=float(data.get("change_percent", data.get("change_pct", 0.0))),
            volume=float(data.get("volume", 0.0)),
            high=float(data["high"]) if data.get("high") is not None else None,
            low=float(data["low"]) if data.get("low") is not None else None,
            ts=_parse_ts(data.get("updated_at") or data.get("timestamp")),
            source="sahmk",
            stale=bool(data.get("is_delayed", False)),
            raw=data,
        )

    async def get_market_summary(self, index: str = "TASI") -> dict[str, Any]:
        """GET /market/summary/?index=TASI"""
        if not self.configured:
            raise RuntimeError("SAHMK_API_KEY is not configured")
        url = f"{self.base_url}/market/summary/"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                url,
                headers=self._headers(),
                params={"index": index},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_quotes_batch(self, symbols: list[str]) -> list[dict[str, Any]]:
        """GET /quotes/?symbols=2222,1120 — up to 50 symbols."""
        if not self.configured:
            raise RuntimeError("SAHMK_API_KEY is not configured")
        bares = [to_provider_symbol(s, "sahmk") for s in symbols]
        url = f"{self.base_url}/quotes/"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                url,
                headers=self._headers(),
                params={"symbols": ",".join(bares)},
            )
            resp.raise_for_status()
            payload = resp.json()
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            return list(payload.get("data", payload.get("quotes", [])))
        return []

    async def list_companies(
        self,
        market: str = "TASI",
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """GET /companies/?market=TASI"""
        if not self.configured:
            raise RuntimeError("SAHMK_API_KEY is not configured")
        url = f"{self.base_url}/companies/"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                url,
                headers=self._headers(),
                params={"market": market, "limit": limit, "offset": offset, "status": "active"},
            )
            resp.raise_for_status()
            return resp.json()

    async def iter_all_companies(self, market: str = "TASI", page_size: int = 50) -> list[dict[str, Any]]:
        """Paginate all active companies for a market."""
        out: list[dict[str, Any]] = []
        offset = 0
        while True:
            page = await self.list_companies(market=market, limit=page_size, offset=offset)
            rows = page.get("results") or []
            if not rows:
                break
            out.extend(rows)
            total = int(page.get("total") or 0)
            offset += len(rows)
            if total and offset >= total:
                break
            if len(rows) < page_size:
                break
        return out

    async def get_company(self, symbol: str) -> dict[str, Any]:
        """GET /company/{symbol}/ — includes sector names."""
        if not self.configured:
            raise RuntimeError("SAHMK_API_KEY is not configured")
        bare = to_provider_symbol(symbol, "sahmk")
        url = f"{self.base_url}/company/{bare}/"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    async def get_historical(
        self,
        symbol: str,
        interval: str = "1d",
        limit: int = 365,
        offset: int = 0,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> dict[str, Any]:
        """GET /historical/{symbol}/ — OHLCV bars (1d/1w/1m/30m/60m)."""
        if not self.configured:
            raise RuntimeError("SAHMK_API_KEY is not configured")
        bare = to_provider_symbol(symbol, "sahmk")
        url = f"{self.base_url}/historical/{bare}/"
        params: dict[str, Any] = {"interval": interval, "limit": limit, "offset": offset}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._headers(),
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_depth(self, symbol: str, levels: int = 10) -> dict[str, Any]:
        """GET /market/depth/{symbol}/ — order book (entitlement-gated, levels 1–20)."""
        if not self.configured:
            raise RuntimeError("SAHMK_API_KEY is not configured")
        bare = to_provider_symbol(symbol, "sahmk")
        url = f"{self.base_url}/market/depth/{bare}/"
        lvl = max(1, min(int(levels), 20))
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                url,
                headers=self._headers(),
                params={"levels": lvl},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_trades(self, symbol: str, limit: int = 50) -> dict[str, Any]:
        """GET /market/trades/{symbol}/ — recent live trade prints (Pro+, limit 1–200)."""
        if not self.configured:
            raise RuntimeError("SAHMK_API_KEY is not configured")
        bare = to_provider_symbol(symbol, "sahmk")
        url = f"{self.base_url}/market/trades/{bare}/"
        lim = max(1, min(int(limit), 200))
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                url,
                headers=self._headers(),
                params={"limit": lim},
            )
            resp.raise_for_status()
            return resp.json()


def _parse_ts(value: Any) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:
            ts /= 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)
