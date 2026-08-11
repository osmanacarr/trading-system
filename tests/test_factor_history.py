"""research/factor_history.py testleri - sentetik veriyle (Modul 2)."""

from __future__ import annotations

import pandas as pd
import pytest

from research import factor_history
from research.factors import FACTOR_REGISTRY
from tests.conftest import make_flat_range_df


def test_load_factor_history_missing_file_returns_empty_df_with_columns(tmp_path):
    path = tmp_path / "factor_history.parquet"
    df = factor_history.load_factor_history(path=path)
    assert list(df.columns) == factor_history.LONG_FORMAT_COLUMNS
    assert df.empty


def test_append_factor_history_missing_column_raises(tmp_path):
    path = tmp_path / "factor_history.parquet"
    bad_rows = pd.DataFrame({"date": ["2020-01-01"], "symbol": ["AAA"]})
    with pytest.raises(ValueError):
        factor_history.append_factor_history(bad_rows, path=path)


def test_append_and_load_roundtrip(tmp_path):
    path = tmp_path / "factor_history.parquet"
    factor_history.append_factor_values(
        "2020-01-02", "THYAO.IS", {"rsi": 55.5, "ema": 100.0}, path=path
    )
    result = factor_history.load_factor_history(path=path)
    assert len(result) == 2
    assert set(result["factor_name"]) == {"rsi", "ema"}
    assert (result["symbol"] == "THYAO.IS").all()
    assert result["date"].iloc[0] == pd.Timestamp("2020-01-02")


def test_append_dedup_keeps_latest_value_for_same_key(tmp_path):
    path = tmp_path / "factor_history.parquet"
    factor_history.append_factor_values("2020-01-02", "THYAO.IS", {"rsi": 40.0}, path=path)
    factor_history.append_factor_values("2020-01-02", "THYAO.IS", {"rsi": 60.0}, path=path)
    result = factor_history.load_factor_history(path=path)
    assert len(result) == 1
    assert result["value"].iloc[0] == pytest.approx(60.0)


def test_append_multiple_dates_accumulates_long_format(tmp_path):
    path = tmp_path / "factor_history.parquet"
    factor_history.append_factor_values("2020-01-02", "THYAO.IS", {"rsi": 40.0}, path=path)
    factor_history.append_factor_values("2020-01-03", "THYAO.IS", {"rsi": 42.0}, path=path)
    result = factor_history.load_factor_history(path=path)
    assert len(result) == 2
    assert sorted(result["date"].dt.strftime("%Y-%m-%d")) == ["2020-01-02", "2020-01-03"]


def test_compute_symbol_factor_row_covers_full_registry():
    df = make_flat_range_df(n=100, price=100.0, half_range=2.0)
    rows = factor_history.compute_symbol_factor_row("THYAO.IS", df)
    assert set(rows["factor_name"]) == set(FACTOR_REGISTRY.keys())
    assert (rows["symbol"] == "THYAO.IS").all()
    assert (rows["date"] == df.index[-1]).all()


def test_compute_symbol_factor_row_handles_empty_df_without_raising():
    empty_df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    rows = factor_history.compute_symbol_factor_row("EMPTY.IS", empty_df)
    assert len(rows) == len(FACTOR_REGISTRY)
    assert rows["date"].isna().all()


def test_collect_factor_history_batches_multiple_symbols(tmp_path):
    path = tmp_path / "factor_history.parquet"
    df_a = make_flat_range_df(n=80, price=100.0)
    df_b = make_flat_range_df(n=80, price=50.0)
    result = factor_history.collect_factor_history(
        ["AAA.IS", "BBB.IS"], {"AAA.IS": df_a, "BBB.IS": df_b}, path=path
    )
    assert set(result["symbol"]) == {"AAA.IS", "BBB.IS"}
    assert set(result["factor_name"]) == set(FACTOR_REGISTRY.keys())


def test_collect_factor_history_skips_symbols_with_no_data(tmp_path):
    path = tmp_path / "factor_history.parquet"
    df_a = make_flat_range_df(n=80, price=100.0)
    empty_df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    result = factor_history.collect_factor_history(
        ["AAA.IS", "MISSING.IS"], {"AAA.IS": df_a, "MISSING.IS": empty_df}, path=path
    )
    assert "MISSING.IS" not in set(result["symbol"])
    assert "AAA.IS" in set(result["symbol"])
