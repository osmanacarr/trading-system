"""NASDAQ kisa-vadeli ortalamaya-donus (RSI2/IBS) - DENEYSEL.

Kaynak: kaynak dosyalarinda (quant.md/quant2.md/quant3.md/trade*.md) bu
spesifik sinyal YOK - arastirmaci muhakemesiyle onerildi (bkz. config.py
"NASDAQ kisa-vadeli ortalamaya-donus" bolumu, tam gerekce ve backtest
sonuclari orada). Donchian (Kart 4) NASDAQ'ta IKI parametre setinde de
basarisiz oldu (t=-0.80, t=-0.62); bu modul FARKLI bir mekanizma dener
(cok kisa vadeli asiri-tepki, yavas trend kirilimi degil).

LONG-ONLY tasarim: SHORT sinyali KASITLI OLARAK uretilmez (entry_short
her zaman False) - yalnizca LONG taraf arastirildi/test edildi, simetrik
SHORT versiyonunu (asiri ALIMDA sat) dogrulamadan eklemek kor taklit olurdu.

Donchian/Price Action'dan mimari fark: cikis SABIT hedef/trailing DEGIL,
SINYAL-BAZLI (RSI(2) donus esigini gecince) VEYA ZAMAN-BAZLI (MAX_HOLD_DAYS
icinde donus olmazsa zorunlu kapanis) - bkz. backtest/engine.py::
run_mean_reversion_backtest (ma_voting'in sinyal-bazli cikis mantigina en
yakin, ama vote-buyuklugu YOK, zaman-asimi VAR).
"""

from __future__ import annotations

import pandas as pd

from backtest.engine import compute_atr
from config import (
    MEAN_REVERSION_ATR_PERIOD,
    MEAN_REVERSION_ATR_STOP_MULT,
    MEAN_REVERSION_IBS_THRESHOLD,
    MEAN_REVERSION_RSI_EXIT,
    MEAN_REVERSION_RSI_OVERSOLD,
    MEAN_REVERSION_RSI_PERIOD,
    MEAN_REVERSION_SMA_TREND_PERIOD,
)
from research.factors import compute_rsi

REQUIRED_COLUMNS: list[str] = ["Open", "High", "Low", "Close", "Volume"]


def compute_ibs(df: pd.DataFrame) -> pd.Series:
    """Internal Bar Strength: (Close-Low)/(High-Low). Dusuk deger -> kapanis
    gunun dip bolgesine yakin (zayif kapanis). High==Low barlarinda NaN
    (asagida entry mantiginda False'a duser)."""
    rng = df["High"] - df["Low"]
    return (df["Close"] - df["Low"]) / rng.replace(0.0, pd.NA)


def generate_signals(
    df: pd.DataFrame,
    rsi_period: int = MEAN_REVERSION_RSI_PERIOD,
    rsi_oversold: float = MEAN_REVERSION_RSI_OVERSOLD,
    rsi_exit: float = MEAN_REVERSION_RSI_EXIT,
    ibs_threshold: float = MEAN_REVERSION_IBS_THRESHOLD,
    sma_trend_period: int = MEAN_REVERSION_SMA_TREND_PERIOD,
    atr_period: int = MEAN_REVERSION_ATR_PERIOD,
    atr_stop_mult: float = MEAN_REVERSION_ATR_STOP_MULT,
) -> pd.DataFrame:
    """RSI2/IBS mean-reversion giris/cikis-sinyali/stop seviyelerini uretir.

    Args:
        df: ["Open","High","Low","Close","Volume"] kolonlarini iceren,
            kronolojik sirali, DatetimeIndex'li DataFrame.
        rsi_period, rsi_oversold, rsi_exit, ibs_threshold, sma_trend_period,
            atr_period, atr_stop_mult: bkz. config.py MEAN_REVERSION_*.

    Returns:
        df ile ayni index'e sahip, su kolonlari iceren DataFrame:
        - "entry_long" (bool): RSI(2)<oversold VE Close>SMA(trend) VE
          IBS<esik
        - "entry_short" (bool): HER ZAMAN False (LONG-only, bkz. modul docstring'i)
        - "stop_long" (float): Close - atr_stop_mult*ATR (yalnizca entry_long
          True oldugunda anlamlidir)
        - "exit_long_signal" (bool): RSI(2)>=rsi_exit (donus tamamlandi)

    Raises:
        ValueError: gerekli kolonlar df'te yoksa.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"df icinde eksik kolon(lar): {missing}")

    rsi = compute_rsi(df, period=rsi_period)
    sma_trend = df["Close"].rolling(sma_trend_period).mean()
    ibs = compute_ibs(df)
    atr = compute_atr(df, period=atr_period)

    out = pd.DataFrame(index=df.index)
    out["entry_long"] = (
        (rsi < rsi_oversold) & (df["Close"] > sma_trend) & (ibs < ibs_threshold)
    ).fillna(False)
    out["entry_short"] = False

    out["stop_long"] = df["Close"] - atr_stop_mult * atr
    out["exit_long_signal"] = (rsi >= rsi_exit).fillna(False)

    return out
