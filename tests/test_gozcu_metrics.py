"""gozcu/metrics.py icin sentetik veri testleri."""

from __future__ import annotations

import numpy as np
import pandas as pd

from gozcu import metrics
from tests.conftest import append_bars, make_flat_range_df


def test_daily_change_pct_basic():
    dates = pd.date_range("2024-01-01", periods=2, freq="B")
    df = pd.DataFrame({"Close": [100.0, 110.0]}, index=dates)
    assert np.isclose(metrics.daily_change_pct(df), 0.10)


def test_daily_change_pct_insufficient_data_returns_none():
    df = pd.DataFrame({"Close": [100.0]}, index=pd.date_range("2024-01-01", periods=1))
    assert metrics.daily_change_pct(df) is None


def test_weekly_change_pct_basic():
    dates = pd.date_range("2024-01-01", periods=6, freq="B")
    df = pd.DataFrame({"Close": [100, 101, 102, 103, 104, 110]}, index=dates)
    assert np.isclose(metrics.weekly_change_pct(df, lookback=5), (110 - 100) / 100)


def test_weekly_change_pct_insufficient_data_returns_none():
    dates = pd.date_range("2024-01-01", periods=3, freq="B")
    df = pd.DataFrame({"Close": [100, 101, 102]}, index=dates)
    assert metrics.weekly_change_pct(df, lookback=5) is None


def test_volume_zscore_matches_manual_calculation():
    dates = pd.date_range("2024-01-01", periods=21, freq="B")
    volumes = [
        1000, 1200, 900, 1100, 950, 1050, 980, 1020, 990, 1010,
        1005, 995, 1015, 985, 1030, 970, 1040, 960, 1025, 975, 4000,
    ]
    df = pd.DataFrame({"Close": np.full(21, 50.0), "Volume": volumes}, index=dates)
    result = metrics.volume_zscore(df, lookback=20)
    window = pd.Series(volumes[:-1], dtype=float)
    expected = (volumes[-1] - window.mean()) / window.std()
    assert np.isclose(result, expected)


def test_volume_zscore_insufficient_data_returns_none():
    dates = pd.date_range("2024-01-01", periods=5, freq="B")
    df = pd.DataFrame({"Close": np.full(5, 50.0), "Volume": np.full(5, 1000.0)}, index=dates)
    assert metrics.volume_zscore(df, lookback=20) is None


def test_volume_zscore_none_when_window_has_zero_variance():
    dates = pd.date_range("2024-01-01", periods=21, freq="B")
    df = pd.DataFrame({"Close": np.full(21, 50.0), "Volume": np.full(21, 1000.0)}, index=dates)
    assert metrics.volume_zscore(df, lookback=20) is None


def test_momentum_candle_flag_true_for_confirmed_breakout():
    base = make_flat_range_df(n=25, price=100.0, half_range=1.0, volume=1000.0)
    breakout = append_bars(base, [{"Open": 101.0, "High": 116.0, "Low": 100.5, "Close": 115.0, "Volume": 6000.0}])
    flag = metrics.momentum_candle_flag(breakout)
    assert flag == {"body_ok": True, "volume_ok": True}


def test_momentum_candle_flag_false_for_flat_bar():
    base = make_flat_range_df(n=25)
    flag = metrics.momentum_candle_flag(base)
    assert flag["body_ok"] is False


def test_relative_volume_basic():
    dates = pd.date_range("2024-01-01 10:00", periods=3, freq="5min")
    intraday = pd.DataFrame({"Volume": [100, 150, 200]}, index=dates)
    rvol = metrics.relative_volume(intraday, avg_daily_volume=2000.0, elapsed_fraction=0.25)
    assert np.isclose(rvol, 450.0 / 500.0)


def test_relative_volume_none_when_inputs_missing():
    intraday = pd.DataFrame({"Volume": [100]}, index=pd.date_range("2024-01-01", periods=1))
    assert metrics.relative_volume(intraday, None, 0.5) is None
    assert metrics.relative_volume(intraday, 1000.0, 0.0) is None
    assert metrics.relative_volume(pd.DataFrame(columns=["Volume"]), 1000.0, 0.5) is None


def test_compute_vwap_matches_manual_calculation():
    dates = pd.date_range("2024-01-01 10:00", periods=3, freq="5min")
    df = pd.DataFrame(
        {"High": [10, 11, 12], "Low": [9, 10, 11], "Close": [9.5, 10.5, 11.5], "Volume": [100, 200, 300]},
        index=dates,
    )
    vwap = metrics.compute_vwap(df)
    typical = (df["High"] + df["Low"] + df["Close"]) / 3.0
    expected_last = (typical * df["Volume"]).cumsum().iloc[-1] / df["Volume"].cumsum().iloc[-1]
    assert np.isclose(vwap.iloc[-1], expected_last)


def test_compute_vwap_empty_df_returns_empty_series():
    result = metrics.compute_vwap(pd.DataFrame(columns=["High", "Low", "Close", "Volume"]))
    assert result.empty


def test_vwap_slope_positive_for_rising_vwap():
    series = pd.Series([100.0, 101.0, 103.0, 106.0])
    slope = metrics.vwap_slope(series, lookback=3)
    assert np.isclose(slope, (106.0 - 100.0) / 3)


def test_vwap_slope_none_when_insufficient_points():
    series = pd.Series([100.0, 101.0])
    assert metrics.vwap_slope(series, lookback=3) is None


def test_vwap_position_pct_above_and_missing():
    assert np.isclose(metrics.vwap_position_pct(110.0, 100.0), 0.10)
    assert metrics.vwap_position_pct(100.0, None) is None


def test_distance_from_52w_high_and_low():
    closes = [90.0, 95.0, 100.0, 80.0, 85.0]
    dates = pd.date_range("2024-01-01", periods=5, freq="B")
    df = pd.DataFrame({"Close": closes}, index=dates)
    high_distance = metrics.distance_from_52w_high(df, lookback=5)
    low_distance = metrics.distance_from_52w_low(df, lookback=5)
    assert np.isclose(high_distance, (85.0 - 100.0) / 100.0)
    assert np.isclose(low_distance, (85.0 - 80.0) / 80.0)


def test_distance_from_52w_empty_df_returns_none():
    df = pd.DataFrame({"Close": []})
    assert metrics.distance_from_52w_high(df) is None
    assert metrics.distance_from_52w_low(df) is None


def test_atr_percentile_high_after_volatility_spike():
    n = 60
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    high = np.full(n, 101.0)
    low = np.full(n, 99.0)
    close = np.full(n, 100.0)
    high[-10:] = 110.0
    low[-10:] = 90.0
    df = pd.DataFrame({"High": high, "Low": low, "Close": close}, index=dates)
    percentile = metrics.atr_percentile(df, period=14, lookback=60)
    assert percentile is not None
    assert percentile > 90.0


def test_atr_percentile_none_when_insufficient_data():
    n = 5
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    df = pd.DataFrame({"High": np.full(n, 11.0), "Low": np.full(n, 9.0), "Close": np.full(n, 10.0)}, index=dates)
    assert metrics.atr_percentile(df, period=14) is None


def test_lateness_warning_none_vwap_reports_data_gap_explicitly():
    result = metrics.compute_lateness_warning(daily_change_pct=0.05, vwap_position_pct=None, elapsed_fraction=0.5)
    assert result["vwap_distance_pct"] is None
    assert result["session_elapsed_pct"] == 50.0
    assert "VWAP verisi henuz yok" in result["warning_text"]


def test_lateness_warning_below_threshold_no_late_clause():
    result = metrics.compute_lateness_warning(
        daily_change_pct=0.02, vwap_position_pct=0.003, elapsed_fraction=0.6, vwap_threshold_pct=1.0
    )
    assert np.isclose(result["vwap_distance_pct"], 0.3)
    assert "GEC KALINMIS" not in result["warning_text"]


def test_lateness_warning_above_threshold_positive_says_pahaliya():
    result = metrics.compute_lateness_warning(
        daily_change_pct=0.06, vwap_position_pct=0.025, elapsed_fraction=0.8, vwap_threshold_pct=1.0
    )
    assert np.isclose(result["vwap_distance_pct"], 2.5)
    assert "GEC KALINMIS OLABILIR" in result["warning_text"]
    assert "pahaliya" in result["warning_text"]
    assert "uzerinde" in result["warning_text"]


def test_lateness_warning_above_threshold_negative_says_ucuza():
    result = metrics.compute_lateness_warning(
        daily_change_pct=-0.05, vwap_position_pct=-0.02, elapsed_fraction=0.4, vwap_threshold_pct=1.0
    )
    assert np.isclose(result["vwap_distance_pct"], -2.0)
    assert "GEC KALINMIS OLABILIR" in result["warning_text"]
    assert "ucuza" in result["warning_text"]
    assert "altinda" in result["warning_text"]
