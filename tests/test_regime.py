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


# -- M5: ADX / trend-range rejim ekseni ------------------------------------


def _trend_df(n: int = 80, step: float = 1.0) -> pd.DataFrame:
    """Guclu, tek yonlu (dogrusal) trend - yuksek ADX beklenir."""
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    close = 100.0 + step * np.arange(n)
    high = close + 0.5
    low = close - 0.5
    open_ = close - step / 2
    volume = np.full(n, 1000.0)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=dates)


def _choppy_df(n: int = 80, amplitude: float = 5.0, period_bars: int = 10) -> pd.DataFrame:
    """Genlik/periyodu sabit bir sinus salinimi - genuine 'yon degistiren'
    (chop) veri; make_flat_range_df BURADA KULLANILMAZ cunku o fixture'in
    High/Low'u bar-bar SABIT kaliyor (bkz. tanimi) - bu, gercekci olmayan
    ("hicbir yon-hareketi yok") dejenere bir girdi ADX icin: DM bilesenleri
    ilk bardan sonra tam SIFIR kalir, bu da standart DX formulunde
    (100*|+DI--DI|/(+DI+-DI)) tanimsiz/sinir-durum bir sonuca (100'e
    kilitlenme) yol acar - GERCEK piyasa verisinde High/Low boyle uzun
    sure birebir sabit kalmaz, bu yuzden bu, ADX'in degil, o fixture'in
    ADX testleri icin uygunsuzlugunun bir sonucudur."""
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    t = np.arange(n)
    close = 100.0 + amplitude * np.sin(2 * np.pi * t / period_bars)
    high = close + 0.3
    low = close - 0.3
    open_ = np.roll(close, 1)
    open_[0] = 100.0
    volume = np.full(n, 1000.0)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=dates)


def test_compute_adx_values_within_0_100():
    df = _trend_df(n=60, step=1.0)
    adx = regime.compute_adx(df, period=14)
    valid = adx.dropna()
    assert not valid.empty
    assert (valid >= 0).all() and (valid <= 100).all()


def test_compute_adx_high_in_strong_trend():
    df = _trend_df(n=80, step=1.0)
    adx = regime.compute_adx(df, period=14)
    assert adx.iloc[-1] > 40  # guclu tek-yonlu trend -> yuksek ADX


def test_compute_adx_low_in_choppy_oscillation():
    df = _choppy_df(n=80, amplitude=5.0, period_bars=10)
    adx = regime.compute_adx(df, period=14)
    assert adx.iloc[-1] < 20.0


def test_compute_trend_range_labels_classifies_trend_and_range():
    trend_df = _trend_df(n=80, step=1.0)
    choppy_df = _choppy_df(n=80, amplitude=5.0, period_bars=10)

    trend_labels = regime.compute_trend_range_labels(trend_df, period=14, trend_threshold=20.0)
    choppy_labels = regime.compute_trend_range_labels(choppy_df, period=14, trend_threshold=20.0)

    assert trend_labels.iloc[-1] == "trend"
    assert choppy_labels.iloc[-1] == "range"


def test_compute_trend_range_labels_none_during_warmup():
    df = _trend_df(n=10, step=1.0)
    labels = regime.compute_trend_range_labels(df, period=14)
    assert pd.isna(labels.iloc[0])


def test_compute_trend_range_labels_only_contains_known_labels_or_none():
    df = _trend_df(n=80, step=1.0)
    labels = regime.compute_trend_range_labels(df, period=14)
    unique = set(labels.dropna().unique())
    assert unique.issubset(set(regime.TREND_RANGE_LABELS))
