"""Redis cache-aside + pub/sub helpers"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self, url: str | None = None) -> None:
        self._url = url or settings.REDIS_URL
        self._client: redis.Redis | None = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.Redis.from_url(self._url, decode_responses=True)
        return self._client

    def get_json(self, key: str) -> dict[str, Any] | list[Any] | None:
        try:
            raw = self.client.get(key)
            return json.loads(raw) if raw else None
        except Exception as exc:  # noqa: BLE001 — graceful degradation
            logger.warning("Redis GET failed for %s: %s", key, exc)
            return None

    def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        try:
            self.client.setex(key, ttl_seconds, json.dumps(value, default=str, ensure_ascii=False))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis SET failed for %s: %s", key, exc)

    def publish(self, channel: str, payload: dict[str, Any]) -> None:
        try:
            self.client.publish(channel, json.dumps(payload, default=str, ensure_ascii=False))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis PUBLISH failed: %s", exc)

    def incr_with_expire(self, key: str, ttl_seconds: int = 60) -> int:
        pipe = self.client.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl_seconds)
        count, _ = pipe.execute()
        return int(count)


redis_client = RedisClient()
