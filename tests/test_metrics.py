"""backtest/metrics.py icin sentetik veri testleri."""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtest.metrics import (
    expectancy_r,
    mae_mfe_summary,
    max_drawdown,
    median_r,
    profit_factor,
    sharpe_ratio,
    summarize,
    win_loss_ratio,
    win_rate,
)


def _trades(
    pnls: list[float],
    r_multiples: list[float],
    mae_r: list[float] | None = None,
    mfe_r: list[float] | None = None,
) -> pd.DataFrame:
    data = {"pnl": pnls, "r_multiple": r_multiples}
    if mae_r is not None:
        data["mae_r"] = mae_r
    if mfe_r is not None:
        data["mfe_r"] = mfe_r
    return pd.DataFrame(data)


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
    assert set(result.keys()) == {
        "n_trades",
        "win_rate",
        "expectancy_r",
        "median_r",
        "max_drawdown",
        "sharpe",
        "profit_factor",
        "win_loss_ratio",
        "mae_mfe",
        "low_sample_warning",
        "overfit_profit_factor_warning",
    }
    assert result["n_trades"] == 2


def test_summarize_low_sample_warning_below_threshold():
    trades = _trades(pnls=[100, -50], r_multiples=[2.0, -1.0])
    equity = pd.Series([100_000.0, 100_100.0, 100_050.0])
    result = summarize(trades, equity)
    assert result["low_sample_warning"] is True  # 2 islem < MIN_TRADES_FOR_RELIABLE_STATS (30)


def test_profit_factor_known_value():
    trades = _trades(pnls=[100, 100, -50], r_multiples=[2.0, 2.0, -1.0])
    assert np.isclose(profit_factor(trades), 200 / 50)


def test_profit_factor_no_losses_is_infinite():
    trades = _trades(pnls=[100, 50], r_multiples=[2.0, 1.0])
    assert profit_factor(trades) == float("inf")


def test_profit_factor_empty_trades_is_zero():
    trades = pd.DataFrame(columns=["pnl", "r_multiple"])
    assert profit_factor(trades) == 0.0


def test_win_loss_ratio_known_value():
    trades = _trades(pnls=[100, 100, -50], r_multiples=[2.0, 2.0, -1.0])
    assert np.isclose(win_loss_ratio(trades), 100 / 50)


def test_overfit_profit_factor_warning_triggers_above_threshold():
    # 10 kazanan (her biri 100), 1 kaybeden (-1) -> profit factor = 1000, esik(5.0) asilir
    trades = _trades(pnls=[100.0] * 10 + [-1.0], r_multiples=[2.0] * 10 + [-1.0])
    equity = pd.Series([100_000.0, 100_500.0])
    result = summarize(trades, equity)
    assert result["overfit_profit_factor_warning"] is True


def test_mae_mfe_summary_computes_means_and_near_mfe_pct():
    trades = _trades(
        pnls=[100, -50],
        r_multiples=[2.0, -1.0],
        mae_r=[0.2, 1.0],
        mfe_r=[2.1, 0.1],
    )
    summary = mae_mfe_summary(trades)
    assert np.isclose(summary["mean_mae_r"], 0.6)
    assert np.isclose(summary["mean_mfe_r"], 1.1)
    # ilk islem: r_multiple(2.0) >= 0.9*mfe_r(2.1)=1.89 -> True; ikinci: -1.0 >= 0.9*0.1=0.09 -> False
    assert np.isclose(summary["pct_closed_near_mfe"], 0.5)


def test_mae_mfe_summary_missing_columns_returns_zeros():
    trades = _trades(pnls=[100], r_multiples=[2.0])
    summary = mae_mfe_summary(trades)
    assert summary == {
        "mean_mae_r": 0.0,
        "mean_mfe_r": 0.0,
        "median_mae_r": 0.0,
        "median_mfe_r": 0.0,
        "pct_closed_near_mfe": 0.0,
    }
