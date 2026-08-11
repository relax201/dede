"""WebSocket /ws/live — تحديثات لحظية من بث سهمك (fan-out داخل العملية)"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.domain.symbols import normalize_symbol
from app.infrastructure.external.sahmk_ws import get_sahmk_stream

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []
        self.subscriptions: dict[WebSocket, set[str]] = {}

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.append(websocket)
        self.subscriptions[websocket] = set()

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active:
            self.active.remove(websocket)
        self.subscriptions.pop(websocket, None)

    async def broadcast(self, message: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        symbol = str(message.get("symbol", "")).upper() if message.get("symbol") else None
        for ws in list(self.active):
            wanted = self.subscriptions.get(ws) or set()
            # Empty set = receive all; otherwise filter quotes by symbol
            if symbol and wanted and symbol not in wanted and message.get("type") == "quote":
                continue
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


@router.websocket("/ws/live")
async def websocket_live(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        await websocket.send_json(
            {
                "type": "ready",
                "message": 'متصل بتاسي فيجن — أرسل {"action":"subscribe","symbols":["2222"]}',
                "sahmk_stream": _stream_snapshot(),
            }
        )

        while True:
            data = await websocket.receive_json()
            action = data.get("action") or data.get("type")
            symbols_raw = data.get("symbols") or data.get("subscribe") or []
            if isinstance(symbols_raw, str):
                symbols_raw = [symbols_raw]

            if action == "subscribe" or "subscribe" in data:
                symbols = [normalize_symbol(s).bare for s in symbols_raw]
                manager.subscriptions[websocket].update(symbols)
                stream = get_sahmk_stream()
                if stream is not None and symbols:
                    await stream.subscribe(symbols)
                await websocket.send_json(
                    {
                        "ok": True,
                        "action": "subscribe",
                        "subscribed": sorted(manager.subscriptions[websocket]),
                        "upstream": "sahmk_ws" if stream else None,
                    }
                )
            elif action == "unsubscribe":
                symbols = [normalize_symbol(s).bare for s in symbols_raw]
                manager.subscriptions[websocket].difference_update(symbols)
                stream = get_sahmk_stream()
                if stream is not None and symbols:
                    await stream.unsubscribe(symbols)
                await websocket.send_json(
                    {
                        "ok": True,
                        "action": "unsubscribe",
                        "subscribed": sorted(manager.subscriptions[websocket]),
                    }
                )
            elif action == "ping" or data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            else:
                await websocket.send_json(
                    {
                        "error": "unknown_action",
                        "hint": 'استخدم {"action":"subscribe","symbols":["2222"]}',
                    }
                )
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


def _stream_snapshot() -> dict[str, Any]:
    stream = get_sahmk_stream()
    if stream is None:
        return {"enabled": False}
    return {"enabled": True, **stream.stats}
