"""signals/price_action.py icin sentetik veri testleri."""

from __future__ import annotations

import numpy as np

from signals.price_action import generate_signals
from tests.conftest import append_bars, make_flat_range_df


def test_entry_long_fires_on_confirmed_breakout():
    base = make_flat_range_df(n=25, price=100.0, half_range=1.0, volume=1000.0)
    breakout = append_bars(
        base,
        # govde >= 2x onceki ortalama VE hacim >= 1.5x onceki ortalama
        [{"Open": 100.0, "High": 116.0, "Low": 99.5, "Close": 115.0, "Volume": 8000.0}],
    )
    signals = generate_signals(breakout)
    assert bool(signals["entry_long"].iloc[-1]) is True


def test_entry_blocked_without_volume_confirmation():
    base = make_flat_range_df(n=25, price=100.0, half_range=1.0, volume=1000.0)
    breakout = append_bars(
        base,
        [{"Open": 100.0, "High": 116.0, "Low": 99.5, "Close": 115.0, "Volume": 900.0}],
    )
    signals = generate_signals(breakout)
    assert bool(signals["entry_long"].iloc[-1]) is False


def test_stop_and_target_formula():
    base = make_flat_range_df(n=25, price=100.0, half_range=1.0, volume=1000.0)
    breakout = append_bars(
        base,
        [{"Open": 100.0, "High": 116.0, "Low": 99.5, "Close": 115.0, "Volume": 8000.0}],
    )
    signals = generate_signals(breakout, risk_reward=2.0)
    row = signals.iloc[-1]
    assert np.isclose(row["stop_long"], 99.5)  # bar dusugu
    expected_target = 115.0 + 2.0 * (115.0 - 99.5)
    assert np.isclose(row["target_long"], expected_target)


def test_entry_short_symmetric():
    base = make_flat_range_df(n=25, price=100.0, half_range=1.0, volume=1000.0)
    breakdown = append_bars(
        base,
        [{"Open": 100.0, "High": 100.5, "Low": 84.0, "Close": 85.0, "Volume": 8000.0}],
    )
    signals = generate_signals(breakdown)
    assert bool(signals["entry_short"].iloc[-1]) is True
    assert bool(signals["entry_long"].iloc[-1]) is False
