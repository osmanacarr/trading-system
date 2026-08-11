"""gozcu/market_hours.py - BIST/NASDAQ piyasa-acik kontrolu ve seans-ici gecen sure orani.

dashboard/lib/market.ts: isBistOpen() ile AYNI basitlestirme felsefesi
(sadece hafta ici + saat araligi, resmi tatil takvimi haric) - burada Python
tarafinda, GitHub Actions'in DST-farkindaligi olmayan UTC cron'unu telafi
etmek icin kullanilir (bkz. gozcu/scanner.py modul docstring'i, Bolum 0
mimari karari). `zoneinfo` DST'yi (ozellikle NASDAQ/ABD icin) otomatik
dogru hesaplar - TR'de DST yok.
"""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from config import (
    GOZCU_BIST_CLOSE_TIME,
    GOZCU_BIST_OPEN_TIME,
    GOZCU_BIST_TIMEZONE,
    GOZCU_NASDAQ_CLOSE_TIME,
    GOZCU_NASDAQ_OPEN_TIME,
    GOZCU_NASDAQ_TIMEZONE,
)


def _to_minutes(t: tuple[int, int]) -> int:
    return t[0] * 60 + t[1]


def _local_now(now_utc: dt.datetime | None, tz_name: str) -> dt.datetime:
    now = now_utc if now_utc is not None else dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    return now.astimezone(ZoneInfo(tz_name))


def _is_open(now_utc: dt.datetime | None, tz_name: str, open_time: tuple[int, int], close_time: tuple[int, int]) -> bool:
    local = _local_now(now_utc, tz_name)
    if local.weekday() >= 5:  # Cmt=5, Paz=6
        return False
    minutes = local.hour * 60 + local.minute
    return _to_minutes(open_time) <= minutes <= _to_minutes(close_time)


def _elapsed_fraction(now_utc: dt.datetime | None, tz_name: str, open_time: tuple[int, int], close_time: tuple[int, int]) -> float:
    local = _local_now(now_utc, tz_name)
    minutes = local.hour * 60 + local.minute
    open_minutes = _to_minutes(open_time)
    close_minutes = _to_minutes(close_time)
    session_length = close_minutes - open_minutes
    if session_length <= 0:
        return 0.0
    fraction = (minutes - open_minutes) / session_length
    return max(0.0, min(1.0, fraction))


def is_bist_open(now_utc: dt.datetime | None = None) -> bool:
    """BIST'in su anda (yaklasik olarak) acik olup olmadigi - hafta ici 10:00-18:10 TRT."""
    return _is_open(now_utc, GOZCU_BIST_TIMEZONE, GOZCU_BIST_OPEN_TIME, GOZCU_BIST_CLOSE_TIME)


def is_nasdaq_open(now_utc: dt.datetime | None = None) -> bool:
    """NASDAQ'in su anda (yaklasik olarak) acik olup olmadigi - hafta ici 09:30-16:00 ET (DST'ye gore otomatik kayar)."""
    return _is_open(now_utc, GOZCU_NASDAQ_TIMEZONE, GOZCU_NASDAQ_OPEN_TIME, GOZCU_NASDAQ_CLOSE_TIME)


def bist_elapsed_fraction(now_utc: dt.datetime | None = None) -> float:
    """BIST seansinin ne kadarinin gectigi (0-1 arasi; RVOL hesaplamasinda kullanilir)."""
    return _elapsed_fraction(now_utc, GOZCU_BIST_TIMEZONE, GOZCU_BIST_OPEN_TIME, GOZCU_BIST_CLOSE_TIME)


def nasdaq_elapsed_fraction(now_utc: dt.datetime | None = None) -> float:
    """NASDAQ seansinin ne kadarinin gectigi (0-1 arasi; RVOL hesaplamasinda kullanilir)."""
    return _elapsed_fraction(now_utc, GOZCU_NASDAQ_TIMEZONE, GOZCU_NASDAQ_OPEN_TIME, GOZCU_NASDAQ_CLOSE_TIME)
