"""MarketAux Professional — news + sentiment feed. Symbol: bare 2222"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.domain.symbols import to_provider_symbol
from app.infrastructure.external.base import NewsItem

logger = logging.getLogger(__name__)


class MarketAuxClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.MARKETAUX_API_KEY
        self.base_url = (base_url or settings.MARKETAUX_BASE_URL).rstrip("/")
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def fetch_news(self, symbol: str, limit: int = 20) -> list[NewsItem]:
        if not self.configured:
            raise RuntimeError("MARKETAUX_API_KEY is not configured")
        bare = to_provider_symbol(symbol, "marketaux")
        url = f"{self.base_url}/news/all"
        params = {
            "api_token": self.api_key,
            "symbols": bare,
            "language": "ar,en",
            "limit": limit,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                payload = resp.json()
        except httpx.HTTPError as exc:
            logger.error("MarketAux news failed for %s: %s", bare, exc)
            raise

        items: list[NewsItem] = []
        for row in payload.get("data", []):
            published = row.get("published_at") or row.get("publishedAt")
            try:
                ts = datetime.fromisoformat(str(published).replace("Z", "+00:00"))
            except (TypeError, ValueError):
                ts = datetime.now(timezone.utc)
            entities = row.get("entities") or []
            score = None
            if entities:
                score = float(entities[0].get("sentiment_score", 0.0))
            items.append(
                NewsItem(
                    symbol_bare=bare,
                    headline=str(row.get("title", "")),
                    published_at=ts,
                    url=str(row.get("url", "")),
                    source="marketaux",
                    sentiment_score=score,
                )
            )
        return items
