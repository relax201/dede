"""Shared types for market data connectors"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

QuoteSource = Literal["sahmk", "lseg", "tadawul", "alpha_vantage", "redis_cache"]


@dataclass(frozen=True)
class LiveQuote:
    symbol_bare: str
    price: float
    change_pct: float
    volume: float
    high: float | None
    low: float | None
    ts: datetime
    source: QuoteSource
    stale: bool = False
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class NewsItem:
    symbol_bare: str
    headline: str
    published_at: datetime
    url: str
    source: str = "marketaux"
    sentiment_score: float | None = None
