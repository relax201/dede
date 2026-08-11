"""GET /api/stream/status — حالة بث سهمك WebSocket"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.infrastructure.external.sahmk_ws import get_sahmk_stream

router = APIRouter(tags=["stream"])


@router.get("/stream/status", summary="حالة بث SAHMK WebSocket")
async def stream_status() -> dict:
    stream = get_sahmk_stream()
    runtime = None if stream is None else stream.stats
    return {
        "enabled": settings.SAHMK_WS_ENABLED,
        "configured": bool(settings.SAHMK_API_KEY),
        "ws_url": settings.SAHMK_WS_URL,
        "subscribe_all": settings.SAHMK_WS_SUBSCRIBE_ALL,
        "auto_universe": settings.SAHMK_WS_AUTO_UNIVERSE,
        "max_symbols": settings.SAHMK_WS_MAX_SYMBOLS,
        "seed_symbols": settings.sahmk_ws_seed_symbols,
        "runtime": runtime,
        "subscribed_symbols": None if stream is None else list(stream._desired_ordered),
    }


@router.post("/stream/expand", summary="إعادة بناء أوسع تغذية مسموحة بالخطة")
async def stream_expand() -> dict:
    stream = get_sahmk_stream()
    if stream is None:
        return {"ok": False, "error": "stream_not_running"}
    universe = await stream.expand_to_plan_limit()
    return {
        "ok": True,
        "universe_size": len(universe),
        "symbols": universe,
        "runtime": stream.stats,
    }
