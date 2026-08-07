"""data/fetch.py icin testler (ag cagrisi yapilmaz, yf.download mock'lanir)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import data.fetch as fetch_module


def _fake_download(ticker, start=None, end=None, interval=None, auto_adjust=None, progress=None, multi_level_index=None):
    dates = pd.date_range("2022-01-03", periods=5, freq="B")
    return pd.DataFrame(
        {
            "Open": np.full(5, 10.0),
            "High": np.full(5, 11.0),
            "Low": np.full(5, 9.0),
            "Close": np.full(5, 10.5),
            "Volume": np.full(5, 1000.0),
        },
        index=dates,
    )


def test_fetch_ohlcv_returns_expected_columns(monkeypatch):
    monkeypatch.setattr(fetch_module.yf, "download", _fake_download)
    df = fetch_module.fetch_ohlcv("FAKE.IS", start="2022-01-01")
    assert list(df.columns) == fetch_module.OHLCV_COLUMNS
    assert len(df) == 5


def test_fetch_ohlcv_empty_ticker_raises():
    with pytest.raises(ValueError):
        fetch_module.fetch_ohlcv("", start="2022-01-01")


def test_fetch_ohlcv_empty_response_returns_empty_df(monkeypatch):
    monkeypatch.setattr(fetch_module.yf, "download", lambda *a, **k: pd.DataFrame())
    df = fetch_module.fetch_ohlcv("NOPE.IS", start="2022-01-01")
    assert df.empty
    assert list(df.columns) == fetch_module.OHLCV_COLUMNS


def test_fetch_universe_handles_partial_failures(monkeypatch):
    def flaky_download(ticker, **kwargs):
        if ticker == "BAD.IS":
            raise RuntimeError("network error")
        return _fake_download(ticker, **kwargs)

    monkeypatch.setattr(fetch_module.yf, "download", flaky_download)
    result = fetch_module.fetch_universe(["GOOD.IS", "BAD.IS"], start="2022-01-01")
    assert len(result["GOOD.IS"]) == 5
    assert result["BAD.IS"].empty
