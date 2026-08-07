"""Anomali / fiyat sicramasi duzeltme.

BIST verilerinde yfinance'in auto_adjust'i her zaman tum kurumsal
aksiyonlari (bedelli/bedelsiz sermaye artirimi, temettu vb.) dogru
yakalamayabilir; bu da seride tek gunluk buyuk (%40+) yapay siramalara
yol acar. Bu modul, esik uzerindeki gunluk getirileri tespit edip
sicramadan ONCEKI tum barlari geriye donuk olarak (split-adjustment
mantigiyla) olcekleyerek seriyi surekli hale getirir.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

PRICE_COLUMNS: list[str] = ["Open", "High", "Low", "Close"]


def detect_jumps(df: pd.DataFrame, threshold: float = 0.40) -> pd.DatetimeIndex:
    """Gunluk kapanis getirisi mutlak degerce esigi asan barlarin tarihlerini bulur.

    Args:
        df: En az "Close" kolonunu iceren, DatetimeIndex'li DataFrame.
        threshold: Sicrama esigi (orn. 0.40 -> %40).

    Returns:
        Sicrama tespit edilen barlarin (t, yani sicramanin GERCEKLESTIGI
        bar) tarih indeksi, kronolojik sirada.
    """
    if df.empty:
        return pd.DatetimeIndex([])

    returns = df["Close"].pct_change()
    jump_mask = returns.abs() >= threshold
    return df.index[jump_mask.fillna(False)]


def adjust_jumps(df: pd.DataFrame, threshold: float = 0.40) -> pd.DataFrame:
    """Esik uzerindeki sicramalari geriye donuk olcekleyerek duzeltir.

    Her tespit edilen sicrama barinda (t), gozlenen oran
    ratio = Close[t] / Close[t-1] hesaplanir ve t'den ONCEKI tum barlar
    (Open, High, Low, Close) bu oranla carpilarak Close[t-1]_adjusted,
    Close[t]'ye yaklastirilir (sicrama kaldirilir, yuzde getiri surekliligi
    korunur). Sicramalar kronolojik sirada, eskiden yeniye isslenir; boylece
    birden fazla sicrama olan seriler de dogru kumulatif olarak duzeltilir.

    Volume kolonu olceklenmez (hisse adedi kurumsal aksiyonla gercekten
    degisebilir; fiyat serisinin sureklilik varsayimi Volume icin gecerli
    degildir).

    Args:
        df: ["Open","High","Low","Close"] kolonlarini iceren, DatetimeIndex'li
            ve kronolojik sirali DataFrame.
        threshold: Sicrama esigi (orn. 0.40 -> %40).

    Returns:
        Sicramalari duzeltilmis, orijinaliyle ayni index/kolonlara sahip
        yeni bir DataFrame (girdi degistirilmez).
    """
    if df.empty:
        return df.copy()

    adjusted = df.copy()
    jump_dates = detect_jumps(adjusted, threshold=threshold)

    for jump_date in jump_dates:
        pos = adjusted.index.get_loc(jump_date)
        if pos == 0:
            continue
        close_before = adjusted["Close"].iloc[pos - 1]
        close_at = adjusted["Close"].iloc[pos]
        if close_before == 0 or np.isnan(close_before) or np.isnan(close_at):
            continue
        ratio = close_at / close_before
        mask = np.arange(len(adjusted)) < pos
        adjusted.loc[mask, PRICE_COLUMNS] = adjusted.loc[mask, PRICE_COLUMNS] * ratio

    return adjusted
