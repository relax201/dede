"""GET /api/stream/status — حالة بث سهمك WebSocket"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.infrastructure.external.sahmk_ws import get_sahmk_stream

router = APIRouter(tags=["stream"])


@router.get("/stream/status", summary="حالة بث SAHMK WebSocket")
async def stream_status() -> dict:
    stream = get_sahmk_stream()
    return {
        "enabled": settings.SAHMK_WS_ENABLED,
        "configured": bool(settings.SAHMK_API_KEY),
        "ws_url": settings.SAHMK_WS_URL,
        "subscribe_all": settings.SAHMK_WS_SUBSCRIBE_ALL,
        "seed_symbols": settings.sahmk_ws_seed_symbols,
        "runtime": None if stream is None else stream.stats,
    }
