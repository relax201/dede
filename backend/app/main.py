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
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("websockets.client").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("tasi.api")

STATIC_DIR = Path(os.environ.get("STATIC_DIR", "/app/static"))
API_PREFIXES = ("api/", "docs", "redoc", "openapi.json", "ws", "healthz")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Accept traffic immediately; warm DB/WS after a short delay."""
    import asyncio

    from app.core.config import settings

    logger.info(
        "Starting %s v%s PORT=%s STATIC=%s",
        settings.APP_NAME,
        settings.APP_VERSION,
        os.environ.get("PORT", "?"),
        STATIC_DIR,
    )
    logger.info("Static index present=%s", (STATIC_DIR / "index.html").is_file())

    async def _boot_background() -> None:
        await asyncio.sleep(1.5)
        try:
            from app.infrastructure.db.session import ensure_schema

            await asyncio.wait_for(asyncio.to_thread(ensure_schema), timeout=5.0)
        except Exception as exc:  # noqa: BLE001
            logger.error("Schema bootstrap failed/skipped: %s", exc)

        if not (settings.SAHMK_WS_ENABLED and settings.SAHMK_API_KEY):
            logger.warning("SAHMK WebSocket disabled or SAHMK_API_KEY missing")
            return
        try:
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
            stream.start()
            app.state.sahmk_stream = stream
            logger.info("SAHMK WebSocket started on seed universe")
            if settings.SAHMK_WS_AUTO_UNIVERSE and not settings.SAHMK_WS_SUBSCRIBE_ALL:
                universe = await stream.expand_to_plan_limit()
                logger.info("SAHMK WS auto-universe ready: %s symbols", len(universe))
        except Exception as exc:  # noqa: BLE001
            logger.error("SAHMK boot failed (API stays up): %s", exc)

    boot_task = asyncio.create_task(_boot_background(), name="tasi-boot")
    yield

    if not boot_task.done():
        boot_task.cancel()
        try:
            await boot_task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
    stream = getattr(app.state, "sahmk_stream", None)
    if stream is not None:
        try:
            await stream.stop()
        except Exception:  # noqa: BLE001
            pass
    logger.info("Shutting down API")


def create_app() -> FastAPI:
    from app.core.config import settings

    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "تاسي فيجن (TASI Vision) — أدوات تحليل لسوق الأسهم السعودي. "
            "لا تشكّل توصية استثمارية شخصية."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Ultra-light probes registered before heavy routers
    @application.get("/healthz", include_in_schema=False)
    @application.get("/api/health", tags=["health"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "version": settings.APP_VERSION}

    from app.api.v1.router import api_router
    from app.websockets.live import router as ws_router

    application.include_router(api_router, prefix=settings.API_V1_STR)
    application.include_router(ws_router)

    def _meta_payload() -> dict:
        return {
            "success": True,
            "app": settings.APP_NAME,
            "brand_ar": settings.BRAND_NAME_AR,
            "brand_en": settings.BRAND_NAME_EN,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "ui": "/",
            "static_index": (STATIC_DIR / "index.html").is_file(),
        }

    @application.get("/api/meta", tags=["root"])
    async def api_meta() -> dict:
        return _meta_payload()

    @application.get("/", include_in_schema=False, response_model=None)
    async def root():
        index = STATIC_DIR / "index.html"
        if index.is_file():
            try:
                return HTMLResponse(index.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed reading index.html: %s", exc)
        return JSONResponse(_meta_payload())

    assets = STATIC_DIR / "assets"
    if assets.is_dir():
        application.mount("/assets", StaticFiles(directory=assets), name="assets")

    @application.get("/{full_path:path}", include_in_schema=False, response_model=None)
    async def spa_fallback(full_path: str):
        if full_path.startswith(API_PREFIXES):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = STATIC_DIR / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        index = STATIC_DIR / "index.html"
        if index.is_file():
            return HTMLResponse(index.read_text(encoding="utf-8"))
        raise HTTPException(status_code=404, detail="Not Found")

    return application


app = create_app()
