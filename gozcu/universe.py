"""gozcu/universe.py - BIST ve NASDAQ-100 evrenlerini dinamik olarak ceker.

Her iki fonksiyon da Wikipedia'daki bir tabloyu parse eder; agin/tablonun
degismesi, agin erisilemez olmasi gibi durumlarda ISTISNA FIRLATMAZ, statik
bir yedek listeye duser (gozcu/scanner.py'nin surekli calisir kalmasi
gerektigi icin - bkz. gozcu paketi genel felsefesi).

BIST notu: pd.read_html ile parse edilebilir, gercek "BIST100 endeks
bilesenleri" tablosu bulunamadi (Borsa Istanbul/Wikipedia'nin BIST100
sayfalarinda yapilandirilmis bir tablo yok). Bunun yerine Borsa Istanbul'a
kote TUM sirketleri listeleyen (BIST100'den daha genis) tablo kullanilir -
bkz. config.GOZCU_BIST_WIKI_URL yorumu ve README "GOZCU mimarisi" bolumu.

User-Agent notu: Wikipedia, pd.read_html'in varsayilan (User-Agent'siz)
urllib istegini 403 Forbidden ile reddediyor - bu yuzden sayfa ONCE
`requests` ile (tarayici benzeri bir User-Agent'la) cekilir, HTML METNI
pd.read_html'e URL yerine dogrudan verilir (bkz. _fetch_tables).
"""

from __future__ import annotations

import logging
import re
from io import StringIO

import pandas as pd
import requests

from config import (
    BIST_TICKERS,
    GOZCU_BIST_WIKI_URL,
    GOZCU_NASDAQ100_FALLBACK,
    GOZCU_NASDAQ100_WIKI_URL,
)

log = logging.getLogger("gozcu.universe")

_FOOTNOTE_RE = re.compile(r"\[.*?\]")
_REQUEST_TIMEOUT_SECONDS = 15
_USER_AGENT = "Mozilla/5.0 (compatible; gozcu-bot/1.0; NASDAQ+BIST izleme paneli)"


def _fetch_tables(url: str) -> list[pd.DataFrame]:
    """Sayfayi tarayici benzeri bir User-Agent ile ceker ve tum tablolarini parse eder."""
    response = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=_REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return pd.read_html(StringIO(response.text))


def _clean_symbol(raw: str) -> str | None:
    """Bir tablo hucresindeki tek bir sembolu normalize eder.

    Wikipedia footnote referanslarini ("AKBNK[1]") temizler, sadece
    harf/rakam/nokta iceren gecerli gorunumlu sembolleri kabul eder.
    """
    symbol = _FOOTNOTE_RE.sub("", raw).strip().upper()
    if not symbol or not symbol.isascii():
        return None
    if not re.fullmatch(r"[A-Z0-9.]+", symbol):
        return None
    return symbol


def get_bist_universe() -> list[str]:
    """Borsa Istanbul'a kote sirketlerin yfinance sembol listesini ceker.

    Returns:
        ".IS" son ekli, tekillestirilmis, alfabetik sirali sembol listesi.
        Cekme/parse basarisiz olursa veya sonuc bos donerse config.BIST_TICKERS
        (13 likit sembol) donulur.
    """
    try:
        tables = _fetch_tables(GOZCU_BIST_WIKI_URL)
    except Exception:
        log.warning("BIST evreni Wikipedia'dan cekilemedi, statik listeye dusuluyor")
        return list(BIST_TICKERS)

    symbols: set[str] = set()
    for table in tables:
        if "Symbol" not in table.columns:
            continue
        for cell in table["Symbol"].dropna():
            for raw in str(cell).split(","):
                symbol = _clean_symbol(raw)
                if symbol:
                    symbols.add(f"{symbol}.IS")

    if not symbols:
        log.warning("BIST evreni tablosu bos/parse edilemedi, statik listeye dusuluyor")
        return list(BIST_TICKERS)
    return sorted(symbols)


def get_nasdaq100_universe() -> list[str]:
    """NASDAQ-100 sirketlerinin yfinance sembol listesini ceker.

    Returns:
        Tekillestirilmis, alfabetik sirali sembol listesi. Cekme/parse
        basarisiz olursa veya sonuc bos donerse config.GOZCU_NASDAQ100_FALLBACK
        (bilinen ~38 buyuk isim) donulur.
    """
    try:
        tables = _fetch_tables(GOZCU_NASDAQ100_WIKI_URL)
    except Exception:
        log.warning("NASDAQ-100 evreni Wikipedia'dan cekilemedi, statik listeye dusuluyor")
        return list(GOZCU_NASDAQ100_FALLBACK)

    symbols: set[str] = set()
    for table in tables:
        ticker_col = next((c for c in table.columns if str(c).strip() in ("Ticker", "Symbol")), None)
        if ticker_col is None:
            continue
        for cell in table[ticker_col].dropna():
            symbol = _clean_symbol(str(cell))
            if symbol:
                symbols.add(symbol)

    if not symbols:
        log.warning("NASDAQ-100 evreni tablosu bos/parse edilemedi, statik listeye dusuluyor")
        return list(GOZCU_NASDAQ100_FALLBACK)
    return sorted(symbols)
