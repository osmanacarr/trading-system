"""paper_trading/action_sheet.py icin sentetik pozisyon verisiyle testler.

state.db'ye HIC dokunulmuyor - build_action_sheet saf bir fonksiyon
(PositionRecord listesi + mark_prices -> ActionSheetEntry listesi), bu
yuzden testler dogrudan PositionRecord nesneleri kurar (bkz.
tests/test_paper_state.py'deki gecici-db deseninin AKSINE, burada gerek yok).
"""

from __future__ import annotations

import datetime as dt
import json

import pandas as pd
import pytest

from paper_trading import action_sheet
from paper_trading.state import PositionRecord


def _pos(
    symbol="THYAO.IS",
    strategy="donchian",
    direction=1,
    entry_date=dt.date(2026, 8, 10),
    entry_price=100.0,
    stop_price=95.0,
    size=20.0,
) -> PositionRecord:
    return PositionRecord(
        symbol=symbol, strategy=strategy, direction=direction, entry_date=entry_date,
        entry_price=entry_price, stop_price=stop_price, size=size,
    )


RUN_DATE = dt.date(2026, 8, 12)


def test_long_position_is_applicable_by_default():
    entries = action_sheet.build_action_sheet([_pos(direction=1)], RUN_DATE)
    assert entries[0].applicable is True


def test_short_position_not_applicable_when_user_can_short_false():
    assert action_sheet.USER_CAN_SHORT is False  # bkz. config.py - varsayilan
    entries = action_sheet.build_action_sheet([_pos(direction=-1)], RUN_DATE)
    assert entries[0].applicable is False


def test_short_position_applicable_when_user_can_short_true(monkeypatch):
    monkeypatch.setattr(action_sheet, "USER_CAN_SHORT", True)
    entries = action_sheet.build_action_sheet([_pos(direction=-1)], RUN_DATE)
    assert entries[0].applicable is True


def test_is_new_today_flag_true_when_entry_date_matches_run_date():
    entries = action_sheet.build_action_sheet([_pos(entry_date=RUN_DATE)], RUN_DATE)
    assert entries[0].is_new_today is True


def test_is_new_today_flag_false_for_older_position():
    entries = action_sheet.build_action_sheet([_pos(entry_date=dt.date(2026, 8, 1))], RUN_DATE)
    assert entries[0].is_new_today is False


def test_days_open_calculation():
    entries = action_sheet.build_action_sheet([_pos(entry_date=dt.date(2026, 8, 5))], RUN_DATE)
    assert entries[0].days_open == 7


def test_stop_distance_and_near_stop_flag_when_price_close_to_stop():
    # entry=100, stop=95 -> initial_risk=5; guncel fiyat 95.5 -> distance_to_stop=0.5
    # esik: STOP_PROXIMITY_WARNING_PCT(0.20) * 5 = 1.0 -> 0.5 < 1.0 -> yakin.
    pos = _pos(entry_price=100.0, stop_price=95.0)
    entries = action_sheet.build_action_sheet([pos], RUN_DATE, mark_prices={"THYAO.IS": 95.5})
    assert entries[0].current_price == 95.5
    assert entries[0].is_near_stop is True
    assert entries[0].stop_distance_pct == pytest.approx(abs(95.5 - 95.0) / 95.5 * 100)


def test_stop_distance_none_and_not_near_when_no_mark_price():
    entries = action_sheet.build_action_sheet([_pos()], RUN_DATE, mark_prices={})
    assert entries[0].current_price is None
    assert entries[0].stop_distance_pct is None
    assert entries[0].is_near_stop is False


def test_exit_explanation_mentions_trailing_for_donchian():
    entries = action_sheet.build_action_sheet([_pos(strategy="donchian")], RUN_DATE)
    assert "takip stopu" in entries[0].exit_explanation
    assert "HER GUN" in entries[0].exit_explanation


def test_exit_explanation_mentions_fixed_target_for_price_action():
    entries = action_sheet.build_action_sheet([_pos(strategy="price_action")], RUN_DATE)
    assert "SABIT" in entries[0].exit_explanation


def test_format_action_steps_does_not_leak_a_quantity_number():
    entries = action_sheet.build_action_sheet([_pos(direction=1)], RUN_DATE)
    text = action_sheet.format_action_steps(entries[0])
    assert "THYAO.IS" in text
    assert "dashboard" in text.lower()
    # Gercek sermaye sunucuda YOK - "Miktar" satirinda somut bir adet sayisi OLMAMALI.
    assert "adet" not in text.split("Miktar:")[1].split("\n")[0].lower() or "gercek sermayenize" in text


def test_telegram_summary_empty_string_when_no_open_positions():
    assert action_sheet.format_daily_telegram_summary([], RUN_DATE) == ""


def test_unrealized_pnl_pct_computed_for_long_and_short():
    long_pos = _pos(symbol="THYAO.IS", direction=1, entry_price=100.0)
    short_pos = _pos(symbol="EREGL.IS", direction=-1, entry_price=100.0, stop_price=105.0)
    entries = action_sheet.build_action_sheet(
        [long_pos, short_pos], RUN_DATE, mark_prices={"THYAO.IS": 110.0, "EREGL.IS": 110.0}
    )
    by_symbol = {e.symbol: e for e in entries}
    assert by_symbol["THYAO.IS"].unrealized_pnl_pct == pytest.approx(10.0)  # LONG, fiyat yukseldi -> kar
    assert by_symbol["EREGL.IS"].unrealized_pnl_pct == pytest.approx(-10.0)  # SHORT, fiyat yukseldi -> zarar


def test_unrealized_pnl_pct_none_when_no_mark_price():
    entries = action_sheet.build_action_sheet([_pos()], RUN_DATE, mark_prices={})
    assert entries[0].unrealized_pnl_pct is None


def test_refresh_live_prices_returns_false_when_file_missing(tmp_path):
    missing_path = tmp_path / "does_not_exist.json"
    assert action_sheet.refresh_live_prices(path=missing_path, fetch_batch_fn=lambda symbols: {}) is False


def test_refresh_live_prices_updates_price_fields_in_place(tmp_path):
    pos = _pos(symbol="THYAO.IS", direction=1, entry_price=100.0, stop_price=95.0)
    entries = action_sheet.build_action_sheet([pos], RUN_DATE, mark_prices={"THYAO.IS": 100.0})
    out_path = action_sheet.write_action_sheet_json(entries, RUN_DATE, path=tmp_path / "action_sheet.json")
    original = json.loads(out_path.read_text(encoding="utf-8"))

    def fake_fetch(symbols):
        assert symbols == ["THYAO.IS"]
        return {"THYAO.IS": pd.DataFrame({"Close": [108.0]})}

    updated = action_sheet.refresh_live_prices(path=out_path, fetch_batch_fn=fake_fetch)
    assert updated is True

    data = json.loads(out_path.read_text(encoding="utf-8"))
    entry = data["entries"][0]
    assert entry["current_price"] == 108.0
    assert entry["unrealized_pnl_pct"] == pytest.approx(8.0)
    assert entry["stop_distance_pct"] == pytest.approx(abs(108.0 - 95.0) / 108.0 * 100)
    # Fiyat-bagimsiz alanlar DEGISMEMELI (yeniden uretilmiyor, sadece yerinde guncelleniyor).
    assert entry["entry_price"] == original["entries"][0]["entry_price"]
    assert entry["exit_explanation"] == original["entries"][0]["exit_explanation"]
    assert data["generated_at"] == original["generated_at"]
    assert data["prices_updated_at"] != original["prices_updated_at"]


def test_refresh_live_prices_skips_symbol_gracefully_when_fetch_empty(tmp_path):
    pos = _pos(symbol="THYAO.IS", direction=1, entry_price=100.0, stop_price=95.0)
    entries = action_sheet.build_action_sheet([pos], RUN_DATE, mark_prices={"THYAO.IS": 100.0})
    out_path = action_sheet.write_action_sheet_json(entries, RUN_DATE, path=tmp_path / "action_sheet.json")

    updated = action_sheet.refresh_live_prices(path=out_path, fetch_batch_fn=lambda symbols: {"THYAO.IS": pd.DataFrame()})
    assert updated is True

    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["entries"][0]["current_price"] == 100.0  # eski deger korunuyor, ezilmiyor


def test_telegram_summary_separates_actionable_and_watch_only():
    entries = action_sheet.build_action_sheet(
        [_pos(symbol="THYAO.IS", direction=1), _pos(symbol="EREGL.IS", direction=-1)], RUN_DATE
    )
    text = action_sheet.format_daily_telegram_summary(entries, RUN_DATE)
    assert "THYAO.IS" in text
    assert "SADECE IZLEME" in text
    assert "EREGL.IS" in text
    assert "uygulanabilir 1 pozisyon" in text


def test_write_action_sheet_json_roundtrip(tmp_path):
    entries = action_sheet.build_action_sheet([_pos()], RUN_DATE, mark_prices={"THYAO.IS": 101.0})
    out_path = action_sheet.write_action_sheet_json(entries, RUN_DATE, path=tmp_path / "action_sheet.json")
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["run_date"] == RUN_DATE.isoformat()
    assert data["disclaimer"] == action_sheet.DISCLAIMER
    assert len(data["entries"]) == 1
    assert data["entries"][0]["symbol"] == "THYAO.IS"
