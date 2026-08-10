"""WebSocket /ws/live — تحديثات لحظية للأسعار والتوصيات"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.infrastructure.cache.redis_client import redis_client

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        data = json.dumps(message, default=str, ensure_ascii=False)
        for ws in self.active:
            try:
                await ws.send_text(data)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


@router.websocket("/ws/live")
async def websocket_live(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    pubsub = None
    try:
        # Client may send subscribe filter: {"subscribe": ["2222.SR", "1120.SR"]}
        pubsub = redis_client.client.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe("ws:channel:live")

        async def reader() -> None:
            while True:
                message = pubsub.get_message(timeout=0.01)
                if message and message.get("type") == "message":
                    raw = message.get("data")
                    try:
                        payload = json.loads(raw) if isinstance(raw, str) else raw
                    except json.JSONDecodeError:
                        payload = {"raw": raw}
                    await websocket.send_json(payload)
                await asyncio.sleep(0.05)

        reader_task = asyncio.create_task(reader())
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                except json.JSONDecodeError:
                    await websocket.send_json({"error": "invalid_json"})
                    continue
                if "subscribe" in msg:
                    await websocket.send_json({"ok": True, "subscribed": msg["subscribe"]})
                elif msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
        finally:
            reader_task.cancel()
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as exc:  # noqa: BLE001
        logger.exception("WebSocket error: %s", exc)
        try:
            await websocket.close(code=1011)
        except Exception:  # noqa: BLE001
            pass
    finally:
        manager.disconnect(websocket)
        if pubsub is not None:
            try:
                pubsub.close()
            except Exception:  # noqa: BLE001
                pass
