"""BIST (TL) fiyatlarini USD'ye cevirmek icin USDTRY yardimcilari.

Amac: BIST ve BTC/USDT sonuclarini ayni para biriminde (USD) karsilastirmak
istendiginde kullanilir; Donchian/Price Action sinyal ve backtest mantigi
para biriminden bagimsizdir, bu modul yalnizca raporlama/karsilastirma
katmanindadir.
"""

from __future__ import annotations

import pandas as pd

from config import USDTRY_TICKER
from data.fetch import fetch_ohlcv

PRICE_COLUMNS: list[str] = ["Open", "High", "Low", "Close"]


def fetch_usdtry(start: str, end: str | None = None) -> pd.Series:
    """USDTRY kapanis serisini ceker.

    Args:
        start: Baslangic tarihi, "YYYY-MM-DD".
        end: Bitis tarihi, "YYYY-MM-DD" veya None.

    Returns:
        DatetimeIndex'li USDTRY kapanis fiyati Series'i (bos olabilir).
    """
    df = fetch_ohlcv(USDTRY_TICKER, start=start, end=end, interval="1d")
    if df.empty:
        return pd.Series(dtype=float, name="USDTRY")
    return df["Close"].rename("USDTRY")


def convert_to_usd(df_tl: pd.DataFrame, usdtry: pd.Series) -> pd.DataFrame:
    """TL cinsinden OHLC fiyatlari, hizalanmis USDTRY kuruyla USD'ye cevirir.

    USDTRY serisi df_tl'nin tarih indeksine ileri-doldurma (ffill) ile
    hizalanir (BIST ve FX takvimleri tam ortusmeyebilir).

    Args:
        df_tl: ["Open","High","Low","Close"] (ve opsiyonel "Volume")
            kolonlarina sahip, TL cinsinden DataFrame.
        usdtry: USDTRY kapanis fiyati Series'i (kac TL = 1 USD).

    Returns:
        Ayni index/kolonlara sahip, Open/High/Low/Close USD'ye cevrilmis
        yeni bir DataFrame. Volume (varsa) degistirilmeden kopyalanir.
        usdtry bos ise veya hicbir tarih hizalanamazsa girdi TL fiyatlariyla
        (donusum yapilmadan) doner.
    """
    if df_tl.empty or usdtry.empty:
        return df_tl.copy()

    rate = usdtry.reindex(df_tl.index, method="ffill")
    if rate.notna().sum() == 0:
        return df_tl.copy()

    result = df_tl.copy()
    for col in PRICE_COLUMNS:
        if col in result.columns:
            result[col] = result[col] / rate

    valid = rate.notna()
    result = result.loc[valid].copy()
    return result
