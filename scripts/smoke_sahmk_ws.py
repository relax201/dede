#!/usr/bin/env python3
"""Smoke test: connect to SAHMK stocks WebSocket and print events/quotes."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

# Load .env if present
env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from app.core.config import get_settings
from app.infrastructure.external.sahmk_ws import SahmkStockStream

get_settings.cache_clear()


async def main() -> None:
    quotes: list[dict] = []

    async def on_quote(msg: dict) -> None:
        quotes.append(msg)
        data = msg.get("data") or {}
        print(f"QUOTE {msg.get('symbol')} price={data.get('price')} latency_ms={msg.get('latency_ms')}")

    async def on_event(msg: dict) -> None:
        print(f"EVENT {msg.get('type')} {msg}")

    stream = SahmkStockStream(
        on_quote=on_quote,
        on_event=on_event,
        seed_symbols=["2222", "1120"],
        subscribe_all=False,
    )
    stream.start()
    ok = await stream.wait_connected(20)
    print("connected=", ok, "stats=", stream.stats)
    await asyncio.sleep(15)
    print("quotes_received=", len(quotes))
    await stream.stop()


if __name__ == "__main__":
    asyncio.run(main())
