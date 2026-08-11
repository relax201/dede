"""Company universe endpoints — sync & list from SAHMK"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import DbSession, rate_limit
from app.domain.services.company_sync_service import CompanySyncService
from app.domain.services.historical_service import HistoricalService
from app.infrastructure.external.sahmk_ws import get_sahmk_stream

router = APIRouter(tags=["companies"])


@router.get("/companies", summary="قائمة شركات تاسي (من الكاش/المزامنة)")
async def list_companies(
    sector: str | None = Query(default=None),
    q: str | None = Query(default=None, description="بحث بالرمز أو الاسم"),
    _: None = Depends(rate_limit),
) -> dict:
    service = CompanySyncService(db=None)
    rows = service.list_cached()
    if not rows:
        # lazy sync if cache empty
        try:
            synced = await CompanySyncService(db=None).sync_tasi(enrich_sectors=False)
            rows = service.list_cached() or synced.get("sample") or []
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"تعذر جلب الشركات: {exc}",
            ) from exc

    if sector and sector != "الكل":
        rows = [r for r in rows if r.get("sector") == sector]
    if q:
        qq = q.strip().lower()
        rows = [
            r
            for r in rows
            if qq in str(r.get("symbol", "")).lower()
            or qq in str(r.get("name_ar", "")).lower()
            or qq in str(r.get("name_en", "")).lower()
        ]
    return {"count": len(rows), "results": rows}


@router.post("/companies/sync", summary="مزامنة شركات تاسي من سهمك")
async def sync_companies(
    db: DbSession,
    enrich_sectors: bool = Query(default=True),
    _: None = Depends(rate_limit),
) -> dict:
    service = CompanySyncService(db=db)
    try:
        return await service.sync_tasi(enrich_sectors=enrich_sectors, enrich_limit=60)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/stock/{symbol}/candles", summary="شموع تاريخية من سهمك")
async def stock_candles(
    symbol: str,
    interval: str = Query(default="1d"),
    limit: int = Query(default=120, ge=5, le=2000),
    _: None = Depends(rate_limit),
) -> dict:
    service = HistoricalService()
    try:
        return await service.get_candles(symbol, interval=interval, limit=limit)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"فشل جلب الشموع: {exc}") from exc


@router.post("/market/warm-history", summary="تسخين التاريخ لكون البث الحالي")
async def warm_history(
    limit: int = Query(default=120, ge=5, le=2000),
    _: None = Depends(rate_limit),
) -> dict:
    stream = get_sahmk_stream()
    symbols = list(stream._desired_ordered) if stream is not None else ["2222", "1120", "1180"]
    service = HistoricalService()
    return await service.warm_universe(symbols, limit=limit)
