"""gozcu/universe.py icin testler (ag cagrisi yapilmaz, requests.get mock'lanir)."""

from __future__ import annotations

import pandas as pd

import gozcu.universe as universe_module
from config import BIST_TICKERS, GOZCU_NASDAQ100_FALLBACK


class _FakeResponse:
    def __init__(self, html: str):
        self.text = html

    def raise_for_status(self) -> None:
        pass


def _fake_get(html: str):
    return lambda url, headers=None, timeout=None: _FakeResponse(html)


def test_get_bist_universe_parses_symbol_column(monkeypatch):
    table = pd.DataFrame(
        {
            "Company": ["Akbank", "Adana Cimento"],
            "Symbol": ["AKBNK", "ADANA, ADBGR"],
            "Notes": ["...", "..."],
        }
    )
    monkeypatch.setattr(universe_module.requests, "get", _fake_get(table.to_html()))
    result = universe_module.get_bist_universe()
    assert "AKBNK.IS" in result
    assert "ADANA.IS" in result
    assert "ADBGR.IS" in result
    assert result == sorted(result)


def test_get_bist_universe_falls_back_on_request_exception(monkeypatch):
    def raise_error(url, headers=None, timeout=None):
        raise RuntimeError("network error")

    monkeypatch.setattr(universe_module.requests, "get", raise_error)
    assert universe_module.get_bist_universe() == list(BIST_TICKERS)


def test_get_bist_universe_falls_back_on_missing_symbol_column(monkeypatch):
    table = pd.DataFrame({"Company": ["X"], "Notes": ["Y"]})
    monkeypatch.setattr(universe_module.requests, "get", _fake_get(table.to_html()))
    assert universe_module.get_bist_universe() == list(BIST_TICKERS)


def test_get_bist_universe_filters_short_section_header_artifacts(monkeypatch):
    # Canli testte gozlemlendi: Wikipedia'nin alfabetik bolum basliklari
    # ("A", "B", ...) bazen "Symbol" hucresi gibi parse ediliyor - bunlar
    # gercek BIST sembolu degil (en kisa gercek sembol >=3 karakter).
    table = pd.DataFrame(
        {"Company": ["A (bolum basligi)", "Akbank"], "Symbol": ["A", "AKBNK"], "Notes": ["", ""]}
    )
    monkeypatch.setattr(universe_module.requests, "get", _fake_get(table.to_html()))
    result = universe_module.get_bist_universe()
    assert "A.IS" not in result
    assert "AKBNK.IS" in result


def test_get_nasdaq100_universe_parses_ticker_column(monkeypatch):
    table = pd.DataFrame({"Ticker": ["AAPL", "MSFT"], "Company": ["Apple", "Microsoft"]})
    monkeypatch.setattr(universe_module.requests, "get", _fake_get(table.to_html()))
    result = universe_module.get_nasdaq100_universe()
    assert result == ["AAPL", "MSFT"]


def test_get_nasdaq100_universe_keeps_short_two_letter_tickers(monkeypatch):
    # NASDAQ'ta "ON" (ON Semiconductor) gibi gecerli 2 harfli tikerlar var -
    # BIST'e ozel min_length=3 filtresi NASDAQ tarafina uygulanmamali.
    table = pd.DataFrame({"Ticker": ["ON", "AAPL"], "Company": ["ON Semiconductor", "Apple"]})
    monkeypatch.setattr(universe_module.requests, "get", _fake_get(table.to_html()))
    result = universe_module.get_nasdaq100_universe()
    assert "ON" in result


def test_get_nasdaq100_universe_falls_back_on_request_exception(monkeypatch):
    def raise_error(url, headers=None, timeout=None):
        raise RuntimeError("network error")

    monkeypatch.setattr(universe_module.requests, "get", raise_error)
    assert universe_module.get_nasdaq100_universe() == list(GOZCU_NASDAQ100_FALLBACK)
