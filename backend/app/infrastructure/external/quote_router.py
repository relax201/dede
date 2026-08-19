"""
Quote router with session-aware pricing and failover

أثناء التداول: SAHMK (3s) → LSEG (10s) → Tadawul → Redis
بعد الإغلاق: LSEG close → Redis
"""

from __future__ import annotations

import logging
from datetime import datetime

from app.core.config import settings
from app.domain.market_session import RIYADH, is_market_open
from app.domain.symbols import normalize_symbol
from app.infrastructure.cache import memory_quotes
from app.infrastructure.cache.redis_client import redis_client
from app.infrastructure.external.base import LiveQuote
from app.infrastructure.external.lseg_client import LsegClient
from app.infrastructure.external.sahmk_client import SahmkClient
from app.infrastructure.external.tadawul_client import TadawulClient

logger = logging.getLogger(__name__)


class QuoteRouter:
    """Unified quote access with provider failover and Redis fallback."""

    def __init__(
        self,
        sahmk: SahmkClient | None = None,
        lseg: LsegClient | None = None,
        tadawul: TadawulClient | None = None,
    ) -> None:
        self.sahmk = sahmk or SahmkClient()
        self.lseg = lseg or LsegClient()
        self.tadawul = tadawul or TadawulClient()

    async def get_quote(self, symbol: str) -> LiveQuote:
        forms = normalize_symbol(symbol)
        # Prefer fresh WS/memory tick when available (works even if Redis is down)
        mem = memory_quotes.get_quote(forms.bare)
        if isinstance(mem, dict) and "price" in mem:
            return self._quote_from_cached(forms.bare, mem, stale=False)
        if is_market_open():
            return await self._in_session(forms.bare)
        return await self._after_close(forms.bare)

    def _quote_from_cached(self, bare: str, cached: dict, *, stale: bool) -> LiveQuote:
        ts_raw = cached.get("ts")
        try:
            ts = datetime.fromisoformat(str(ts_raw)) if ts_raw else datetime.now(RIYADH)
        except ValueError:
            ts = datetime.now(RIYADH)
        return LiveQuote(
            symbol_bare=bare,
            price=float(cached["price"]),
            change_pct=float(cached.get("change_pct") or 0.0),
            volume=float(cached.get("volume") or 0.0),
            high=float(cached["high"]) if cached.get("high") is not None else None,
            low=float(cached["low"]) if cached.get("low") is not None else None,
            ts=ts,
            source="redis_cache",
            stale=stale,
            raw=cached,
        )

    async def _in_session(self, bare: str) -> LiveQuote:
        # 1) SAHMK primary
        if self.sahmk.configured:
            try:
                quote = await self.sahmk.get_quote(bare)
                self._cache(quote)
                return quote
            except Exception as exc:  # noqa: BLE001
                logger.warning("SAHMK failover → LSEG for %s: %s", bare, exc)

        # 2) LSEG every ~10s failover
        if self.lseg.configured:
            try:
                quote = await self.lseg.get_quote(bare)
                self._cache(quote)
                return quote
            except Exception as exc:  # noqa: BLE001
                logger.warning("LSEG failover → Tadawul for %s: %s", bare, exc)

        # 3) Tadawul
        if self.tadawul.configured:
            try:
                quote = await self.tadawul.get_quote(bare)
                self._cache(quote)
                return quote
            except Exception as exc:  # noqa: BLE001
                logger.warning("Tadawul failed for %s: %s", bare, exc)

        return self._from_redis_or_raise(bare)

    async def _after_close(self, bare: str) -> LiveQuote:
        # Official close from LSEG preferred; SAHMK last print as practical fallback
        if self.lseg.configured:
            try:
                quote = await self.lseg.get_quote(bare)
                self._cache(quote)
                return quote
            except Exception as exc:  # noqa: BLE001
                logger.warning("After-close LSEG failed for %s: %s", bare, exc)

        if self.sahmk.configured:
            try:
                quote = await self.sahmk.get_quote(bare)
                self._cache(quote)
                return quote
            except Exception as exc:  # noqa: BLE001
                logger.warning("After-close SAHMK fallback failed for %s: %s", bare, exc)

        return self._from_redis_or_raise(bare)

    def _cache(self, quote: LiveQuote) -> None:
        ttl = settings.SAHMK_TICK_INTERVAL_SECONDS * 4  # ~12s during session
        payload = {
            "price": quote.price,
            "change_pct": quote.change_pct,
            "volume": quote.volume,
            "high": quote.high,
            "low": quote.low,
            "ts": quote.ts.isoformat(),
            "source": quote.source,
        }
        memory_quotes.put_quote(quote.symbol_bare, payload)
        redis_client.set_json(
            f"quote:{quote.symbol_bare}",
            payload,
            ttl_seconds=max(ttl, 30),
        )

    def _from_redis_or_raise(self, bare: str) -> LiveQuote:
        cached = memory_quotes.get_quote(bare)
        if not (isinstance(cached, dict) and "price" in cached):
            cached = redis_client.get_json(f"quote:{bare}")
        if isinstance(cached, dict) and "price" in cached:
            return self._quote_from_cached(bare, cached, stale=True)
        raise LookupError(f"No live or cached quote available for {bare}")
