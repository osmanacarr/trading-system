"""signals/donchian.py icin sentetik veri testleri."""

from __future__ import annotations

import numpy as np
import pandas as pd

from signals.donchian import compute_donchian_channels, generate_signals
from tests.conftest import append_bars, make_flat_range_df


def test_channels_have_no_lookahead():
    df = make_flat_range_df(n=30)
    channels = compute_donchian_channels(df, entry_n=20, exit_n=10)
    # t barindaki entry_upper, yalnizca t'den ONCEKI 20 barin en yuksegi
    # olmali (t'nin kendi High'i haric)
    for i in range(21, 30):
        expected = df["High"].iloc[i - 20 : i].max()
        assert np.isclose(channels["entry_upper"].iloc[i], expected)


def test_entry_long_fires_on_confirmed_breakout():
    base = make_flat_range_df(n=25, price=100.0, half_range=1.0, volume=1000.0)
    # Guclu govdeli + yuksek hacimli acik kirilim bari
    breakout = append_bars(
        base,
        [{"Open": 101.0, "High": 116.0, "Low": 100.5, "Close": 115.0, "Volume": 6000.0}],
    )
    signals = generate_signals(breakout, entry_n=20, exit_n=10)
    assert bool(signals["entry_long"].iloc[-1]) is True
    assert bool(signals["entry_short"].iloc[-1]) is False


def test_entry_long_blocked_without_volume_confirmation():
    base = make_flat_range_df(n=25, price=100.0, half_range=1.0, volume=1000.0)
    # Fiyat kanali kirsa da hacim onayi yok (ortalamanin altinda)
    weak_breakout = append_bars(
        base,
        [{"Open": 101.0, "High": 116.0, "Low": 100.5, "Close": 115.0, "Volume": 500.0}],
    )
    signals = generate_signals(weak_breakout, entry_n=20, exit_n=10)
    assert bool(signals["entry_long"].iloc[-1]) is False


def test_entry_long_blocked_without_body_confirmation():
    base = make_flat_range_df(n=25, price=100.0, half_range=1.0, volume=1000.0)
    # Kirilim var, hacim var ama govde kucuk (dogi benzeri mum)
    small_body_breakout = append_bars(
        base,
        [{"Open": 101.4, "High": 116.0, "Low": 100.5, "Close": 101.5, "Volume": 6000.0}],
    )
    signals = generate_signals(small_body_breakout, entry_n=20, exit_n=10)
    # Close (101.5), entry_upper'i (~100.5) kirar ve hacim yeterlidir; ancak
    # govde (|Close-Open|=0.1) onceki 5 barin ortalama govdesinin 1.5 kati
    # kadar degildir -> govde filtresi tek basina sinyali engellemelidir.
    assert bool(signals["entry_long"].iloc[-1]) is False


def test_exit_long_level_matches_prior_10day_low():
    df = make_flat_range_df(n=35)
    signals = generate_signals(df, entry_n=20, exit_n=10)
    for i in range(11, 35):
        expected = df["Low"].iloc[i - 10 : i].min()
        assert np.isclose(signals["exit_long_level"].iloc[i], expected)


def test_missing_columns_raises():
    df = pd.DataFrame({"Close": [1, 2, 3]})
    try:
        generate_signals(df)
        assert False, "ValueError beklendi"
    except ValueError:
        pass
