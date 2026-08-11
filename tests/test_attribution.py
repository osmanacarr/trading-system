"""research/attribution.py testleri - sentetik veriyle (Modul 7)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from research import attribution


def _price_df(closes: list[float], start: str = "2020-01-01") -> pd.DataFrame:
    dates = pd.date_range(start, periods=len(closes), freq="B")
    return pd.DataFrame({"Close": closes}, index=dates)


def test_compute_daily_returns_matches_pct_change():
    df = _price_df([100.0, 110.0, 121.0])
    returns = attribution.compute_daily_returns(df, df.index[0], df.index[-1])
    assert np.isclose(returns.iloc[0], 0.10)
    assert np.isclose(returns.iloc[1], 0.10)


def test_single_factor_attribution_identical_series_beta_one_all_common():
    closes = [100.0, 102.0, 101.0, 105.0, 110.0]
    price_df = _price_df(closes)
    reference_df = _price_df(closes)
    position_returns = attribution.compute_daily_returns(price_df, price_df.index[0], price_df.index[-1])
    reference_returns = attribution.compute_daily_returns(reference_df, reference_df.index[0], reference_df.index[-1])

    result = attribution.single_factor_attribution(position_returns, reference_returns)

    assert np.isclose(result["beta"], 1.0, atol=1e-6)
    assert np.isclose(result["r_squared"], 1.0, atol=1e-6)
    assert np.isclose(result["specific_return"], 0.0, atol=1e-6)
    assert np.isclose(result["common_return"], position_returns.sum(), atol=1e-6)


def test_single_factor_attribution_flat_reference_falls_back_to_all_specific():
    price_df = _price_df([100.0, 105.0, 110.0, 108.0])
    reference_df = _price_df([100.0, 100.0, 100.0, 100.0])  # sifir varyans
    position_returns = attribution.compute_daily_returns(price_df, price_df.index[0], price_df.index[-1])
    reference_returns = attribution.compute_daily_returns(reference_df, reference_df.index[0], reference_df.index[-1])

    result = attribution.single_factor_attribution(position_returns, reference_returns)

    assert result["common_return"] == 0.0
    assert np.isclose(result["specific_return"], position_returns.sum())


def test_single_factor_attribution_insufficient_days_returns_zero_fallback():
    empty = pd.Series(dtype=float)
    result = attribution.single_factor_attribution(empty, empty)
    assert result["n_days"] == 0
    assert result["common_return"] == 0.0
    assert result["specific_return"] == 0.0


def test_attribute_trade_short_position_has_negative_beta_and_positive_common():
    closes = [100.0, 95.0, 90.0, 85.0, 80.0]  # dusen piyasa
    price_df = _price_df(closes)
    reference_df = _price_df(closes)  # sembol = referans (mukemmel korelasyon)

    result = attribution.attribute_trade(
        price_df, reference_df, price_df.index[0], price_df.index[-1], direction=-1
    )
    assert result["beta"] < 0
    # kisa pozisyon dusen piyasada kazanir - kazanc TAMAMEN piyasa hareketinden (common) geliyor
    assert result["common_return"] > 0
    assert np.isclose(result["specific_return"], 0.0, atol=1e-6)


def test_attribute_trade_long_position_matches_single_factor_directly():
    closes = [100.0, 103.0, 101.0, 107.0]
    price_df = _price_df(closes)
    reference_df = _price_df([100.0, 101.0, 102.0, 103.0])

    direct = attribution.attribute_trade(price_df, reference_df, price_df.index[0], price_df.index[-1], direction=1)
    position_returns = attribution.compute_daily_returns(price_df, price_df.index[0], price_df.index[-1])
    reference_returns = attribution.compute_daily_returns(reference_df, reference_df.index[0], reference_df.index[-1])
    manual = attribution.single_factor_attribution(position_returns, reference_returns)

    assert np.isclose(direct["common_return"], manual["common_return"])
    assert np.isclose(direct["specific_return"], manual["specific_return"])


def test_attribute_trades_adds_common_and_specific_columns():
    closes = [100.0, 102.0, 104.0, 103.0, 108.0, 110.0]
    price_df = _price_df(closes)
    reference_df = _price_df([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
    trades = pd.DataFrame(
        {
            "entry_date": [price_df.index[0], price_df.index[3]],
            "exit_date": [price_df.index[2], price_df.index[5]],
            "direction": [1, 1],
        }
    )

    result = attribution.attribute_trades(trades, price_df, reference_df)

    assert "common_return" in result.columns
    assert "specific_return" in result.columns
    assert len(result) == 2


def test_attribute_trades_empty_dataframe_returns_columns():
    trades = pd.DataFrame(columns=["entry_date", "exit_date", "direction"])
    price_df = _price_df([100.0, 101.0])
    reference_df = _price_df([100.0, 101.0])
    result = attribution.attribute_trades(trades, price_df, reference_df)
    assert "common_return" in result.columns and "specific_return" in result.columns
    assert result.empty


def test_summarize_attribution_computes_pct_specific():
    trades = pd.DataFrame({"common_return": [0.02, 0.01], "specific_return": [0.03, 0.04]})
    summary = attribution.summarize_attribution(trades)
    assert np.isclose(summary["total_common_return"], 0.03)
    assert np.isclose(summary["total_specific_return"], 0.07)
    assert np.isclose(summary["pct_specific"], 0.07 / 0.10)


def test_summarize_attribution_missing_columns_returns_zeros():
    trades = pd.DataFrame({"pnl": [100.0]})
    summary = attribution.summarize_attribution(trades)
    assert summary == {"total_common_return": 0.0, "total_specific_return": 0.0, "pct_specific": 0.0}
