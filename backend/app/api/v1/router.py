"""API v1 router aggregation"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import auth, companies, market, portfolio, recommendation, stock, stream
from app.infrastructure.cache import memory_quotes
from app.infrastructure.cache.redis_client import redis_client
from app.infrastructure.db.session import ping_db

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(stock.router)
api_router.include_router(recommendation.router)
api_router.include_router(portfolio.router)
api_router.include_router(market.router)
api_router.include_router(stream.router)
api_router.include_router(companies.router)


@api_router.get("/health/detail", tags=["health"], summary="فحص الصحة التفصيلي")
async def health_detail() -> dict:
    import asyncio

    from app.core.release import RELEASE
    from app.infrastructure.db.session import db_url_kind

    redis_ok = False
    try:
        redis_ok = await asyncio.wait_for(asyncio.to_thread(redis_client.ping), timeout=0.5)
    except Exception:  # noqa: BLE001
        redis_ok = False
    try:
        postgres_ok = await asyncio.wait_for(asyncio.to_thread(ping_db), timeout=1.0)
    except Exception:  # noqa: BLE001
        postgres_ok = False
    return {
        "status": "ok",
        "version": RELEASE,
        "db": db_url_kind(),
        "postgres": bool(postgres_ok),
        "redis": bool(redis_ok),
        "memory_quotes": memory_quotes.stats(),
    }
