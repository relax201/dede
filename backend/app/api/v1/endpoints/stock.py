"""GET /api/stock/{symbol}"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import DbSession, rate_limit
from app.domain.services.stock_service import StockService
from app.schemas.stock import ErrorResponse, StockResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["stocks"])


@router.get(
    "/stock/{symbol}",
    response_model=StockResponse,
    responses={404: {"model": ErrorResponse}},
    summary="بيانات السهم (سعر، حجم، مؤشرات)",
)
async def get_stock(
    symbol: str,
    db: DbSession,
    _: None = Depends(rate_limit),
) -> StockResponse:
    service = StockService(db)
    try:
        return await service.get_stock(symbol)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("stock lookup failed for %s", symbol)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"فشل جلب بيانات السهم: {exc}",
        ) from exc
