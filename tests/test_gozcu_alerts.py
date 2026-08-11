"""gozcu/alerts.py icin testler (Telegram gonderimi mock'lanir, ag cagrisi yapilmaz)."""

from __future__ import annotations

import datetime as dt

from gozcu import alerts


def test_should_alert_true_when_never_warned():
    assert alerts.should_alert("AAPL", dt.date(2024, 1, 1), {}) is True


def test_should_alert_false_on_same_day():
    state = {"AAPL": "2024-01-01"}
    assert alerts.should_alert("AAPL", dt.date(2024, 1, 1), state) is False


def test_should_alert_true_on_new_day():
    state = {"AAPL": "2024-01-01"}
    assert alerts.should_alert("AAPL", dt.date(2024, 1, 2), state) is True


def test_record_alert_returns_new_dict_without_mutating_original():
    state: dict[str, str] = {}
    updated = alerts.record_alert("AAPL", dt.date(2024, 1, 1), state)
    assert state == {}
    assert updated == {"AAPL": "2024-01-01"}


def test_save_and_load_alert_state_roundtrip(tmp_path):
    path = tmp_path / "alert_state.json"
    alerts.save_alert_state({"AAPL": "2024-01-01"}, path=path)
    loaded = alerts.load_alert_state(path=path)
    assert loaded == {"AAPL": "2024-01-01"}


def test_load_alert_state_missing_file_returns_empty(tmp_path):
    path = tmp_path / "missing.json"
    assert alerts.load_alert_state(path=path) == {}


def test_load_alert_state_corrupt_file_returns_empty(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not valid json", encoding="utf-8")
    assert alerts.load_alert_state(path=path) == {}


def test_maybe_send_attention_alert_sends_once_per_day(monkeypatch):
    sent: list[str] = []
    monkeypatch.setattr(alerts, "send_telegram_message", lambda text: sent.append(text) or True)

    state: dict[str, str] = {}
    state = alerts.maybe_send_attention_alert(
        "THYAO.IS", "BIST", 9.0, 3.2, state, today=dt.date(2024, 1, 1), threshold=8.0
    )
    assert len(sent) == 1
    assert "THYAO.IS" in sent[0]
    assert "AL sinyali" in sent[0]

    state = alerts.maybe_send_attention_alert(
        "THYAO.IS", "BIST", 9.0, 3.2, state, today=dt.date(2024, 1, 1), threshold=8.0
    )
    assert len(sent) == 1  # ayni gun tekrar gonderilmez


def test_maybe_send_attention_alert_below_threshold_not_sent(monkeypatch):
    sent: list[str] = []
    monkeypatch.setattr(alerts, "send_telegram_message", lambda text: sent.append(text) or True)

    state = alerts.maybe_send_attention_alert(
        "AAPL", "NASDAQ", 3.0, 1.1, {}, today=dt.date(2024, 1, 1), threshold=8.0
    )
    assert sent == []
    assert state == {}


def test_maybe_send_attention_alert_new_day_sends_again(monkeypatch):
    sent: list[str] = []
    monkeypatch.setattr(alerts, "send_telegram_message", lambda text: sent.append(text) or True)

    state = alerts.maybe_send_attention_alert(
        "AAPL", "NASDAQ", 9.0, 2.0, {}, today=dt.date(2024, 1, 1), threshold=8.0
    )
    state = alerts.maybe_send_attention_alert(
        "AAPL", "NASDAQ", 9.0, 2.0, state, today=dt.date(2024, 1, 2), threshold=8.0
    )
    assert len(sent) == 2
