"""gozcu/data_fetch.py icin testler (ag cagrisi yapilmaz, yf.download mock'lanir)."""

from __future__ import annotations

import numpy as np
import pandas as pd

import gozcu.data_fetch as data_fetch_module


def _fake_multi_download(tickers=None, **kwargs):
    dates = pd.date_range("2024-01-02", periods=3, freq="B")
    frames = {}
    for t in tickers:
        frames[t] = pd.DataFrame(
            {
                "Open": np.full(3, 10.0),
                "High": np.full(3, 11.0),
                "Low": np.full(3, 9.0),
                "Close": np.full(3, 10.5),
                "Volume": np.full(3, 1000.0),
            },
            index=dates,
        )
    return pd.concat(frames, axis=1)


def test_fetch_ohlcv_batch_parses_multiindex_response(monkeypatch):
    monkeypatch.setattr(data_fetch_module.yf, "download", _fake_multi_download)
    result = data_fetch_module.fetch_ohlcv_batch(["AAA.IS", "BBB.IS"], period="5d", interval="1d")
    assert set(result.keys()) == {"AAA.IS", "BBB.IS"}
    assert len(result["AAA.IS"]) == 3
    assert list(result["AAA.IS"].columns) == data_fetch_module.OHLCV_COLUMNS


def test_fetch_ohlcv_batch_splits_into_chunks(monkeypatch):
    calls: list[list[str]] = []

    def recording_download(tickers=None, **kwargs):
        calls.append(list(tickers))
        return _fake_multi_download(tickers=tickers, **kwargs)

    monkeypatch.setattr(data_fetch_module.yf, "download", recording_download)
    tickers = [f"T{i}.IS" for i in range(5)]
    result = data_fetch_module.fetch_ohlcv_batch(tickers, period="5d", chunk_size=2)

    assert len(calls) == 3  # 2 + 2 + 1
    assert sum(len(c) for c in calls) == 5
    assert set(result.keys()) == set(tickers)


def test_fetch_ohlcv_batch_chunk_failure_returns_empty_frames(monkeypatch):
    def flaky_download(tickers=None, **kwargs):
        raise RuntimeError("network error")

    monkeypatch.setattr(data_fetch_module.yf, "download", flaky_download)
    result = data_fetch_module.fetch_ohlcv_batch(["AAA.IS"], period="5d")
    assert result["AAA.IS"].empty
    assert list(result["AAA.IS"].columns) == data_fetch_module.OHLCV_COLUMNS


def test_fetch_ohlcv_batch_empty_ticker_list_returns_empty_dict():
    assert data_fetch_module.fetch_ohlcv_batch([], period="5d") == {}


def test_fetch_ohlcv_batch_missing_ticker_in_response_returns_empty_frame(monkeypatch):
    def partial_download(tickers=None, **kwargs):
        return _fake_multi_download(tickers=["AAA.IS"], **kwargs)

    monkeypatch.setattr(data_fetch_module.yf, "download", partial_download)
    result = data_fetch_module.fetch_ohlcv_batch(["AAA.IS", "MISSING.IS"], period="5d")
    assert len(result["AAA.IS"]) == 3
    assert result["MISSING.IS"].empty


def test_fetch_daily_batch_corrects_price_jumps(monkeypatch):
    # data/adjust.py: bir sicramanin ONCEKI barlari geriye donuk olceklenir,
    # boylece son barin gunluk getirisi (sicrama) yapay olarak yok edilir.
    def jumpy_download(tickers=None, **kwargs):
        dates = pd.date_range("2024-01-02", periods=3, freq="B")
        frames = {}
        for t in tickers:
            close = [100.0, 101.0, 1200.0]  # son barda sahte %1088 sicrama
            frames[t] = pd.DataFrame(
                {"Open": close, "High": close, "Low": close, "Close": close, "Volume": np.full(3, 1000.0)},
                index=dates,
            )
        return pd.concat(frames, axis=1)

    monkeypatch.setattr(data_fetch_module.yf, "download", jumpy_download)
    result = data_fetch_module.fetch_daily_batch(["AAA.IS"])
    close = result["AAA.IS"]["Close"]
    assert np.isclose(close.iloc[-1], 1200.0)  # son bar DEGISMEZ
    assert np.isclose(close.iloc[-2], 1200.0)  # onceki bar sicramaya gore olceklendi
