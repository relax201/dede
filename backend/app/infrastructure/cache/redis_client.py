"""Redis cache-aside + pub/sub helpers with fail-open circuit breaker.

Sync redis calls must never stall the asyncio event loop for long: unreachable
REDIS_URL (common on Railway before Redis is linked) previously blocked every
request for the full socket timeout and made the site appear down.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any
from urllib.parse import urlparse

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)


def _is_local_redis(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:  # noqa: BLE001
        return True
    return host in {"", "localhost", "127.0.0.1", "::1", "0.0.0.0"}


class RedisClient:
    def __init__(self, url: str | None = None) -> None:
        self._url = url or settings.REDIS_URL
        self._client: redis.Redis | None = None
        self._lock = threading.Lock()
        # Localhost Redis is almost never available in Railway single-service deploys.
        self._enabled = bool(self._url) and not _is_local_redis(self._url)
        self._fail_count = 0
        self._disabled_until = 0.0
        self._last_error_log = 0.0
        if not self._enabled:
            logger.info("Redis disabled (local/empty URL) — using fail-open memory path")

    @property
    def enabled(self) -> bool:
        if not self._enabled:
            return False
        if time.monotonic() < self._disabled_until:
            return False
        return True

    def _trip(self, exc: Exception) -> None:
        self._fail_count += 1
        # Trip quickly: one timeout is enough to open the circuit for a while.
        backoff = min(120.0, 15.0 * max(1, self._fail_count))
        self._disabled_until = time.monotonic() + backoff
        now = time.monotonic()
        if now - self._last_error_log > 30:
            self._last_error_log = now
            logger.warning(
                "Redis unavailable — circuit open for %.0fs (%s)",
                backoff,
                exc,
            )
        # Drop broken connection so the next probe recreates it
        self._client = None

    def _recover(self) -> None:
        self._fail_count = 0
        self._disabled_until = 0.0

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.Redis.from_url(
                self._url,
                decode_responses=True,
                socket_connect_timeout=0.25,
                socket_timeout=0.25,
                retry_on_timeout=False,
                health_check_interval=30,
            )
        return self._client

    def get_json(self, key: str) -> dict[str, Any] | list[Any] | None:
        if not self.enabled:
            return None
        try:
            raw = self.client.get(key)
            self._recover()
            return json.loads(raw) if raw else None
        except Exception as exc:  # noqa: BLE001 — graceful degradation
            self._trip(exc)
            return None

    def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        if not self.enabled:
            return
        try:
            self.client.setex(key, ttl_seconds, json.dumps(value, default=str, ensure_ascii=False))
            self._recover()
        except Exception as exc:  # noqa: BLE001
            self._trip(exc)

    def publish(self, channel: str, payload: dict[str, Any]) -> None:
        if not self.enabled:
            return
        try:
            self.client.publish(channel, json.dumps(payload, default=str, ensure_ascii=False))
            self._recover()
        except Exception as exc:  # noqa: BLE001
            self._trip(exc)

    def incr_with_expire(self, key: str, ttl_seconds: int = 60) -> int:
        if not self.enabled:
            return 0
        try:
            pipe = self.client.pipeline()
            pipe.incr(key)
            pipe.expire(key, ttl_seconds)
            count, _ = pipe.execute()
            self._recover()
            return int(count)
        except Exception as exc:  # noqa: BLE001
            self._trip(exc)
            return 0

    def ping(self) -> bool:
        if not self._enabled:
            return False
        # Allow a probe even while circuit is open (half-open)
        try:
            ok = bool(self.client.ping())
            if ok:
                self._recover()
            return ok
        except Exception as exc:  # noqa: BLE001
            self._trip(exc)
            return False


redis_client = RedisClient()
