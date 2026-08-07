"""yfinance uzerinden gunluk (gerekirse gun ici) OHLCV veri cekme.

Kaynak: proje iskeleti talebi - "data/fetch.py: yfinance ile veri cekme
(gunluk + gerekirse gun ici)".
"""

from __future__ import annotations

import pandas as pd
import yfinance as yf

OHLCV_COLUMNS: list[str] = ["Open", "High", "Low", "Close", "Volume"]


def fetch_ohlcv(
    ticker: str,
    start: str,
    end: str | None = None,
    interval: str = "1d",
) -> pd.DataFrame:
    """Tek bir sembol icin OHLCV verisini yfinance'tan ceker.

    Args:
        ticker: yfinance sembolu (orn. "THYAO.IS", "BTC-USD").
        start: Baslangic tarihi, "YYYY-MM-DD" formatinda.
        end: Bitis tarihi, "YYYY-MM-DD" formatinda. None ise bugune kadar.
        interval: yfinance interval kodu ("1d", "1h", "5m" vb.).

    Returns:
        DatetimeIndex'li, ["Open", "High", "Low", "Close", "Volume"]
        kolonlarina sahip bir DataFrame. Veri bulunamazsa bos DataFrame
        doner.

    Raises:
        ValueError: ticker bos string ise.
    """
    if not ticker:
        raise ValueError("ticker bos olamaz")

    raw = yf.download(
        ticker,
        start=start,
        end=end,
        interval=interval,
        auto_adjust=True,
        progress=False,
        multi_level_index=False,
    )

    if raw is None or raw.empty:
        return pd.DataFrame(columns=OHLCV_COLUMNS)

    df = raw[OHLCV_COLUMNS].copy()
    df.index.name = "Date"
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    return df


def fetch_universe(
    tickers: list[str],
    start: str,
    end: str | None = None,
    interval: str = "1d",
) -> dict[str, pd.DataFrame]:
    """Birden fazla sembol icin fetch_ohlcv'i sirayla cagirir.

    Args:
        tickers: yfinance sembol listesi.
        start: Baslangic tarihi, "YYYY-MM-DD".
        end: Bitis tarihi, "YYYY-MM-DD" veya None.
        interval: yfinance interval kodu.

    Returns:
        {ticker: OHLCV DataFrame} seklinde bir sozluk. Veri cekilemeyen
        semboller icin bos DataFrame degeri atanir (islem durmaz).
    """
    result: dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        try:
            result[ticker] = fetch_ohlcv(ticker, start=start, end=end, interval=interval)
        except Exception:
            result[ticker] = pd.DataFrame(columns=OHLCV_COLUMNS)
    return result
