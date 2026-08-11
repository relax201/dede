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
