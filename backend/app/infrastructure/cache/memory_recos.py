"""In-process recommendation list cache."""

from __future__ import annotations

import threading
import time
from typing import Any

_lock = threading.Lock()
_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}


def put(key: str, rows: list[dict[str, Any]], ttl: float = 180.0) -> None:
    with _lock:
        _cache[key] = (time.time() + ttl, rows)


def get(key: str) -> list[dict[str, Any]] | None:
    with _lock:
        item = _cache.get(key)
        if not item:
            return None
        expires, rows = item
        if time.time() > expires:
            _cache.pop(key, None)
            return None
        return list(rows)
