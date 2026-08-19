"""Company universe endpoints — sync & list from SAHMK"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import DbSession, rate_limit
from app.domain.services.company_sync_service import CompanySyncService
from app.domain.services.historical_service import ALLOWED_INTERVALS, HistoricalService
from app.domain.services.market_book_service import MarketBookService
from app.infrastructure.external.sahmk_ws import get_sahmk_stream

router = APIRouter(tags=["companies"])


@router.get("/companies", summary="قائمة شركات تاسي (من الكاش/المزامنة)")
async def list_companies(
    db: DbSession,
    sector: str | None = Query(default=None),
    q: str | None = Query(default=None, description="بحث بالرمز أو الاسم"),
    _: None = Depends(rate_limit),
) -> dict:
    service = CompanySyncService(db=db)
    rows = service.list_cached()
    if not rows:
        # lazy sync if cache empty — also upsert into Postgres/SQLite when available
        try:
            synced = await CompanySyncService(db=db).sync_tasi(enrich_sectors=True, enrich_limit=40)
            rows = service.list_cached() or list(synced.get("companies") or synced.get("sample") or [])
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


@router.get("/stock/{symbol}/candles", summary="شموع تاريخية من سهمك (OHLCV)")
async def stock_candles(
    symbol: str,
    interval: str = Query(default="1d", description="1d | 1w | 1m | 30m | 60m"),
    limit: int = Query(default=120, ge=5, le=2000),
    from_date: str | None = Query(default=None, alias="from", description="YYYY-MM-DD"),
    to_date: str | None = Query(default=None, alias="to", description="YYYY-MM-DD"),
    _: None = Depends(rate_limit),
) -> dict:
    if interval not in ALLOWED_INTERVALS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"interval غير مدعوم — استخدم: {', '.join(sorted(ALLOWED_INTERVALS))}",
        )
    service = HistoricalService()
    try:
        return await service.get_candles(
            symbol,
            interval=interval,
            limit=limit,
            from_date=from_date,
            to_date=to_date,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"فشل جلب الشموع: {exc}") from exc


@router.get("/stock/{symbol}/depth", summary="عمق السوق من سهمك (دفتر الأوامر)")
async def stock_depth(
    symbol: str,
    levels: int = Query(default=10, ge=1, le=20),
    _: None = Depends(rate_limit),
) -> dict:
    service = MarketBookService()
    try:
        return await service.get_depth(symbol, levels=levels)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"فشل جلب عمق السوق: {exc}") from exc


@router.get("/stock/{symbol}/trades", summary="سجل الصفقات من سهمك (Tape)")
async def stock_trades(
    symbol: str,
    limit: int = Query(default=40, ge=1, le=200),
    _: None = Depends(rate_limit),
) -> dict:
    service = MarketBookService()
    try:
        return await service.get_trades(symbol, limit=limit)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"فشل جلب سجل الصفقات: {exc}") from exc


@router.post("/market/warm-history", summary="تسخين التاريخ لكون البث الحالي")
async def warm_history(
    limit: int = Query(default=120, ge=5, le=2000),
    _: None = Depends(rate_limit),
) -> dict:
    stream = get_sahmk_stream()
    symbols = list(stream._desired_ordered) if stream is not None else ["2222", "1120", "1180"]
    service = HistoricalService()
    return await service.warm_universe(symbols, limit=limit)
