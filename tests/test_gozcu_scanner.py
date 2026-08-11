"""gozcu/scanner.py icin testler (ag cagrisi yapilmaz, batch fetch fonksiyonlari mock'lanir)."""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from data.fetch import OHLCV_COLUMNS
from gozcu import scanner


def test_write_and_load_snapshot_roundtrip(tmp_path):
    path = tmp_path / "snapshot.json"
    data = {"generated_at": "2024-01-01T00:00:00+00:00", "markets": {"bist": {"market_open": True}}}
    scanner._write_snapshot_atomic(data, path=path)
    loaded = scanner._load_previous_snapshot(path)
    assert loaded == data


def test_load_previous_snapshot_missing_file_returns_empty(tmp_path):
    path = tmp_path / "missing.json"
    assert scanner._load_previous_snapshot(path) == {}


def test_load_previous_snapshot_corrupt_file_returns_empty(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not valid json", encoding="utf-8")
    assert scanner._load_previous_snapshot(path) == {}


def test_run_scan_closed_market_preserves_previous_data(monkeypatch, tmp_path):
    snapshot_path = tmp_path / "snapshot.json"
    previous = {
        "generated_at": "2024-01-01T00:00:00+00:00",
        "markets": {
            "bist": {
                "market_open": True,
                "scanned_at": "2024-01-01T10:00:00+00:00",
                "attention_list": [{"symbol": "THYAO.IS"}],
            }
        },
    }
    scanner._write_snapshot_atomic(previous, path=snapshot_path)

    monkeypatch.setattr(scanner, "GOZCU_SNAPSHOT_PATH", snapshot_path)
    monkeypatch.setattr(scanner.market_hours, "is_bist_open", lambda now: False)
    monkeypatch.setattr(scanner.alerts, "load_alert_state", lambda: {})
    monkeypatch.setattr(scanner.alerts, "save_alert_state", lambda state: None)

    result = scanner.run_scan(markets=["bist"], now=dt.datetime(2024, 1, 2, tzinfo=dt.timezone.utc))

    assert result["markets"]["bist"]["market_open"] is False
    assert result["markets"]["bist"]["attention_list"] == [{"symbol": "THYAO.IS"}]


def test_scan_market_ranks_attention_list_by_score(monkeypatch):
    dates = pd.date_range("2024-01-01", periods=30, freq="B")

    def make_daily(spike_pct: float) -> pd.DataFrame:
        closes = np.full(30, 100.0)
        closes[-1] = 100.0 * (1 + spike_pct)
        return pd.DataFrame(
            {"Open": closes, "High": closes + 1, "Low": closes - 1, "Close": closes, "Volume": np.full(30, 1000.0)},
            index=dates,
        )

    daily_data = {"AAA.IS": make_daily(0.20), "BBB.IS": make_daily(0.01)}
    intraday_dates = pd.date_range(f"{dates[-1].date()} 10:00", periods=3, freq="5min")
    intraday_data = {
        s: pd.DataFrame(
            {"High": [101] * 3, "Low": [99] * 3, "Close": [100] * 3, "Volume": [500, 500, 500]},
            index=intraday_dates,
        )
        for s in daily_data
    }

    monkeypatch.setattr(
        scanner,
        "fetch_daily_batch",
        lambda symbols: {s: daily_data.get(s, pd.DataFrame(columns=OHLCV_COLUMNS)) for s in symbols},
    )
    monkeypatch.setattr(
        scanner,
        "fetch_intraday_batch",
        lambda symbols: {s: intraday_data.get(s, pd.DataFrame(columns=OHLCV_COLUMNS)) for s in symbols},
    )

    now = dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)
    result = scanner.scan_market(
        "bist",
        ["AAA.IS", "BBB.IS"],
        "XU100.IS",
        "^XU100",
        session_progress_fn=lambda ts: 0.5,
        now=now,
        actually_open=True,
    )

    assert result["market_open"] is True
    assert result["scanned_count"] == 2
    assert result["error_count"] == 0
    assert result["attention_list"][0]["symbol"] == "AAA.IS"  # daha buyuk gunluk degisim -> daha yuksek skor
    assert result["correlation"]["average_correlation"] is None  # referans verisi yok (fetch bos donuyor)


def test_compute_symbol_metrics_uses_last_intraday_bar_timestamp_for_session_progress():
    # KOK NEDEN DUZELTMESI: RVOL, tek bir market-genelinde "su an" (wall-clock)
    # degeri yerine, HER sembolun kendi son gun-ici barinin zaman damgasindan
    # hesaplanan seans-ilerleme oranini kullanmali - piyasa kapaliyken (veri
    # bir onceki TAMAMLANMIS seansa ait oldugunda) "su an" o seansla alakasiz
    # oldugu icin RVOL'u yanlislikla None yapiyordu (bkz. ilgili hata raporu).
    dates = pd.date_range("2024-01-01", periods=30, freq="B")
    daily_df = pd.DataFrame(
        {"Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100.0, "Volume": 1000.0},
        index=dates,
    )
    intraday_dates = pd.date_range("2024-01-30 10:00", periods=3, freq="5min", tz="UTC")
    intraday_df = pd.DataFrame(
        {"High": [101] * 3, "Low": [99] * 3, "Close": [100] * 3, "Volume": [500, 500, 500]},
        index=intraday_dates,
    )

    received_timestamps = []

    def fake_session_progress(ts):
        received_timestamps.append(ts)
        return 0.5

    result = scanner._compute_symbol_metrics("AAA", daily_df, intraday_df, fake_session_progress)

    assert received_timestamps == [intraday_dates[-1]]
    assert result["rvol"] is not None


def test_compute_symbol_metrics_empty_intraday_skips_session_progress_call():
    dates = pd.date_range("2024-01-01", periods=30, freq="B")
    daily_df = pd.DataFrame(
        {"Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100.0, "Volume": 1000.0},
        index=dates,
    )
    calls = []

    def fake_session_progress(ts):
        calls.append(ts)
        return 0.5

    result = scanner._compute_symbol_metrics("AAA", daily_df, pd.DataFrame(columns=OHLCV_COLUMNS), fake_session_progress)

    assert calls == []
    assert result["rvol"] is None


def test_scan_market_market_open_reflects_actually_open_flag(monkeypatch):
    dates = pd.date_range("2024-01-01", periods=30, freq="B")
    close = 100.0 + np.sin(np.arange(30))  # sabit olmayan seri: korelasyon std=0 uyarisini onler
    daily_df = pd.DataFrame(
        {"Open": close, "High": close + 1, "Low": close - 1, "Close": close, "Volume": np.full(30, 1000.0)},
        index=dates,
    )
    monkeypatch.setattr(scanner, "fetch_daily_batch", lambda symbols: {s: daily_df for s in symbols})
    monkeypatch.setattr(
        scanner, "fetch_intraday_batch", lambda symbols: {s: pd.DataFrame(columns=OHLCV_COLUMNS) for s in symbols}
    )

    now = dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)
    # force ile tetiklenen ama piyasa GERCEKTE kapali bir tarama - donen
    # market_open, tetiklenme sebebinden BAGIMSIZ olarak gercek durumu yansitmali.
    result = scanner.scan_market(
        "nasdaq", ["AAA"], "QQQ", None, session_progress_fn=lambda ts: 0.0, now=now, actually_open=False
    )
    assert result["market_open"] is False
