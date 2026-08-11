"""Unit tests — symbol normalization + market session helper"""

from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-chars!!")
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost:5432/tasi")

from app.domain.market_session import is_market_open
from app.domain.symbols import normalize_symbol, to_provider_symbol


def test_normalize_bare_and_lseg() -> None:
    forms = normalize_symbol("2222.SR")
    assert forms.bare == "2222"
    assert forms.lseg == "2222.SR"
    assert forms.display == "2222"


def test_provider_mapping() -> None:
    assert to_provider_symbol("2222", "sahmk") == "2222"
    assert to_provider_symbol("2222", "marketaux") == "2222"
    assert to_provider_symbol("2222", "lseg") == "2222.SR"
    assert to_provider_symbol("2222.sr", "lseg") == "2222.SR"


def test_market_open_sunday_midday() -> None:
    # 2026-08-09 was a Sunday in some calendars — use explicit weekday
    # 2024-01-07 is Sunday
    sunday_noon = datetime(2024, 1, 7, 12, 0, tzinfo=ZoneInfo("Asia/Riyadh"))
    assert is_market_open(sunday_noon) is True


def test_market_closed_friday() -> None:
    friday = datetime(2024, 1, 5, 12, 0, tzinfo=ZoneInfo("Asia/Riyadh"))
    assert is_market_open(friday) is False
