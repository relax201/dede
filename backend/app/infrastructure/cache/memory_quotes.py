"""Process-local quote cache (survives Redis outages within one worker)"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any

_lock = threading.Lock()
_quotes: dict[str, dict[str, Any]] = {}


def put_quote(symbol: str, payload: dict[str, Any]) -> None:
    bare = str(symbol).strip().upper()
    if not bare:
        return
    with _lock:
        _quotes[bare] = {**payload, "symbol": bare}


def get_quote(symbol: str) -> dict[str, Any] | None:
    bare = str(symbol).strip().upper()
    with _lock:
        cached = _quotes.get(bare)
        return dict(cached) if cached else None


def stats() -> dict[str, Any]:
    with _lock:
        return {
            "size": len(_quotes),
            "symbols_sample": list(_quotes.keys())[:10],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
