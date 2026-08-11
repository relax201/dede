"""GET /api/recommendation/{symbol}?horizon=5|10|20"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import DbSession, rate_limit
from app.core.config import settings
from app.domain.services.recommendation_service import RecommendationService
from app.schemas.stock import ErrorResponse, RecommendationResponse

router = APIRouter(tags=["recommendations"])


@router.get(
    "/recommendation/{symbol}",
    response_model=RecommendationResponse,
    responses={404: {"model": ErrorResponse}},
    summary="التوصية الحالية مع تفسير SHAP",
)
async def get_recommendation(
    symbol: str,
    db: DbSession,
    horizon: Literal[5, 10, 20] = Query(
        default=5,
        description="أفق التوصية بالأيام — الأساسي 5، الاختياري 10 أو 20",
    ),
    _: None = Depends(rate_limit),
) -> RecommendationResponse:
    if horizon not in settings.forward_horizons:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"الأفق المسموح: {settings.forward_horizons}",
        )
    service = RecommendationService(db)
    try:
        reco = service.get_by_symbol(symbol, horizon_days=horizon)
        reco.disclaimer_ar = settings.LEGAL_DISCLAIMER_AR
        return reco
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="فشل توليد التوصية",
        ) from exc
