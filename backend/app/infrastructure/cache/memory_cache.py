"""Tiny process-local TTL cache — used when Redis is unavailable."""

from __future__ import annotations

import threading
import time
from typing import Any


class MemoryTTLCache:
    def __init__(self) -> None:
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        now = time.monotonic()
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires, value = item
            if expires < now:
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        with self._lock:
            self._data[key] = (time.monotonic() + max(0.1, float(ttl_seconds)), value)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


memory_cache = MemoryTTLCache()
