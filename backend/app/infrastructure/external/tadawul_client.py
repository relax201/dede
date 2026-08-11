"""Tadawul API — tertiary live failover. Symbol: bare 2222"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.domain.symbols import to_provider_symbol
from app.infrastructure.external.base import LiveQuote

logger = logging.getLogger(__name__)


class TadawulClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 6.0,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.TADAWUL_API_KEY
        self.base_url = (base_url or settings.TADAWUL_BASE_URL).rstrip("/")
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def get_quote(self, symbol: str) -> LiveQuote:
        if not self.configured:
            raise RuntimeError("TADAWUL_API_KEY is not configured")
        bare = to_provider_symbol(symbol, "tadawul")
        url = f"{self.base_url}/market/quotes/{bare}"
        headers = {"X-API-Key": self.api_key}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()
        except httpx.HTTPError as exc:
            logger.error("Tadawul quote failed for %s: %s", bare, exc)
            raise

        return LiveQuote(
            symbol_bare=bare,
            price=float(data.get("lastPrice", data.get("price"))),
            change_pct=float(data.get("changePct", data.get("change_pct", 0.0))),
            volume=float(data.get("volume", 0.0)),
            high=float(data["high"]) if data.get("high") is not None else None,
            low=float(data["low"]) if data.get("low") is not None else None,
            ts=datetime.now(timezone.utc),
            source="tadawul",
            stale=False,
            raw=data,
        )
