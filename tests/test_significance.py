"""validation/significance.py icin sentetik veri testleri."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from validation.significance import (
    is_significant,
    min_years_for_confidence,
    rolling_walk_forward_splits,
    sharpe_confidence_interval,
    single_split,
    standard_error_r,
    t_statistic,
)


def test_t_statistic_known_value():
    # R degerleri: mean=1.0, ddof=1 std hesaplaniyor
    r_values = np.array([1.0, 2.0, 0.0, 1.0, 1.0])
    n = len(r_values)
    expected_se = np.std(r_values, ddof=1) / np.sqrt(n)
    expected_t = np.mean(r_values) / expected_se
    assert np.isclose(standard_error_r(r_values), expected_se)
    assert np.isclose(t_statistic(r_values), expected_t)


def test_t_statistic_insufficient_data_returns_zero():
    assert t_statistic([1.0]) == 0.0
    assert t_statistic([]) == 0.0


def test_is_significant_thresholds():
    strong_signal = np.array([1.0] * 50) + np.random.default_rng(0).normal(0, 0.01, 50)
    assert is_significant(strong_signal, t_threshold=2.0) is True

    noisy_signal = np.array([0.01, -0.02, 0.03, -0.01, 0.0])
    assert is_significant(noisy_signal, t_threshold=2.0) is False


def test_min_years_for_confidence_formula():
    assert np.isclose(min_years_for_confidence(0.5), 4.0)
    assert np.isclose(min_years_for_confidence(1.0), 1.0)
    assert min_years_for_confidence(0.0) == float("inf")


def test_sharpe_confidence_interval_brackets_point_estimate():
    lower, upper = sharpe_confidence_interval(0.6, n_periods=250, confidence=0.95)
    assert lower < 0.6 < upper


def test_single_split_ratio():
    df = pd.DataFrame({"x": range(100)}, index=pd.date_range("2020-01-01", periods=100, freq="B"))
    train, test = single_split(df, train_frac=0.7)
    assert len(train) == 70
    assert len(test) == 30
    assert train.index[-1] < test.index[0]


def test_single_split_invalid_frac_raises():
    df = pd.DataFrame({"x": range(10)})
    with pytest.raises(ValueError):
        single_split(df, train_frac=1.5)


def test_rolling_walk_forward_splits_cover_full_range_without_overlap():
    df = pd.DataFrame({"x": range(100)}, index=pd.date_range("2020-01-01", periods=100, freq="B"))
    splits = rolling_walk_forward_splits(df, n_splits=4, min_train_frac=0.5)
    assert len(splits) == 4

    # Her test parcasi bir onceki parcanin bittigi yerden baslamali (bosluk/cakisma yok)
    prev_test_end_idx = None
    for train_df, test_df in splits:
        assert len(test_df) > 0
        assert train_df.index[-1] < test_df.index[0]
        if prev_test_end_idx is not None:
            assert test_df.index[0] == df.index[prev_test_end_idx]
        prev_test_end_idx = df.index.get_loc(test_df.index[-1]) + 1

    # Son test parcasi verinin sonuna kadar uzanmali
    assert splits[-1][1].index[-1] == df.index[-1]


def test_rolling_walk_forward_splits_too_short_raises():
    df = pd.DataFrame({"x": range(3)}, index=pd.date_range("2020-01-01", periods=3, freq="B"))
    with pytest.raises(ValueError):
        rolling_walk_forward_splits(df, n_splits=5, min_train_frac=0.5)
