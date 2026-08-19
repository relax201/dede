"""GET /api/recommendation/{symbol}  |  GET /api/recommendations"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import DbSession, rate_limit
from app.core.config import settings
from app.domain.services.recommendation_service import RecommendationService
from app.infrastructure.external.sahmk_ws import get_sahmk_stream
from app.schemas.stock import ErrorResponse, RecommendationResponse

router = APIRouter(tags=["recommendations"])


@router.get(
    "/recommendations",
    summary="تحليلات لكون الأسهم الحالي",
)
async def list_recommendations(
    db: DbSession,
    horizon: int = Query(default=5),
    limit: int = Query(default=8, ge=1, le=20),
    _: None = Depends(rate_limit),
) -> dict:
    if horizon not in (5, 10, 20):
        raise HTTPException(status_code=400, detail="الأفق المسموح: 5, 10, 20")
    stream = get_sahmk_stream()
    symbols = list(settings.sahmk_ws_seed_symbols)
    if stream is not None:
        live = list(getattr(stream, "_desired_ordered", []) or [])
        if live:
            symbols = live
    symbols = symbols[:limit]
    service = RecommendationService(db)
    rows = await service.list_live(symbols, horizon_days=horizon)
    return {"count": len(rows), "horizon": horizon, "results": rows}


@router.get(
    "/recommendation/{symbol}",
    response_model=RecommendationResponse,
    responses={404: {"model": ErrorResponse}},
    summary="التوصية الحالية مع تفسير SHAP",
)
async def get_recommendation(
    symbol: str,
    db: DbSession,
    horizon: int = Query(
        default=5,
        description="أفق التوصية بالأيام — الأساسي 5، الاختياري 10 أو 20",
    ),
    _: None = Depends(rate_limit),
) -> RecommendationResponse:
    if horizon not in (5, 10, 20) or horizon not in settings.forward_horizons:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"الأفق المسموح: {settings.forward_horizons}",
        )
    service = RecommendationService(db)
    try:
        reco = await service.get_by_symbol(symbol, horizon_days=horizon)
        reco.disclaimer_ar = settings.LEGAL_DISCLAIMER_AR
        return reco
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"فشل توليد التوصية: {exc}",
        ) from exc
