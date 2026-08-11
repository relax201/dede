"""
SAHMK (سهمك) WebSocket stock stream
Endpoint: wss://api.sahmk.sa/ws/v1/stocks/?api_key=...
Docs: https://www.sahmk.sa/en/developers/docs
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import websockets
from websockets.asyncio.client import ClientConnection
from websockets.exceptions import ConnectionClosed

from app.core.config import settings
from app.domain.symbols import normalize_symbol

logger = logging.getLogger(__name__)

QuoteHandler = Callable[[dict[str, Any]], Awaitable[None] | None]

# Seed universe when not using Enterprise wildcard
DEFAULT_SEED_SYMBOLS: tuple[str, ...] = (
    "2222",  # أرامكو
    "1120",  # الراجحي
    "1180",  # الأهلي
    "1010",  # الرياض
    "2010",  # سابك
    "1211",  # معادن
    "2350",  # كيان
    "1050",  # السعودي الفرنسي
    "1060",  # الأول
    "1150",  # الإنماء
    "7020",  # زين
    "7010",  # STC
    "4030",  # البحري
    "2280",  # المراعي
    "4002",  # المواساة
)


class SahmkStockStream:
    """
    Production-oriented SAHMK stocks WebSocket client:
    - auto reconnect with exponential backoff
    - ping keepalive
    - subscribe / unsubscribe (chunked by max_symbols_per_call)
    - quote callback for Redis / fan-out
    """

    def __init__(
        self,
        api_key: str | None = None,
        ws_url: str | None = None,
        on_quote: QuoteHandler | None = None,
        on_event: QuoteHandler | None = None,
        subscribe_all: bool | None = None,
        seed_symbols: list[str] | None = None,
        ping_interval: float = 20.0,
        max_backoff: float = 60.0,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.SAHMK_API_KEY
        self.ws_base = (ws_url or settings.SAHMK_WS_URL).rstrip("?")
        self.on_quote = on_quote
        self.on_event = on_event
        self.subscribe_all = (
            settings.SAHMK_WS_SUBSCRIBE_ALL if subscribe_all is None else subscribe_all
        )
        self.seed_symbols = [
            normalize_symbol(s).bare
            for s in (seed_symbols or list(settings.sahmk_ws_seed_symbols) or list(DEFAULT_SEED_SYMBOLS))
        ]
        self.ping_interval = ping_interval
        self.max_backoff = max_backoff
        self.max_symbols = settings.SAHMK_WS_MAX_SYMBOLS

        self._desired_ordered: list[str] = list(dict.fromkeys(self.seed_symbols))
        self._desired: set[str] = set(self._desired_ordered)
        self._ws: ClientConnection | None = None
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self._connected = asyncio.Event()
        self._lock = asyncio.Lock()
        self._limits: dict[str, Any] = {
            "max_symbols_per_connection": 60,
            "max_symbols_per_call": 20,
        }
        self.stats: dict[str, Any] = {
            "connected": False,
            "plan": None,
            "quotes_received": 0,
            "last_quote_at": None,
            "last_error": None,
            "reconnects": 0,
            "subscribed": list(self._desired_ordered),
            "universe_size": len(self._desired_ordered),
            "mode": "wildcard" if self.subscribe_all else "universe",
        }

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    @property
    def connection_url(self) -> str:
        base = self.ws_base
        if "api_key=" in base:
            return base
        sep = "&" if "?" in base else "?"
        return f"{base}{sep}{urlencode({'api_key': self.api_key})}"

    def start(self) -> asyncio.Task[None] | None:
        if not self.configured:
            logger.warning("SAHMK WS not started — missing SAHMK_API_KEY")
            return None
        if self._task and not self._task.done():
            return self._task
        self._stop.clear()
        self._task = asyncio.create_task(self._run_forever(), name="sahmk-stock-stream")
        return self._task

    async def stop(self) -> None:
        self._stop.set()
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:  # noqa: BLE001
                pass
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self._task.cancel()
            self._task = None
        self.stats["connected"] = False
        self._connected.clear()

    def set_universe(self, symbols: list[str]) -> None:
        """Replace desired subscription set (truncated to plan/connection cap)."""
        cap = min(self.max_symbols, int(self._limits.get("max_symbols_per_connection") or self.max_symbols))
        ordered: list[str] = []
        seen: set[str] = set()
        for raw in symbols:
            try:
                bare = normalize_symbol(raw).bare
            except ValueError:
                continue
            if bare not in seen:
                seen.add(bare)
                ordered.append(bare)
        self._desired_ordered = ordered[:cap]
        self._desired = set(self._desired_ordered)
        self.stats["universe_size"] = len(self._desired_ordered)
        self.stats["mode"] = "wildcard" if self.subscribe_all else "universe"
        self.stats["subscribed"] = list(self._desired_ordered)

    async def expand_to_plan_limit(self) -> list[str]:
        """Build and apply the widest universe allowed by the active plan."""
        from app.infrastructure.external.sahmk_universe import build_ws_universe

        cap = min(self.max_symbols, int(self._limits.get("max_symbols_per_connection") or self.max_symbols))
        universe = await build_ws_universe(max_symbols=cap)
        self.set_universe(universe)
        if self._ws is not None and not self.subscribe_all:
            await self._resync_subscriptions()
        return list(self._desired_ordered)

    async def subscribe(self, symbols: list[str]) -> None:
        bares = [normalize_symbol(s).bare for s in symbols]
        cap = min(self.max_symbols, int(self._limits.get("max_symbols_per_connection") or self.max_symbols))
        async with self._lock:
            for b in bares:
                if b not in self._desired:
                    self._desired_ordered.append(b)
                    self._desired.add(b)
            if len(self._desired_ordered) > cap:
                self._desired_ordered = self._desired_ordered[:cap]
                self._desired = set(self._desired_ordered)
            self.stats["universe_size"] = len(self._desired_ordered)
            self.stats["subscribed"] = list(self._desired_ordered)
            if self._ws is not None and not self.subscribe_all:
                await self._send_subscribe(bares)

    async def unsubscribe(self, symbols: list[str]) -> None:
        bares = [normalize_symbol(s).bare for s in symbols]
        async with self._lock:
            self._desired.difference_update(bares)
            self._desired_ordered = [s for s in self._desired_ordered if s not in set(bares)]
            self.stats["subscribed"] = list(self._desired_ordered)
            self.stats["universe_size"] = len(self._desired_ordered)
            if self._ws is not None and bares:
                await self._send({"action": "unsubscribe", "symbols": bares})

    async def wait_connected(self, timeout: float = 15.0) -> bool:
        try:
            await asyncio.wait_for(self._connected.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def _run_forever(self) -> None:
        backoff = 1.0
        while not self._stop.is_set():
            try:
                await self._connect_session()
                backoff = 1.0
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                self.stats["last_error"] = str(exc)
                self.stats["connected"] = False
                self._connected.clear()
                logger.exception("SAHMK WS session error: %s", exc)
            if self._stop.is_set():
                break
            self.stats["reconnects"] += 1
            logger.info("SAHMK WS reconnecting in %.1fs", backoff)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=backoff)
            except asyncio.TimeoutError:
                pass
            backoff = min(backoff * 2, self.max_backoff)

    async def _connect_session(self) -> None:
        logger.info("Connecting SAHMK WS → %s", self.ws_base)
        async with websockets.connect(
            self.connection_url,
            ping_interval=None,  # application-level ping
            max_size=2_000_000,
            open_timeout=20,
        ) as ws:
            self._ws = ws
            ping_task = asyncio.create_task(self._ping_loop(ws))
            try:
                async for raw in ws:
                    if self._stop.is_set():
                        break
                    await self._handle_message(raw)
            finally:
                ping_task.cancel()
                self._ws = None
                self.stats["connected"] = False
                self._connected.clear()

    async def _ping_loop(self, ws: ClientConnection) -> None:
        while not self._stop.is_set():
            await asyncio.sleep(self.ping_interval)
            try:
                await ws.send(json.dumps({"action": "ping"}))
            except ConnectionClosed:
                return
            except Exception as exc:  # noqa: BLE001
                logger.debug("SAHMK ping failed: %s", exc)
                return

    async def _handle_message(self, raw: str | bytes) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("SAHMK WS non-JSON frame: %s", raw[:200])
            return

        msg_type = msg.get("type")
        if msg_type == "connected":
            self.stats["connected"] = True
            self.stats["plan"] = msg.get("plan")
            if isinstance(msg.get("limits"), dict):
                self._limits.update(msg["limits"])
                # Clamp desired set to connection limit announced by SAHMK
                conn_cap = int(self._limits.get("max_symbols_per_connection") or self.max_symbols)
                if len(self._desired_ordered) > conn_cap:
                    self.set_universe(self._desired_ordered[:conn_cap])
            self._connected.set()
            logger.info(
                "SAHMK WS connected plan=%s limits=%s universe=%s",
                msg.get("plan"),
                self._limits,
                len(self._desired),
            )
            if self.on_event:
                await _maybe_await(self.on_event(msg))
            await self._resync_subscriptions()
            return

        if msg_type == "pong":
            return

        if msg_type == "quote":
            self.stats["quotes_received"] += 1
            self.stats["last_quote_at"] = datetime.now(timezone.utc).isoformat()
            if self.on_quote:
                await _maybe_await(self.on_quote(msg))
            return

        if msg_type in {"subscribed", "unsubscribed", "error", "info"}:
            if msg_type == "error":
                self.stats["last_error"] = str(msg)
                logger.error("SAHMK WS error frame: %s", msg)
                # Auto-fallback when wildcard not entitled (Pro plan)
                code = msg.get("code")
                if code == "plan_not_entitled" and self.subscribe_all:
                    logger.warning(
                        "Wildcard subscribe not entitled — falling back to max universe (%s)",
                        self._limits.get("max_symbols_per_connection"),
                    )
                    self.subscribe_all = False
                    self.stats["mode"] = "universe"
                    await self.expand_to_plan_limit()
            if self.on_event:
                await _maybe_await(self.on_event(msg))
            return

        # Unknown / passthrough
        if self.on_event:
            await _maybe_await(self.on_event(msg))

    async def _resync_subscriptions(self) -> None:
        async with self._lock:
            if self.subscribe_all:
                await self._send({"action": "subscribe", "symbols": ["*"]})
                self.stats["subscribed"] = ["*"]
                return
            symbols = list(self._desired_ordered)
            self.stats["subscribed"] = symbols
            await self._send_subscribe(symbols)

    async def _send_subscribe(self, symbols: list[str]) -> None:
        if not symbols:
            return
        chunk = int(self._limits.get("max_symbols_per_call") or 40)
        for i in range(0, len(symbols), chunk):
            batch = symbols[i : i + chunk]
            await self._send({"action": "subscribe", "symbols": batch})

    async def _send(self, payload: dict[str, Any]) -> None:
        if self._ws is None:
            return
        await self._ws.send(json.dumps(payload, ensure_ascii=False))


async def _maybe_await(result: Any) -> None:
    if asyncio.iscoroutine(result):
        await result


# Process-wide singleton used by FastAPI lifespan and /ws/live
sahmk_stream: SahmkStockStream | None = None


def get_sahmk_stream() -> SahmkStockStream | None:
    return sahmk_stream
