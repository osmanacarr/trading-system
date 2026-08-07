"""notifications/telegram.py icin testler (gercek ag cagrisi yapilmaz,
requests.post mock'lanir - bkz. tests/test_fetch.py ile ayni monkeypatch
deseni)."""

from __future__ import annotations

import requests

import notifications.telegram as telegram_module
from notifications.telegram import send_telegram_message


class _FakeResponse:
    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


def test_send_telegram_message_missing_credentials_returns_false(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    called = False

    def fail_if_called(*args, **kwargs):
        nonlocal called
        called = True
        return _FakeResponse(200)

    monkeypatch.setattr(telegram_module.requests, "post", fail_if_called)

    result = send_telegram_message("test mesaji")

    assert result is False
    assert called is False


def test_send_telegram_message_success(monkeypatch):
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return _FakeResponse(200)

    monkeypatch.setattr(telegram_module.requests, "post", fake_post)

    result = send_telegram_message("🟢 GIRIS: EREGL.IS SHORT @ 38.66", bot_token="FAKE_TOKEN", chat_id="12345")

    assert result is True
    assert captured["url"] == "https://api.telegram.org/botFAKE_TOKEN/sendMessage"
    assert captured["json"] == {"chat_id": "12345", "text": "🟢 GIRIS: EREGL.IS SHORT @ 38.66"}


def test_send_telegram_message_network_error_returns_false(monkeypatch):
    def raise_network_error(*args, **kwargs):
        raise requests.exceptions.ConnectionError("baglanti kurulamadi")

    monkeypatch.setattr(telegram_module.requests, "post", raise_network_error)

    result = send_telegram_message("test mesaji", bot_token="FAKE_TOKEN", chat_id="12345")

    assert result is False


def test_send_telegram_message_api_error_status_returns_false(monkeypatch):
    monkeypatch.setattr(
        telegram_module.requests, "post", lambda *a, **k: _FakeResponse(401, "Unauthorized")
    )

    result = send_telegram_message("test mesaji", bot_token="BAD_TOKEN", chat_id="12345")

    assert result is False
