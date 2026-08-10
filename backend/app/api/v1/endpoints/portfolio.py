"""POST /api/portfolio  |  GET /api/portfolio/{id}/performance"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, DbSession, rate_limit
from app.domain.services.portfolio_service import PortfolioService
from app.schemas.stock import (
    ErrorResponse,
    PortfolioCreate,
    PortfolioPerformanceResponse,
    PortfolioResponse,
)

router = APIRouter(tags=["portfolios"])


@router.post(
    "/portfolio",
    response_model=PortfolioResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}},
    summary="إنشاء محفظة وإضافة أسهم",
)
async def create_portfolio(
    payload: PortfolioCreate,
    db: DbSession,
    user: CurrentUser,
    _: None = Depends(rate_limit),
) -> PortfolioResponse:
    service = PortfolioService(db)
    try:
        return service.create(UUID(user["sub"]), payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"تعذر إنشاء المحفظة: {exc}",
        ) from exc


@router.get(
    "/portfolio/{portfolio_id}/performance",
    response_model=PortfolioPerformanceResponse,
    responses={404: {"model": ErrorResponse}},
    summary="أداء المحفظة",
)
async def portfolio_performance(
    portfolio_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: None = Depends(rate_limit),
) -> PortfolioPerformanceResponse:
    _ = user  # authorization hook: ensure ownership in production
    service = PortfolioService(db)
    try:
        return service.performance(portfolio_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
