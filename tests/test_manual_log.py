"""paper_trading/manual_log.py icin testler."""

from __future__ import annotations

import datetime as dt

from paper_trading.manual_log import read_manual_entries, record_manual_entry, slippage_pct


def test_record_and_read_manual_entry_roundtrip(tmp_path):
    log_path = tmp_path / "manual_trades.jsonl"

    record_manual_entry(
        symbol="EREGL.IS",
        signal_date=dt.date(2026, 8, 7),
        user_entry_price=38.90,
        user_size=32.0,
        system_entry_price=38.66,
        note="Piyasa emriyle acildi",
        log_path=log_path,
    )

    entries = read_manual_entries(log_path=log_path)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["symbol"] == "EREGL.IS"
    assert entry["signal_date"] == "2026-08-07"
    assert entry["user_entry_price"] == 38.90
    assert entry["system_entry_price"] == 38.66
    assert entry["note"] == "Piyasa emriyle acildi"
    assert "marked_at" in entry


def test_read_manual_entries_missing_file_returns_empty_list(tmp_path):
    entries = read_manual_entries(log_path=tmp_path / "nope.jsonl")
    assert entries == []


def test_record_manual_entry_appends_multiple(tmp_path):
    log_path = tmp_path / "manual_trades.jsonl"
    record_manual_entry("EREGL.IS", dt.date(2026, 8, 7), 38.90, 32.0, log_path=log_path)
    record_manual_entry("BTC-USD", dt.date(2026, 8, 8), 61_500.0, 0.01, log_path=log_path)

    entries = read_manual_entries(log_path=log_path)
    assert [e["symbol"] for e in entries] == ["EREGL.IS", "BTC-USD"]


def test_slippage_pct_computes_relative_difference():
    record = {"system_entry_price": 100.0, "user_entry_price": 102.0}
    assert slippage_pct(record) == 0.02


def test_slippage_pct_none_when_system_price_missing():
    record = {"system_entry_price": None, "user_entry_price": 102.0}
    assert slippage_pct(record) is None
