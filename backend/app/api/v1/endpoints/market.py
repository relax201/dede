"""Market overview endpoint used by Dashboard"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import rate_limit
from app.domain.services.stock_service import StockService
from app.schemas.stock import MarketOverview

router = APIRouter(tags=["market"])


@router.get("/market/overview", response_model=MarketOverview, summary="نظرة عامة على السوق")
async def market_overview(_: None = Depends(rate_limit)) -> MarketOverview:
    # db=None — overview must stay up even before Postgres is linked
    return await StockService(db=None).market_overview()  # type: ignore[arg-type]
