"""research/factors.py testleri - sentetik veriyle (Modul 1)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from gozcu.metrics import volume_zscore as gozcu_volume_zscore
from research import factors
from tests.conftest import append_bars, make_flat_range_df


def test_missing_columns_raises_value_error():
    df = pd.DataFrame({"Close": [1.0, 2.0, 3.0]})
    with pytest.raises(ValueError):
        factors.compute_ema(df)


def test_ema_converges_on_flat_price():
    df = make_flat_range_df(n=60, price=100.0, half_range=0.0)
    ema = factors.compute_ema(df, period=10)
    assert ema.iloc[-1] == pytest.approx(100.0, abs=1e-6)
    assert factors.ema_factor(df, period=10) == pytest.approx(100.0, abs=1e-6)


def test_rsi_reaches_100_on_strict_uptrend():
    base = make_flat_range_df(n=20, price=100.0, half_range=0.0)
    up_bars = [
        {"Open": 100 + i, "High": 101 + i, "Low": 99 + i, "Close": 101 + i, "Volume": 1000.0}
        for i in range(30)
    ]
    df = append_bars(base, up_bars)
    rsi = factors.compute_rsi(df, period=14)
    assert rsi.iloc[-1] == pytest.approx(100.0, abs=1e-6)
    assert (rsi.dropna() >= 0).all() and (rsi.dropna() <= 100).all()


def test_macd_histogram_equals_line_minus_signal():
    df = make_flat_range_df(n=80)
    macd_df = factors.compute_macd(df, fast=12, slow=26, signal=9)
    diff = macd_df["macd_line"] - macd_df["signal_line"]
    pd.testing.assert_series_equal(
        macd_df["histogram"], diff, check_names=False
    )
    assert factors.macd_factor(df) == pytest.approx(diff.iloc[-1])


def test_stochastic_bounded_between_0_and_100():
    df = make_flat_range_df(n=60)
    stoch = factors.compute_stochastic(df, k_period=14, d_period=3)
    valid_k = stoch["percent_k"].dropna()
    assert (valid_k >= -1e-9).all() and (valid_k <= 100 + 1e-9).all()


def test_volume_zscore_matches_gozcu_scalar_formula():
    df = make_flat_range_df(n=40, volume=1000.0)
    extra = [
        {"Open": 100, "High": 101, "Low": 99, "Close": 100, "Volume": v}
        for v in [1000, 1200, 900, 1500, 3000]
    ]
    df = append_bars(df, extra)
    vectorized_last = factors.volume_zscore_factor(df, lookback=20)
    scalar_ref = gozcu_volume_zscore(df, lookback=20)
    assert vectorized_last == pytest.approx(scalar_ref, rel=1e-9)


def test_cvd_proxy_sign_method_matches_manual_calc():
    df = pd.DataFrame(
        {
            "Open": [10.0, 10.0, 10.0],
            "High": [11.0, 11.0, 11.0],
            "Low": [9.0, 9.0, 9.0],
            "Close": [11.0, 9.0, 10.0],  # up, down, flat(no change -> sign=0)
            "Volume": [100.0, 200.0, 300.0],
        },
        index=pd.date_range("2020-01-01", periods=3, freq="B"),
    )
    cvd = factors.compute_cvd_proxy(df, method="sign")
    # sign(close-open): +1, -1, 0 -> signed volume: 100, -200, 0 -> cumsum: 100, -100, -100
    expected = pd.Series([100.0, -100.0, -100.0], index=df.index)
    pd.testing.assert_series_equal(cvd, expected, check_names=False)


def test_cvd_divergence_detects_bullish_pattern():
    # Fiyat: ilk dip 90, ikinci dip 85 (daha dusuk) ama ikinci dip'te
    # kapanis>acilis ile pozitif hacim agirlikli barlar -> CVD proxy ikinci
    # dipte daha yuksek olmali (bullish diverjans beklenir).
    dates = pd.date_range("2020-01-01", periods=40, freq="B")
    close = np.concatenate(
        [
            np.linspace(100, 90, 10),   # ilk dip'e inis (pivot ~idx 9-10)
            np.linspace(90, 105, 10),   # toparlanma
            np.linspace(105, 85, 10),   # ikinci (daha derin) dip'e inis
            np.linspace(85, 100, 10),   # onay icin sonraki barlar
        ]
    )
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    # ikinci dip bolgesinde (idx 20-29) close>open agirlikli yap (pozitif CVD katkisi)
    for i in range(20, 30):
        open_[i] = close[i] - 0.5
    high = np.maximum(open_, close) + 0.1
    low = np.minimum(open_, close) - 0.1
    volume = np.full(40, 1000.0)
    df = pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=dates,
    )
    divergence = factors.compute_cvd_divergence(df, pivot_window=5)
    assert set(divergence.unique()).issubset({-1, 0, 1})
    assert (divergence == 1).any(), "beklenen bullish diverjans (+1) hic gorulmedi"


def test_poc_price_within_trailing_window_range():
    df = make_flat_range_df(n=30, price=100.0, half_range=5.0)
    poc = factors.compute_volume_profile_poc(df, lookback=10, n_bins=8)
    valid = poc.dropna()
    assert not valid.empty
    for date, poc_price in valid.items():
        idx = df.index.get_loc(date)
        window = df.iloc[idx - 10 : idx]
        assert window["Low"].min() - 1e-6 <= poc_price <= window["High"].max() + 1e-6


def test_value_area_bounds_contain_poc():
    df = make_flat_range_df(n=30, price=100.0, half_range=5.0)
    va = factors.compute_value_area(df, lookback=10, n_bins=8)
    valid = va.dropna()
    assert not valid.empty
    assert (valid["value_area_low"] <= valid["poc"] + 1e-6).all()
    assert (valid["value_area_high"] >= valid["poc"] - 1e-6).all()


def test_absorption_heuristic_higher_for_high_volume_narrow_range_bar():
    base = make_flat_range_df(n=25, price=100.0, half_range=1.0, volume=1000.0)
    normal_bar = [{"Open": 100, "High": 100.5, "Low": 99.5, "Close": 100, "Volume": 1000.0}]
    df_normal = append_bars(base, normal_bar)

    absorption_bar = [{"Open": 100, "High": 100.05, "Low": 99.95, "Close": 100, "Volume": 5000.0}]
    df_absorption = append_bars(base, absorption_bar)

    score_normal = factors.absorption_factor(df_normal)
    score_absorption = factors.absorption_factor(df_absorption)
    assert score_absorption > score_normal


def test_factor_registry_returns_finite_or_nan_floats():
    df = make_flat_range_df(n=100, price=100.0, half_range=2.0)
    for name, factor_fn in factors.FACTOR_REGISTRY.items():
        value = factor_fn(df)
        assert isinstance(value, float), f"{name} float donmedi: {type(value)}"
