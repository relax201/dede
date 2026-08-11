"""TASI trading session helpers — Asia/Riyadh"""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

RIYADH = ZoneInfo("Asia/Riyadh")
SESSION_OPEN = time(10, 0)
SESSION_CLOSE = time(15, 0)


def is_market_open(now: datetime | None = None) -> bool:
    """
    تقريب جلسة تاسي المستمرة: الأحد–الخميس 10:00–15:00.
    يُضبط لاحقاً حسب تقويم العطل الرسمي.
    """
    current = now.astimezone(RIYADH) if now else datetime.now(RIYADH)
    if current.weekday() not in (6, 0, 1, 2, 3):
        return False
    return SESSION_OPEN <= current.time() <= SESSION_CLOSE
