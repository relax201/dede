"""
Build the widest SAHMK WebSocket universe allowed by the current plan.

Pro: max 60 symbols / connection (no wildcard).
Enterprise: may use symbols=["*"].
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings
from app.domain.symbols import normalize_symbol
from app.infrastructure.external.sahmk_ws import DEFAULT_SEED_SYMBOLS

logger = logging.getLogger(__name__)

# Large-cap / high-interest TASI names kept as priority anchors
PRIORITY_SYMBOLS: tuple[str, ...] = (
    "2222",  # أرامكو
    "1120",  # الراجحي
    "1180",  # الأهلي
    "1010",  # الرياض
    "1050",  # الفرنسي
    "1060",  # الأول
    "1150",  # الإنماء
    "2010",  # سابك
    "1211",  # معادن
    "2020",  # سابك للمغذيات
    "2350",  # كيان
    "2310",  # سبكيم
    "2290",  # ينساب
    "2380",  # بترو رابغ
    "7010",  # STC
    "7020",  # زين
    "7030",  # موبايلي
    "2082",  # أكوا باور
    "7203",  # علم
    "4002",  # المواساة
    "4001",  # سليمان الحبيب
    "2280",  # المراعي
    "2281",  # تنمية
    "4030",  # البحري
    "5110",  # كهرباء السعودية
    "4300",  # دار الأركان
    "4321",  # رتال
    "4260",  # بلوماكس
    "4261",  # ذيب
    "1111",  # تداول
)


async def fetch_market_symbols(limit: int = 50) -> list[str]:
    """Merge volume + value leaders from SAHMK market endpoints."""
    if not settings.SAHMK_API_KEY:
        return []

    headers = {"X-API-Key": settings.SAHMK_API_KEY}
    base = settings.SAHMK_BASE_URL.rstrip("/")
    symbols: list[str] = []

    async with httpx.AsyncClient(timeout=20.0) as client:
        for path, key in (
            ("/market/volume/", "stocks"),
            ("/market/value/", "stocks"),
            ("/market/gainers/", "gainers"),
            ("/market/losers/", "losers"),
        ):
            try:
                resp = await client.get(
                    f"{base}{path}",
                    headers=headers,
                    params={"index": "TASI", "limit": min(limit, 50)},
                )
                resp.raise_for_status()
                payload: dict[str, Any] = resp.json()
                rows = payload.get(key) or payload.get("stocks") or payload.get("results") or []
                for row in rows:
                    sym = row.get("symbol")
                    if sym:
                        symbols.append(normalize_symbol(str(sym)).bare)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Universe fetch failed for %s: %s", path, exc)

    return symbols


async def fetch_tasi_company_symbols(max_pages: int = 5, page_size: int = 50) -> list[str]:
    """Paginate /companies/?market=TASI for broader coverage fill."""
    if not settings.SAHMK_API_KEY:
        return []
    headers = {"X-API-Key": settings.SAHMK_API_KEY}
    base = settings.SAHMK_BASE_URL.rstrip("/")
    out: list[str] = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for page in range(max_pages):
            offset = page * page_size
            try:
                resp = await client.get(
                    f"{base}/companies/",
                    headers=headers,
                    params={
                        "market": "TASI",
                        "limit": page_size,
                        "offset": offset,
                        "status": "active",
                    },
                )
                resp.raise_for_status()
                payload = resp.json()
                rows = payload.get("results") or []
                if not rows:
                    break
                for row in rows:
                    if row.get("is_etf"):
                        continue
                    if str(row.get("security_type", "Equity")).lower() not in {"equity", ""}:
                        continue
                    sym = row.get("symbol")
                    if sym:
                        out.append(normalize_symbol(str(sym)).bare)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Companies page fetch failed offset=%s: %s", offset, exc)
                break
    return out


async def build_ws_universe(max_symbols: int | None = None) -> list[str]:
    """
    Widest practical universe for the active plan.
    Priority: configured seeds → blue chips → volume/value leaders → company list fill.
    """
    cap = max_symbols or settings.SAHMK_WS_MAX_SYMBOLS
    ordered: list[str] = []
    seen: set[str] = set()

    def add_many(items: list[str] | tuple[str, ...]) -> None:
        for raw in items:
            try:
                bare = normalize_symbol(raw).bare
            except ValueError:
                continue
            if bare in seen:
                continue
            seen.add(bare)
            ordered.append(bare)

    add_many(settings.sahmk_ws_seed_symbols)
    add_many(PRIORITY_SYMBOLS)
    add_many(DEFAULT_SEED_SYMBOLS)
    add_many(await fetch_market_symbols(limit=50))
    if len(ordered) < cap:
        add_many(await fetch_tasi_company_symbols(max_pages=6, page_size=50))

    universe = ordered[:cap]
    logger.info("Built SAHMK WS universe size=%s (cap=%s)", len(universe), cap)
    return universe
