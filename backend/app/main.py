"""
FastAPI entrypoint — تاسي فيجن (TASI Vision)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.websockets.live import router as ws_router

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("tasi.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    try:
        from app.infrastructure.db.session import ensure_schema

        ensure_schema()
    except Exception as exc:  # noqa: BLE001
        logger.error("Schema bootstrap failed (API will degrade): %s", exc)

    stream = None
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
        if settings.SAHMK_WS_AUTO_UNIVERSE and not settings.SAHMK_WS_SUBSCRIBE_ALL:
            try:
                universe = await stream.expand_to_plan_limit()
                logger.info("SAHMK WS auto-universe ready: %s symbols", len(universe))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Auto-universe build failed, using seeds: %s", exc)

        sahmk_ws_mod.sahmk_stream = stream
        stream.start()
        logger.info(
            "SAHMK WebSocket stream starting (mode=%s, universe=%s, subscribe_all=%s)",
            stream.stats.get("mode"),
            stream.stats.get("universe_size"),
            stream.subscribe_all,
        )
    else:
        logger.warning("SAHMK WebSocket disabled or SAHMK_API_KEY missing")

    yield

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
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(ws_router)


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


@app.get("/", tags=["root"])
async def root() -> dict:
    return {
        "success": True,
        "app": settings.APP_NAME,
        "brand_ar": settings.BRAND_NAME_AR,
        "brand_en": settings.BRAND_NAME_EN,
        "version": settings.APP_VERSION,
        "docs": "/docs",
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
            "primary": settings.AWS_REGION_PRIMARY,
            "dr": settings.AWS_REGION_DR,
        },
        "endpoints": {
            "stock": f"{settings.API_V1_STR}/stock/{{symbol}}",
            "recommendation": f"{settings.API_V1_STR}/recommendation/{{symbol}}?horizon=5",
            "portfolio": f"{settings.API_V1_STR}/portfolio",
            "portfolio_performance": f"{settings.API_V1_STR}/portfolio/{{id}}/performance",
            "stream_status": f"{settings.API_V1_STR}/stream/status",
            "websocket": "/ws/live",
        },
    }
