"""API v1 router aggregation"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import companies, market, portfolio, recommendation, stock, stream

api_router = APIRouter()
api_router.include_router(stock.router)
api_router.include_router(recommendation.router)
api_router.include_router(portfolio.router)
api_router.include_router(market.router)
api_router.include_router(stream.router)
api_router.include_router(companies.router)


@api_router.get("/health", tags=["health"], summary="فحص الصحة")
async def health() -> dict[str, str]:
    return {"status": "ok"}
