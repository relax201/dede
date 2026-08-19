"""
FastAPI entrypoint — تاسي فيجن (TASI Vision)
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
for noisy in ("websockets", "websockets.client", "httpcore", "httpx"):
    logging.getLogger(noisy).setLevel(logging.WARNING)
logger = logging.getLogger("tasi.api")

STATIC_DIR = Path(os.environ.get("STATIC_DIR", "/app/static"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    from app.core.config import settings

    logger.info(
        "ready version=%s port=%s index=%s",
        settings.APP_VERSION,
        os.environ.get("PORT", "?"),
        (STATIC_DIR / "index.html").is_file(),
    )

    async def _warm() -> None:
        await asyncio.sleep(1)
        try:
            from app.infrastructure.db.session import ensure_schema

            await asyncio.wait_for(asyncio.to_thread(ensure_schema), timeout=5)
        except Exception as exc:  # noqa: BLE001
            logger.warning("schema skipped: %s", exc)
        if not (settings.SAHMK_WS_ENABLED and settings.SAHMK_API_KEY):
            logger.warning("SAHMK WS disabled")
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
            logger.info("SAHMK WS started")
            if settings.SAHMK_WS_AUTO_UNIVERSE and not settings.SAHMK_WS_SUBSCRIBE_ALL:
                await stream.expand_to_plan_limit()
                logger.info("SAHMK universe expanded")
        except Exception as exc:  # noqa: BLE001
            logger.exception("SAHMK warm failed: %s", exc)

    task = asyncio.create_task(_warm(), name="warm")
    yield
    if not task.done():
        task.cancel()
        try:
            await task
        except Exception:  # noqa: BLE001
            pass
    stream = getattr(app.state, "sahmk_stream", None)
    if stream is not None:
        try:
            await stream.stop()
        except Exception:  # noqa: BLE001
            pass


def create_app() -> FastAPI:
    from app.api.v1.router import api_router
    from app.core.config import settings
    from app.websockets.live import router as ws_router

    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/healthz")
    @application.get("/api/health")
    async def health() -> dict:
        return {
            "status": "ok",
            "version": settings.APP_VERSION,
            "static": (STATIC_DIR / "index.html").is_file(),
        }

    application.include_router(api_router, prefix=settings.API_V1_STR)
    application.include_router(ws_router)

    assets = STATIC_DIR / "assets"
    if assets.is_dir():
        application.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    @application.get("/")
    async def root():
        index = STATIC_DIR / "index.html"
        if index.is_file():
            return HTMLResponse(index.read_text(encoding="utf-8"))
        return JSONResponse(
            {
                "success": True,
                "app": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "message": "API live — UI not baked into image",
                "health": "/healthz",
                "docs": "/docs",
            }
        )

    @application.get("/{full_path:path}")
    async def spa(full_path: str):
        if full_path.startswith(("api/", "ws")) or full_path in {
            "docs",
            "redoc",
            "openapi.json",
            "healthz",
        }:
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = STATIC_DIR / full_path
        if candidate.is_file():
            data = candidate.read_bytes()
            media = "application/octet-stream"
            if full_path.endswith(".js"):
                media = "application/javascript"
            elif full_path.endswith(".css"):
                media = "text/css"
            elif full_path.endswith(".svg"):
                media = "image/svg+xml"
            elif full_path.endswith(".html"):
                media = "text/html"
            return Response(content=data, media_type=media)
        index = STATIC_DIR / "index.html"
        if index.is_file():
            return HTMLResponse(index.read_text(encoding="utf-8"))
        raise HTTPException(status_code=404, detail="Not Found")

    return application


app = create_app()
