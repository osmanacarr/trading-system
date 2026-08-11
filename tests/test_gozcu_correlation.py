"""gozcu/correlation.py icin testler."""

from __future__ import annotations

import numpy as np
import pandas as pd

from gozcu import correlation


def test_compute_returns_basic():
    dates = pd.date_range("2024-01-01", periods=4, freq="B")
    df = pd.DataFrame({"Close": [100, 110, 121, 133.1]}, index=dates)
    returns = correlation.compute_returns(df, lookback=20)
    assert len(returns) == 3
    assert np.isclose(returns.iloc[0], 0.10)


def test_compute_returns_insufficient_data_returns_empty_series():
    df = pd.DataFrame({"Close": [100.0]}, index=pd.date_range("2024-01-01", periods=1))
    assert correlation.compute_returns(df).empty


def test_average_correlation_perfectly_correlated_series():
    dates = pd.date_range("2024-01-01", periods=15, freq="B")
    base_returns = pd.Series(np.linspace(-0.02, 0.02, 15), index=dates)
    returns_by_symbol = {"A": base_returns, "B": base_returns * 2}
    avg_corr = correlation.average_correlation_to_reference(returns_by_symbol, base_returns, min_overlap=5)
    assert np.isclose(avg_corr, 1.0, atol=1e-6)


def test_average_correlation_none_when_insufficient_overlap():
    dates = pd.date_range("2024-01-01", periods=3, freq="B")
    returns = pd.Series([0.01, -0.01, 0.02], index=dates)
    result = correlation.average_correlation_to_reference({"A": returns}, returns, min_overlap=10)
    assert result is None


def test_average_correlation_none_when_reference_empty():
    result = correlation.average_correlation_to_reference({"A": pd.Series([0.01])}, pd.Series(dtype=float))
    assert result is None
