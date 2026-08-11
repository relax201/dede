"""SAHMK Enterprise — primary live quotes (REST + WebSocket every 3s)"""

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
        timeout: float = 5.0,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.SAHMK_API_KEY
        self.base_url = (base_url or settings.SAHMK_BASE_URL).rstrip("/")
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def get_quote(self, symbol: str) -> LiveQuote:
        if not self.configured:
            raise RuntimeError("SAHMK_API_KEY is not configured")
        bare = to_provider_symbol(symbol, "sahmk")
        url = f"{self.base_url}/quotes/{bare}"
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()
        except httpx.HTTPError as exc:
            logger.error("SAHMK quote failed for %s: %s", bare, exc)
            raise

        return LiveQuote(
            symbol_bare=bare,
            price=float(data["price"]),
            change_pct=float(data.get("change_pct", data.get("changePercent", 0.0))),
            volume=float(data.get("volume", 0.0)),
            high=float(data["high"]) if data.get("high") is not None else None,
            low=float(data["low"]) if data.get("low") is not None else None,
            ts=_parse_ts(data.get("ts") or data.get("timestamp")),
            source="sahmk",
            stale=False,
            raw=data,
        )


def _parse_ts(value: Any) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, (int, float)):
        # seconds or ms
        ts = float(value)
        if ts > 1e12:
            ts /= 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)
