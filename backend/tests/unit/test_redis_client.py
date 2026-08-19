"""Unit tests — Redis fail-open / local disable"""

from __future__ import annotations

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-chars!!")
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/tasi_test.db")

from app.infrastructure.cache.redis_client import RedisClient, _is_local_redis


def test_local_redis_urls_detected() -> None:
    assert _is_local_redis("redis://127.0.0.1:6379/0")
    assert _is_local_redis("redis://localhost:6379/0")
    assert not _is_local_redis("redis://redis.railway.internal:6379/0")


def test_local_redis_client_skips_network() -> None:
    client = RedisClient(url="redis://127.0.0.1:6379/0")
    assert client.enabled is False
    assert client.get_json("any") is None
    client.set_json("any", {"a": 1}, ttl_seconds=5)  # no-op
    assert client.incr_with_expire("rl:x") == 0
    assert client.ping() is False
