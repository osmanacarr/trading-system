"""signals/ma_voting.py icin sentetik veri testleri (M4 - Kart 1)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from signals.ma_voting import compute_vote_series, generate_signals
from tests.conftest import make_flat_range_df

# Testlerde hizli warmup icin kucuk ciftler (varsayilan (50,200) 200 bar ister)
SMALL_PAIRS = [(3, 5), (5, 8), (8, 13)]


def _trend_df(n: int = 40, start: float = 100.0, step: float = 1.0, start_date: str = "2020-01-01") -> pd.DataFrame:
    dates = pd.date_range(start_date, periods=n, freq="B")
    close = start + step * np.arange(n)
    high = close + 0.5
    low = close - 0.5
    open_ = close - step / 2
    volume = np.full(n, 1000.0)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=dates)


def test_compute_vote_series_all_bullish_in_uptrend():
    df = _trend_df(n=40, step=1.0)
    votes = compute_vote_series(df, pairs=SMALL_PAIRS)
    assert votes.iloc[-1] == len(SMALL_PAIRS)


def test_compute_vote_series_all_bearish_in_downtrend():
    df = _trend_df(n=40, step=-1.0)
    votes = compute_vote_series(df, pairs=SMALL_PAIRS)
    assert votes.iloc[-1] == -len(SMALL_PAIRS)


def test_compute_vote_series_flat_price_gives_zero_votes():
    df = _trend_df(n=40, step=0.0)
    votes = compute_vote_series(df, pairs=SMALL_PAIRS)
    assert votes.iloc[-1] == 0


def _flat_then_trend(step: float) -> pd.DataFrame:
    flat = make_flat_range_df(n=20, price=100.0, half_range=0.1, volume=1000.0)
    trend = _trend_df(n=20, start=100.0, step=step, start_date=(flat.index[-1] + pd.tseries.offsets.BDay(1)).strftime("%Y-%m-%d"))
    return pd.concat([flat, trend])


def test_entry_long_fires_on_uptrend_and_no_entry_short():
    df = _flat_then_trend(step=1.0)
    signals = generate_signals(df, pairs=SMALL_PAIRS)
    trend_segment = signals.iloc[20:]  # yatay isinma sonrasi (gurultu barlarini disla)
    assert trend_segment["entry_long"].any()
    assert not trend_segment["entry_short"].any()


def test_entry_short_fires_on_downtrend_and_no_entry_long():
    df = _flat_then_trend(step=-1.0)
    signals = generate_signals(df, pairs=SMALL_PAIRS)
    trend_segment = signals.iloc[20:]
    assert trend_segment["entry_short"].any()
    assert not trend_segment["entry_long"].any()


def test_exit_long_signal_true_when_votes_non_positive():
    df = _trend_df(n=40, step=-1.0)
    signals = generate_signals(df, pairs=SMALL_PAIRS)
    assert bool(signals["exit_long_signal"].iloc[-1]) is True
    assert bool(signals["exit_short_signal"].iloc[-1]) is False


def test_exit_short_signal_true_when_votes_non_negative():
    df = _trend_df(n=40, step=1.0)
    signals = generate_signals(df, pairs=SMALL_PAIRS)
    assert bool(signals["exit_short_signal"].iloc[-1]) is True
    assert bool(signals["exit_long_signal"].iloc[-1]) is False


def test_stop_long_below_close_and_stop_short_above_close():
    df = _trend_df(n=40, step=1.0)
    signals = generate_signals(df, pairs=SMALL_PAIRS, atr_period=5, atr_stop_mult=2.0)
    row = signals.iloc[-1]
    close = df["Close"].iloc[-1]
    assert row["stop_long"] < close
    assert row["stop_short"] > close


def test_stop_distance_scales_with_atr_mult():
    df = _trend_df(n=40, step=1.0)
    tight = generate_signals(df, pairs=SMALL_PAIRS, atr_period=5, atr_stop_mult=1.0)
    wide = generate_signals(df, pairs=SMALL_PAIRS, atr_period=5, atr_stop_mult=3.0)
    close = df["Close"].iloc[-1]
    tight_dist = close - tight["stop_long"].iloc[-1]
    wide_dist = close - wide["stop_long"].iloc[-1]
    assert wide_dist > tight_dist


def test_vote_count_column_matches_compute_vote_series():
    df = _trend_df(n=40, step=1.0)
    signals = generate_signals(df, pairs=SMALL_PAIRS)
    votes = compute_vote_series(df, pairs=SMALL_PAIRS)
    pd.testing.assert_series_equal(signals["vote_count"], votes, check_names=False)


def test_missing_columns_raises():
    with pytest.raises(ValueError):
        generate_signals(pd.DataFrame({"Close": [1.0, 2.0]}))
