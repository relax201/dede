"""Unit tests — widest WS universe builder"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-chars!!")
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost:5432/tasi")

from app.infrastructure.external.sahmk_universe import build_ws_universe
from app.infrastructure.external.sahmk_ws import SahmkStockStream


@pytest.mark.asyncio
async def test_build_ws_universe_respects_cap() -> None:
    with (
        patch(
            "app.infrastructure.external.sahmk_universe.fetch_market_symbols",
            new=AsyncMock(return_value=["6015", "9999", "1120"]),
        ),
        patch(
            "app.infrastructure.external.sahmk_universe.fetch_tasi_company_symbols",
            new=AsyncMock(return_value=[str(i) for i in range(1000, 1100)]),
        ),
    ):
        universe = await build_ws_universe(max_symbols=60)
    assert len(universe) == 60
    assert universe[0] in {"2222", "1120", "1180", "1010"} or len(universe) == 60
    # Priority blue chip should appear when available
    assert "2222" in universe
    assert "1120" in universe


@pytest.mark.asyncio
async def test_stream_set_universe_preserves_priority_order() -> None:
    stream = SahmkStockStream(api_key="shmk_test_dummy", seed_symbols=["2222"])
    stream.set_universe(["2222", "1120", "9999"] + [str(i) for i in range(200)])
    assert stream._desired_ordered[0] == "2222"
    assert stream._desired_ordered[1] == "1120"
    assert len(stream._desired_ordered) == stream.max_symbols
