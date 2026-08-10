"""Market overview endpoint used by Dashboard"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, rate_limit
from app.domain.services.stock_service import StockService
from app.schemas.stock import MarketOverview

router = APIRouter(tags=["market"])


@router.get("/market/overview", response_model=MarketOverview, summary="نظرة عامة على السوق")
async def market_overview(db: DbSession, _: None = Depends(rate_limit)) -> MarketOverview:
    return StockService(db).market_overview()
