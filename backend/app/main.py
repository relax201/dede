"""
FastAPI entrypoint — TASI AI Platform
نقطة تشغيل الواجهة الخلفية (Clean Architecture)
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
    yield
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
            "websocket": "/ws/live",
        },
    }
