"""research/publish_summary.py testleri (ag cagrisi yapilmaz, fetch fonksiyonlari mock'lanir)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from research import publish_summary
from tests.conftest import make_flat_range_df


def _factor_long_df() -> pd.DataFrame:
    dates = pd.to_datetime(["2020-01-01"] * 5 + ["2020-01-02"] * 5)
    symbols = [f"S{i}" for i in range(5)] * 2
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    return pd.DataFrame(
        {"date": dates, "symbol": symbols, "factor_name": "f1", "value": values}
    )


def _forward_returns_df() -> pd.DataFrame:
    dates = pd.to_datetime(["2020-01-01"] * 5 + ["2020-01-02"] * 5)
    symbols = [f"S{i}" for i in range(5)] * 2
    returns = [1.0, 2.0, 3.0, 4.0, 5.0, 5.0, 4.0, 3.0, 2.0, 1.0]
    return pd.DataFrame({"date": dates, "symbol": symbols, "forward_return": returns})


def test_build_factor_ic_summary_empty_input_returns_empty_list():
    empty = pd.DataFrame(columns=["date", "symbol", "factor_name", "value"])
    assert publish_summary.build_factor_ic_summary(empty, empty) == []


def test_build_factor_ic_summary_computes_mean_ic_and_n_dates():
    rows = publish_summary.build_factor_ic_summary(_factor_long_df(), _forward_returns_df())
    assert len(rows) == 1
    row = rows[0]
    assert row["factor_name"] == "f1"
    assert row["n_dates"] == 2
    # gun 1: IC=+1.0, gun 2: IC=-1.0 -> ortalama 0.0
    assert np.isclose(row["mean_ic"], 0.0, atol=1e-9)


def test_build_regime_summary_counts_and_majority():
    labels = {"A": "high", "B": "high", "C": "low", "D": None}
    result = publish_summary.build_regime_summary(labels)
    assert result["counts"] == {"low": 1, "normal": 0, "high": 2}
    assert result["majority_label"] == "high"
    assert result["n_symbols"] == 3


def test_build_regime_summary_empty_returns_none_majority():
    result = publish_summary.build_regime_summary({})
    assert result["majority_label"] is None
    assert result["n_symbols"] == 0


def test_build_ensemble_summary_weights_and_redundant_pairs():
    factor_ic_rows = [
        {"factor_name": "f1", "mean_ic": 0.3, "decayed": False},
        {"factor_name": "f2", "mean_ic": 0.6, "decayed": False},
    ]
    wide = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-01", "2020-01-01", "2020-01-02", "2020-01-02"]),
            "symbol": ["A", "B", "A", "B"],
            "f1": [1.0, 2.0, 3.0, 4.0],
            "f2": [2.0, 4.0, 6.0, 8.0],  # f1 ile birebir orantili
        }
    )
    factor_long_df = wide.melt(id_vars=["date", "symbol"], var_name="factor_name", value_name="value")

    result = publish_summary.build_ensemble_summary(factor_ic_rows, factor_long_df)
    weight_names = {w["factor_name"] for w in result["weights"]}
    assert weight_names == {"f1", "f2"}
    assert len(result["redundant_pairs"]) == 1
    assert {result["redundant_pairs"][0]["factor_a"], result["redundant_pairs"][0]["factor_b"]} == {"f1", "f2"}


def test_write_summary_atomic_roundtrip(tmp_path):
    path = tmp_path / "research_summary.json"
    summary = {"generated_at": "2020-01-01T00:00:00+00:00", "factor_ic": []}
    publish_summary.write_summary_atomic(summary, path=path)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded == summary


def test_assemble_summary_combines_all_pieces():
    result = publish_summary.assemble_summary(
        _factor_long_df(),
        _forward_returns_df(),
        regime_label_by_symbol={"A": "low", "B": "high"},
        n_active_filters=2,
    )
    assert set(result.keys()) == {"generated_at", "factor_ic", "regime", "ensemble", "attribution", "rule_burden"}
    assert result["regime"]["n_symbols"] == 2
    assert result["rule_burden"]["n_filters"] == 2


class _FakeEmptyLogger:
    def read_trades(self):
        return pd.DataFrame(columns=["event_type", "date", "symbol", "direction"])


def test_run_publish_summary_end_to_end_with_mocked_fetch(monkeypatch, tmp_path):
    df_a = make_flat_range_df(n=30, price=100.0)
    df_b = make_flat_range_df(n=30, price=50.0)

    monkeypatch.setattr(publish_summary, "fetch_universe", lambda symbols, start: {"A": df_a, "B": df_b})
    monkeypatch.setattr(publish_summary, "fetch_ohlcv", lambda ticker, start: pd.DataFrame(columns=["Close"]))
    monkeypatch.setattr(publish_summary, "PaperTradingLogger", _FakeEmptyLogger)
    monkeypatch.setattr(
        publish_summary,
        "load_factor_history",
        lambda: pd.DataFrame(columns=["date", "symbol", "factor_name", "value"]),
    )

    out_path = tmp_path / "research_summary.json"
    result = publish_summary.run_publish_summary(universe=["A", "B"], path=out_path)

    assert out_path.exists()
    assert result["regime"]["n_symbols"] == 2
    assert result["attribution"]["n_trades"] == 0
    loaded = json.loads(out_path.read_text(encoding="utf-8"))
    assert loaded["regime"]["n_symbols"] == 2


def test_run_publish_summary_computes_attribution_from_paired_trades(monkeypatch, tmp_path):
    closes = [100.0, 102.0, 104.0, 103.0, 108.0]
    df_thyao = _price_df_with_closes(closes)
    reference_df = _price_df_with_closes([100.0, 101.0, 102.0, 103.0, 104.0])

    class _FakeLogger:
        def read_trades(self):
            return pd.DataFrame(
                [
                    {"event_type": "entry", "date": df_thyao.index[0].strftime("%Y-%m-%d"), "symbol": "THYAO.IS", "direction": 1},
                    {"event_type": "exit", "date": df_thyao.index[-1].strftime("%Y-%m-%d"), "symbol": "THYAO.IS", "direction": 1},
                ]
            )

    monkeypatch.setattr(publish_summary, "fetch_universe", lambda symbols, start: {"THYAO.IS": df_thyao})
    monkeypatch.setattr(publish_summary, "fetch_ohlcv", lambda ticker, start: reference_df)
    monkeypatch.setattr(publish_summary, "PaperTradingLogger", _FakeLogger)
    monkeypatch.setattr(
        publish_summary,
        "load_factor_history",
        lambda: pd.DataFrame(columns=["date", "symbol", "factor_name", "value"]),
    )

    out_path = tmp_path / "research_summary.json"
    result = publish_summary.run_publish_summary(universe=["THYAO.IS"], path=out_path)

    assert result["attribution"]["n_trades"] == 1


def _price_df_with_closes(closes: list[float]) -> pd.DataFrame:
    """Tam OHLCV DataFrame'i (regime hesaplamasi icin High/Low de gerekli, sadece Close degil)."""
    dates = pd.date_range("2024-01-01", periods=len(closes), freq="B")
    return pd.DataFrame(
        {
            "Open": closes,
            "High": [c + 1.0 for c in closes],
            "Low": [c - 1.0 for c in closes],
            "Close": closes,
            "Volume": [1000.0] * len(closes),
        },
        index=dates,
    )


def test_build_attribution_summary_skips_symbols_without_reference():
    paired_trades = pd.DataFrame(
        [{"symbol": "BTC-USD", "entry_date": pd.Timestamp("2024-01-01"), "exit_date": pd.Timestamp("2024-01-05"), "direction": 1}]
    )
    price_data = {"BTC-USD": _price_df_with_closes([100.0, 101.0, 102.0, 103.0, 104.0])}
    result = publish_summary.build_attribution_summary(paired_trades, price_data, reference_data={})
    assert result["n_trades"] == 0


def test_build_attribution_summary_empty_paired_trades():
    result = publish_summary.build_attribution_summary(pd.DataFrame(), {}, {})
    assert result["n_trades"] == 0


def test_reference_ticker_for_symbol_bist_vs_other():
    assert publish_summary._reference_ticker_for_symbol("THYAO.IS") is not None
    assert publish_summary._reference_ticker_for_symbol("BTC-USD") is None
