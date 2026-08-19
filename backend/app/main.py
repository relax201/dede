"""
FastAPI entrypoint — تاسي فيجن (TASI Vision)
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.websockets.live import router as ws_router

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
# Quiet noisy third-party DEBUG spam (headers/frames) even if DEBUG=true
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("websockets.client").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("tasi.api")

STATIC_DIR = Path(os.environ.get("STATIC_DIR", "/app/static"))
API_PREFIXES = ("api/", "docs", "redoc", "openapi.json", "ws")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Keep startup fast so Railway healthchecks pass; warm SAHMK in background."""
    import asyncio

    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    try:
        from app.infrastructure.db.session import ensure_schema

        await asyncio.wait_for(asyncio.to_thread(ensure_schema), timeout=8.0)
    except Exception as exc:  # noqa: BLE001
        logger.error("Schema bootstrap failed/skipped: %s", exc)

    stream = None
    warm_task: asyncio.Task | None = None
    if settings.SAHMK_WS_ENABLED and settings.SAHMK_API_KEY:
        from app.infrastructure.external import sahmk_ws as sahmk_ws_mod
        from app.infrastructure.external.sahmk_ws import SahmkStockStream
        from app.infrastructure.messaging.live_bridge import (
            handle_sahmk_event,
            handle_sahmk_quote,
        )

        stream = SahmkStockStream(
            on_quote=handle_sahmk_quote,
            on_event=handle_sahmk_event,
            ping_interval=settings.SAHMK_WS_PING_INTERVAL_SECONDS,
        )
        sahmk_ws_mod.sahmk_stream = stream
        # Start immediately on seed symbols — do NOT block healthchecks
        stream.start()
        logger.info("SAHMK WebSocket started on seed universe")

        async def _warm_universe() -> None:
            if not settings.SAHMK_WS_AUTO_UNIVERSE or settings.SAHMK_WS_SUBSCRIBE_ALL:
                return
            try:
                universe = await stream.expand_to_plan_limit()
                logger.info("SAHMK WS auto-universe ready: %s symbols", len(universe))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Auto-universe build failed, using seeds: %s", exc)

        warm_task = asyncio.create_task(_warm_universe(), name="sahmk-warm-universe")
    else:
        logger.warning("SAHMK WebSocket disabled or SAHMK_API_KEY missing")

    yield

    if warm_task is not None and not warm_task.done():
        warm_task.cancel()
        try:
            await warm_task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
    if stream is not None:
        logger.info("Stopping SAHMK WebSocket stream")
        await stream.stop()
    logger.info("Shutting down API")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "تاسي فيجن (TASI Vision) — أدوات تحليل لسوق الأسهم السعودي مع نماذج Ensemble وتفسير SHAP. "
        "لا تشكّل توصية استثمارية شخصية. التوثيق عبر OpenAPI/Swagger."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(ws_router)


def _meta_payload() -> dict:
    return {
        "success": True,
        "app": settings.APP_NAME,
        "brand_ar": settings.BRAND_NAME_AR,
        "brand_en": settings.BRAND_NAME_EN,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "ui": "/",
        "compliance": {
            "mode": settings.COMPLIANCE_MODE,
            "cma_preliminary_approval": settings.CMA_PRELIMINARY_APPROVAL,
            "disclaimer_ar": settings.LEGAL_DISCLAIMER_AR,
            "audit_retention_years": settings.AUDIT_RETENTION_YEARS,
        },
        "coverage": {
            "basic_target": settings.COVERAGE_BASIC_TARGET,
            "advanced_target": settings.COVERAGE_ADVANCED_TARGET,
        },
        "horizons": settings.forward_horizons,
        "cloud": {
            "host": "railway",
            "primary": settings.AWS_REGION_PRIMARY,
            "dr": settings.AWS_REGION_DR,
        },
        "endpoints": {
            "stock": f"{settings.API_V1_STR}/stock/{{symbol}}",
            "recommendation": f"{settings.API_V1_STR}/recommendation/{{symbol}}?horizon=5",
            "recommendations": f"{settings.API_V1_STR}/recommendations",
            "auth_register": f"{settings.API_V1_STR}/auth/register",
            "auth_login": f"{settings.API_V1_STR}/auth/login",
            "portfolio": f"{settings.API_V1_STR}/portfolio",
            "portfolio_performance": f"{settings.API_V1_STR}/portfolio/{{id}}/performance",
            "stream_status": f"{settings.API_V1_STR}/stream/status",
            "websocket": "/ws/live",
        },
    }


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "internal_error",
            "message": "حدث خطأ داخلي في الخادم" if not settings.DEBUG else str(exc),
        },
    )


@app.get("/api/meta", tags=["root"], summary="بيانات المنصة")
async def api_meta() -> dict:
    return _meta_payload()


@app.get("/", include_in_schema=False)
async def root() -> FileResponse | dict:
    index = STATIC_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    return _meta_payload()


if (STATIC_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    if full_path.startswith(API_PREFIXES):
        raise HTTPException(status_code=404, detail="Not Found")
    candidate = STATIC_DIR / full_path
    if candidate.is_file():
        return FileResponse(candidate)
    index = STATIC_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    raise HTTPException(status_code=404, detail="Not Found")
