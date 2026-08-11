"""research/regime.py testleri - sentetik veriyle (Modul 4)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from research import regime
from signals import donchian
from tests.conftest import append_bars, build_donchian_trailing_exit_df, make_flat_range_df


def test_atr_percentile_series_values_within_0_100():
    df = make_flat_range_df(n=60, price=100.0, half_range=2.0)
    pct = regime.compute_atr_percentile_series(df, period=5, lookback=20)
    valid = pct.dropna()
    assert not valid.empty
    assert (valid >= 0).all() and (valid <= 100).all()


def test_atr_percentile_series_spikes_near_100_after_volatility_burst():
    base = make_flat_range_df(n=40, price=100.0, half_range=0.5, volume=1000.0)
    volatile_bars = [
        {"Open": 100.0, "High": 100 + 10 + i, "Low": 100 - 10 - i, "Close": 100.0, "Volume": 1000.0}
        for i in range(5)
    ]
    df = append_bars(base, volatile_bars)
    pct = regime.compute_atr_percentile_series(df, period=5, lookback=30)
    assert pct.iloc[-1] > 90


def test_regime_labels_none_during_warmup():
    df = make_flat_range_df(n=15, price=100.0, half_range=1.0)
    labels = regime.compute_regime_labels(df, period=5, lookback=20)
    assert pd.isna(labels.iloc[0])


def test_regime_labels_assigns_low_normal_high_thresholds():
    df = make_flat_range_df(n=60, price=100.0, half_range=2.0)
    pct = regime.compute_atr_percentile_series(df, period=5, lookback=20)
    labels = regime.compute_regime_labels(df, period=5, lookback=20, low_threshold=33.0, high_threshold=67.0)
    valid_idx = pct.dropna().index
    for date in valid_idx:
        p = pct.loc[date]
        label = labels.loc[date]
        if p < 33.0:
            assert label == "low"
        elif p > 67.0:
            assert label == "high"
        else:
            assert label == "normal"


def test_regime_labels_only_contains_known_labels_or_none():
    df = make_flat_range_df(n=60, price=100.0, half_range=2.0)
    labels = regime.compute_regime_labels(df, period=5, lookback=20)
    unique = set(labels.dropna().unique())
    assert unique.issubset(set(regime.REGIME_LABELS))


def test_backtest_by_regime_groups_single_trade_into_its_label():
    df = build_donchian_trailing_exit_df()
    signals = donchian.generate_signals(df)
    all_high_regime = pd.Series("high", index=df.index)

    result = regime.backtest_by_regime(df, signals, "donchian", all_high_regime)

    assert set(result.keys()) == {"high"}
    assert result["high"]["n_trades"] == 1
    assert result["high"]["expectancy_r"] > 0  # bu senaryodaki islem karli kapaniyor


def test_backtest_by_regime_empty_trades_returns_empty_dict():
    df = make_flat_range_df(n=40, price=100.0, half_range=1.0, volume=1000.0)
    signals = donchian.generate_signals(df)
    regime_labels = pd.Series("normal", index=df.index)

    result = regime.backtest_by_regime(df, signals, "donchian", regime_labels)
    assert result == {}


def test_backtest_by_regime_excludes_none_labels():
    df = build_donchian_trailing_exit_df()
    signals = donchian.generate_signals(df)
    all_none_regime = pd.Series([None] * len(df), index=df.index)

    result = regime.backtest_by_regime(df, signals, "donchian", all_none_regime)
    assert result == {}


def test_backtest_by_regime_does_not_mutate_input_signals():
    df = build_donchian_trailing_exit_df()
    signals = donchian.generate_signals(df)
    signals_copy = signals.copy()
    regime_labels = pd.Series("high", index=df.index)

    regime.backtest_by_regime(df, signals, "donchian", regime_labels)
    pd.testing.assert_frame_equal(signals, signals_copy)
