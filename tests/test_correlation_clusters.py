"""risk/correlation_clusters.py testleri - sentetik veriyle (M2)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from risk import correlation_clusters, portfolio


def _make_price_df(close: np.ndarray, start: str = "2024-01-01") -> pd.DataFrame:
    index = pd.date_range(start, periods=len(close), freq="B")
    return pd.DataFrame(
        {
            "Open": close,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": np.full(len(close), 1_000_000.0),
        },
        index=index,
    )


def test_compute_return_matrix_aligns_common_dates():
    rng = np.random.default_rng(0)
    a = 100 * np.cumprod(1 + rng.normal(0, 0.01, 80))
    b = 50 * np.cumprod(1 + rng.normal(0, 0.01, 80))
    price_data = {"A": _make_price_df(a), "B": _make_price_df(b)}
    returns = correlation_clusters.compute_return_matrix(price_data, lookback_days=60)
    assert list(returns.columns) == ["A", "B"]
    assert len(returns) <= 61
    assert not returns.isna().any().any()


def test_compute_return_matrix_single_symbol_returns_empty():
    price_data = {"A": _make_price_df(np.array([100.0, 101.0, 102.0]))}
    returns = correlation_clusters.compute_return_matrix(price_data)
    assert returns.empty


def test_compute_return_matrix_missing_close_column_skipped():
    bad_df = pd.DataFrame({"Open": [1.0, 2.0]})
    good_df = _make_price_df(np.array([100.0, 101.0, 102.0]))
    price_data = {"BAD": bad_df, "GOOD": good_df}
    returns = correlation_clusters.compute_return_matrix(price_data)
    # tek gecerli sembol kaldi -> bos doner
    assert returns.empty


def test_build_correlation_clusters_empty_input():
    assert correlation_clusters.build_correlation_clusters(pd.DataFrame()) == {}


def test_build_correlation_clusters_single_symbol():
    returns = pd.DataFrame({"A": [0.01, -0.01, 0.02]})
    assert correlation_clusters.build_correlation_clusters(returns) == {"A": "cluster_0"}


def test_build_correlation_clusters_highly_correlated_grouped_together():
    rng = np.random.default_rng(1)
    base = rng.normal(0, 0.01, 100)
    # B, A'nin neredeyse birebir kopyasi (yuksek korelasyon); C bagimsiz gurultu
    returns = pd.DataFrame(
        {
            "A": base,
            "B": base + rng.normal(0, 0.0005, 100),
            "C": rng.normal(0, 0.01, 100),
        }
    )
    clusters = correlation_clusters.build_correlation_clusters(returns, threshold=0.6)
    assert clusters["A"] == clusters["B"]
    assert clusters["C"] != clusters["A"]


def test_build_correlation_clusters_uncorrelated_symbols_separate_clusters():
    rng = np.random.default_rng(2)
    returns = pd.DataFrame(
        {
            "A": rng.normal(0, 0.01, 100),
            "B": rng.normal(0, 0.01, 100),
            "C": rng.normal(0, 0.01, 100),
        }
    )
    clusters = correlation_clusters.build_correlation_clusters(returns, threshold=0.9)
    assert len(set(clusters.values())) == 3


def test_build_correlation_clusters_output_feeds_optimize_portfolio_sector_map():
    rng = np.random.default_rng(3)
    base = rng.normal(0, 0.01, 100)
    returns = pd.DataFrame(
        {
            "A": base,
            "B": base + rng.normal(0, 0.0005, 100),
            "C": rng.normal(0, 0.01, 100),
        }
    )
    clusters = correlation_clusters.build_correlation_clusters(returns, threshold=0.6)
    scores = {"A": 5.0, "B": 5.0, "C": 1.0}
    weights = portfolio.optimize_portfolio(
        scores,
        max_gross_leverage=1.0,
        max_position_size=0.5,
        sector_map=clusters,
        max_sector_exposure=0.4,
    )
    correlated_cluster_exposure = abs(weights["A"] + weights["B"])
    assert correlated_cluster_exposure <= 0.4 + 1e-6
