"""GET /api/recommendation/{symbol}"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import DbSession, rate_limit
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
    _: None = Depends(rate_limit),
) -> RecommendationResponse:
    service = RecommendationService(db)
    try:
        return service.get_by_symbol(symbol)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="فشل توليد التوصية",
        ) from exc
