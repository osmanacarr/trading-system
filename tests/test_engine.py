"""backtest/engine.py icin sentetik veri testleri."""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtest.engine import (
    TRADE_COLUMNS,
    OpenPosition,
    close_position,
    compute_atr,
    compute_position_size,
    run_donchian_backtest,
    run_price_action_backtest,
)
from config import DONCHIAN_ATR_STOP_MULT, SLIPPAGE_PCT
from signals import donchian, price_action
from tests.conftest import append_bars, build_donchian_trailing_exit_df, make_flat_range_df


def test_compute_atr_converges_to_constant_true_range():
    n = 30
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    df = pd.DataFrame(
        {
            "Open": np.full(n, 100.0),
            "High": np.full(n, 101.0),
            "Low": np.full(n, 99.0),
            "Close": np.full(n, 100.0),
            "Volume": np.full(n, 1000.0),
        },
        index=dates,
    )
    atr = compute_atr(df, period=14)
    valid = atr.dropna()
    assert len(valid) > 0
    assert np.allclose(valid, 2.0)


def test_compute_position_size_formula():
    size = compute_position_size(equity=100_000.0, risk_pct=0.01, entry_price=100.0, stop_price=98.0)
    assert np.isclose(size, 500.0)


def test_compute_position_size_zero_risk_distance_returns_zero():
    size = compute_position_size(equity=100_000.0, risk_pct=0.01, entry_price=100.0, stop_price=100.0)
    assert size == 0.0


def test_donchian_backtest_end_to_end_trailing_exit():
    df = build_donchian_trailing_exit_df()
    signals = donchian.generate_signals(df)
    trades, equity_curve = run_donchian_backtest(df, signals)

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["direction"] == 1
    assert trade["exit_reason"] == "trailing"

    entry_date = df.index[25]  # breakout bari
    expected_entry_price = 115.0 * (1 + SLIPPAGE_PCT)
    assert np.isclose(trade["entry_price"], expected_entry_price)

    atr_at_entry = compute_atr(df).loc[entry_date]
    expected_stop = expected_entry_price - DONCHIAN_ATR_STOP_MULT * atr_at_entry
    assert np.isclose(trade["stop_price"], expected_stop)
    # Reversal barinin dususu (Low=115) stop'un uzerinde kalmali (stop tetiklenmemeli)
    assert 115.0 > expected_stop

    expected_exit_price = 116.0 * (1 - SLIPPAGE_PCT)
    assert np.isclose(trade["exit_price"], expected_exit_price)
    assert trade["pnl"] > 0  # fiyat hala giristen yuksekte cikti
    assert trade["r_multiple"] > 0

    assert len(equity_curve) == len(df)
    assert equity_curve.isna().sum() == 0


def test_donchian_backtest_no_signal_produces_no_trades():
    df = make_flat_range_df(n=40, price=100.0, half_range=1.0, volume=1000.0)
    signals = donchian.generate_signals(df)
    trades, equity_curve = run_donchian_backtest(df, signals)
    assert len(trades) == 0
    assert np.isclose(equity_curve.iloc[-1], equity_curve.iloc[0])


def _price_action_breakout_df(next_bar: dict) -> pd.DataFrame:
    base = make_flat_range_df(n=25, price=100.0, half_range=1.0, volume=1000.0)
    breakout = {"Open": 100.0, "High": 116.0, "Low": 99.5, "Close": 115.0, "Volume": 8000.0}
    return append_bars(base, [breakout, next_bar])


def test_price_action_backtest_stop_hit():
    df = _price_action_breakout_df(
        {"Open": 90.0, "High": 91.0, "Low": 85.0, "Close": 86.0, "Volume": 1000.0}
    )
    signals = price_action.generate_signals(df)
    trades, _equity_curve = run_price_action_backtest(df, signals)

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["exit_reason"] == "stop"
    assert trade["pnl"] < 0
    assert trade["r_multiple"] < 0


def test_price_action_backtest_target_hit():
    df = _price_action_breakout_df(
        {"Open": 150.0, "High": 155.0, "Low": 149.0, "Close": 152.0, "Volume": 1000.0}
    )
    signals = price_action.generate_signals(df)
    trades, _equity_curve = run_price_action_backtest(df, signals)

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["exit_reason"] == "target"
    assert trade["pnl"] > 0
    assert trade["r_multiple"] > 0


def test_trade_columns_include_mae_mfe():
    assert "mae_r" in TRADE_COLUMNS and "mfe_r" in TRADE_COLUMNS


def test_donchian_backtest_trailing_exit_trade_has_nonnegative_mae_mfe():
    df = build_donchian_trailing_exit_df()
    signals = donchian.generate_signals(df)
    trades, _equity_curve = run_donchian_backtest(df, signals)
    trade = trades.iloc[0]
    assert trade["mae_r"] >= 0
    assert trade["mfe_r"] >= 0
    # fiyat giristen cikisa kadar buyuk olcude yukari gitti -> MFE, MAE'den belirgin buyuk olmali
    assert trade["mfe_r"] > trade["mae_r"]


def test_donchian_backtest_no_signal_trades_df_has_mae_mfe_columns():
    df = make_flat_range_df(n=40, price=100.0, half_range=1.0, volume=1000.0)
    signals = donchian.generate_signals(df)
    trades, _equity_curve = run_donchian_backtest(df, signals)
    assert list(trades.columns) == TRADE_COLUMNS


def test_open_position_update_excursion_long():
    pos = OpenPosition(direction=1, entry_date=pd.Timestamp("2020-01-01"), entry_price=100.0, stop_price=95.0, size=10.0)
    pos.update_excursion(high=103.0, low=98.0)
    assert np.isclose(pos.max_favorable_price, 3.0)  # 103-100
    assert np.isclose(pos.max_adverse_price, 2.0)  # 100-98
    pos.update_excursion(high=101.0, low=90.0)  # daha derin bir dip, daha zayif bir tepe
    assert np.isclose(pos.max_adverse_price, 10.0)  # 100-90 > onceki 2 -> guncellenir
    assert np.isclose(pos.max_favorable_price, 3.0)  # 101-100=1 < onceki 3 -> DEGISMEZ (max korunur)


def test_open_position_update_excursion_short():
    pos = OpenPosition(direction=-1, entry_date=pd.Timestamp("2020-01-01"), entry_price=100.0, stop_price=105.0, size=10.0)
    pos.update_excursion(high=104.0, low=97.0)
    assert np.isclose(pos.max_adverse_price, 4.0)  # 104-100
    assert np.isclose(pos.max_favorable_price, 3.0)  # 100-97


def test_close_position_computes_mae_mfe_r():
    pos = OpenPosition(direction=1, entry_date=pd.Timestamp("2020-01-01"), entry_price=100.0, stop_price=95.0, size=10.0)
    pos.update_excursion(high=106.0, low=97.0)  # mfe_price=6, mae_price=3; initial_risk=5
    trade, _net_pnl = close_position(
        pos,
        exit_date=pd.Timestamp("2020-01-03"),
        raw_exit_price=104.0,
        exit_reason="target",
        commission_pct=0.0,
        slippage_pct=0.0,
    )
    assert np.isclose(trade["mfe_r"], 6.0 / 5.0)
    assert np.isclose(trade["mae_r"], 3.0 / 5.0)
