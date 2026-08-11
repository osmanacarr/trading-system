"""gozcu/market_hours.py icin testler (bilinen UTC zaman noktalari)."""

from __future__ import annotations

import datetime as dt

from gozcu import market_hours


def test_is_bist_open_during_session_weekday():
    now = dt.datetime(2024, 5, 15, 8, 0, tzinfo=dt.timezone.utc)  # Carsamba, 11:00 TRT
    assert market_hours.is_bist_open(now) is True


def test_is_bist_open_false_outside_session():
    now = dt.datetime(2024, 5, 15, 16, 0, tzinfo=dt.timezone.utc)  # Carsamba, 19:00 TRT
    assert market_hours.is_bist_open(now) is False


def test_is_bist_open_false_on_weekend():
    now = dt.datetime(2024, 5, 18, 8, 0, tzinfo=dt.timezone.utc)  # Cumartesi
    assert market_hours.is_bist_open(now) is False


def test_is_nasdaq_open_handles_dst_summer_and_winter():
    # Ayni UTC saat (14:00), farkli DST rejimlerinde farkli ET saatine denk gelir.
    summer = dt.datetime(2024, 7, 15, 14, 0, tzinfo=dt.timezone.utc)  # EDT: 10:00 ET -> seans icinde
    winter = dt.datetime(2024, 1, 15, 14, 0, tzinfo=dt.timezone.utc)  # EST: 09:00 ET -> seans acilmadan once
    assert market_hours.is_nasdaq_open(summer) is True
    assert market_hours.is_nasdaq_open(winter) is False


def test_bist_elapsed_fraction_midsession_between_0_and_1():
    now = dt.datetime(2024, 5, 15, 11, 0, tzinfo=dt.timezone.utc)  # 14:00 TRT
    fraction = market_hours.bist_elapsed_fraction(now)
    assert 0.0 < fraction < 1.0


def test_elapsed_fraction_clips_to_0_and_1():
    before_open = dt.datetime(2024, 5, 15, 5, 0, tzinfo=dt.timezone.utc)  # 08:00 TRT
    after_close = dt.datetime(2024, 5, 15, 20, 0, tzinfo=dt.timezone.utc)  # 23:00 TRT
    assert market_hours.bist_elapsed_fraction(before_open) == 0.0
    assert market_hours.bist_elapsed_fraction(after_close) == 1.0
