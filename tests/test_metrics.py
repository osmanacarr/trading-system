"""backtest/metrics.py icin sentetik veri testleri."""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtest.metrics import expectancy_r, max_drawdown, median_r, sharpe_ratio, summarize, win_rate


def _trades(pnls: list[float], r_multiples: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"pnl": pnls, "r_multiple": r_multiples})


def test_win_rate_and_expectancy_known_values():
    trades = _trades(pnls=[100, -50, 200, -50], r_multiples=[2.0, -1.0, 4.0, -1.0])
    assert np.isclose(win_rate(trades), 0.5)
    assert np.isclose(expectancy_r(trades), 1.0)  # (2-1+4-1)/4
    assert np.isclose(median_r(trades), 0.5)  # sorted: -1,-1,2,4 -> medyan 0.5


def test_metrics_empty_trades_return_zero():
    trades = pd.DataFrame(columns=["pnl", "r_multiple"])
    assert win_rate(trades) == 0.0
    assert expectancy_r(trades) == 0.0
    assert median_r(trades) == 0.0


def test_max_drawdown_known_curve():
    equity = pd.Series([100.0, 120.0, 90.0, 95.0, 130.0])
    dd = max_drawdown(equity)
    # tepe 120 -> dip 90: (90-120)/120 = -0.25
    assert np.isclose(dd, -0.25)


def test_max_drawdown_monotonic_up_is_zero():
    equity = pd.Series([100.0, 110.0, 120.0, 130.0])
    assert np.isclose(max_drawdown(equity), 0.0)


def test_sharpe_ratio_zero_variance_returns_zero():
    equity = pd.Series([100.0, 100.0, 100.0, 100.0])
    assert sharpe_ratio(equity) == 0.0


def test_sharpe_ratio_positive_trend_is_positive():
    equity = pd.Series([100.0, 101.0, 102.5, 103.0, 105.0, 106.0])
    assert sharpe_ratio(equity) > 0


def test_summarize_returns_all_keys():
    trades = _trades(pnls=[100, -50], r_multiples=[2.0, -1.0])
    equity = pd.Series([100_000.0, 100_100.0, 100_050.0])
    result = summarize(trades, equity)
    assert set(result.keys()) == {"n_trades", "win_rate", "expectancy_r", "median_r", "max_drawdown", "sharpe"}
    assert result["n_trades"] == 2
