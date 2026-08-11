"""gozcu/metrics.py - Sembol basina "dikkat" metrikleri.

Her fonksiyon tek bir metrigi hesaplar (tek dev fonksiyon degil - bkz. gorev
tanimi), sentetik veriyle test edilebilir ve mumkun oldugunca MEVCUT
fonksiyonlari yeniden kullanir:
- momentum_candle_flag -> signals.donchian.compute_breakout_filters
- atr_percentile       -> backtest.engine.compute_atr

RVOL notu: "son 20 gunun ayni saatteki ortalama hacmi" icin her sembol icin
20 gun geriye donuk gun-ici bar cekmek (yuzlerce sembolde) GOZCU'nun ~5
dakikalik tarama butcesini asar. Bunun yerine GUNLUK ortalama hacim, seans
icinde GECEN sure oranina gore olceklenir (elapsed_fraction) - ayni niyeti
(bugunku hacmin "normal" seyre kiyasla ne kadar one cikti) cok daha ucuz
bir sekilde yaklasiklar.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtest.engine import compute_atr
from config import GOZCU_ATR_PERIOD, GOZCU_VOLUME_ZSCORE_LOOKBACK, GOZCU_WEEKLY_LOOKBACK_TRADING_DAYS
from signals.donchian import compute_breakout_filters


def daily_change_pct(daily_df: pd.DataFrame) -> float | None:
    """Bugunku (son) kapanis/fiyat vs dunku kapanis, oran olarak (0.05 = %5).

    Args:
        daily_df: ["Close"] kolonunu iceren, kronolojik sirali gunluk DataFrame.

    Returns:
        Yeterli veri (>=2 bar) yoksa None.
    """
    close = daily_df["Close"].dropna()
    if len(close) < 2:
        return None
    prev, last = close.iloc[-2], close.iloc[-1]
    if prev == 0:
        return None
    return (last - prev) / prev


def weekly_change_pct(daily_df: pd.DataFrame, lookback: int = GOZCU_WEEKLY_LOOKBACK_TRADING_DAYS) -> float | None:
    """Son `lookback` islem gunu once vs bugunku kapanis, oran olarak."""
    close = daily_df["Close"].dropna()
    if len(close) < lookback + 1:
        return None
    prev, last = close.iloc[-(lookback + 1)], close.iloc[-1]
    if prev == 0:
        return None
    return (last - prev) / prev


def volume_zscore(daily_df: pd.DataFrame, lookback: int = GOZCU_VOLUME_ZSCORE_LOOKBACK) -> float | None:
    """Bugunku hacmin, ONCEKI `lookback` gunun hacim dagilimina gore Z-skoru.

    (today_volume - mean(prev_lookback)) / std(prev_lookback). Bugunku bar
    pencereye dahil edilmez (donchian filtrelerindeki shift(1) felsefesiyle
    tutarli - "normal" bugune gore degil, bugune KADAR bilinen gecmise gore
    tanimlanir).
    """
    volume = daily_df["Volume"].dropna()
    if len(volume) < lookback + 1:
        return None
    window = volume.iloc[-(lookback + 1):-1]
    today = volume.iloc[-1]
    std = window.std()
    if std == 0 or pd.isna(std):
        return None
    return (today - window.mean()) / std


def momentum_candle_flag(daily_df: pd.DataFrame) -> dict:
    """Son barin "momentum mumu" olup olmadigini, mevcut Donchian filtresiyle tespit eder.

    Yeni bir govde/hacim mantigi YAZMAZ - dogrudan
    signals.donchian.compute_breakout_filters()'i cagirir (Kart 4 "sahte
    kirilim filtresi" ile ayni tanim: govde >= body_mult * onceki ortalama
    govde VE hacim >= volume_mult * onceki ortalama hacim).

    Returns:
        {"body_ok": bool, "volume_ok": bool}. Yetersiz veri varsa ikisi de False.
    """
    if len(daily_df) < 2:
        return {"body_ok": False, "volume_ok": False}
    filters = compute_breakout_filters(daily_df)
    last = filters.iloc[-1]
    return {"body_ok": bool(last["body_ok"]), "volume_ok": bool(last["volume_ok"])}


def relative_volume(
    intraday_today_df: pd.DataFrame,
    avg_daily_volume: float | None,
    elapsed_fraction: float,
) -> float | None:
    """Bugunku kumulatif gun-ici hacmin, o ana kadar "normal" beklenen hacme orani (RVOL).

    Args:
        intraday_today_df: SADECE bugunku gun-ici barlari iceren ["Volume"]
            kolonlu DataFrame (caller filtreler).
        avg_daily_volume: Son N gunun ortalama GUNLUK hacmi (volume_zscore
            ile ayni pencereden hesaplanabilir).
        elapsed_fraction: Seansin ne kadarinin gectigi (0-1 arasi; orn. 0.25
            = seansin ilk ceyregi). gozcu/market_hours.py tarafindan hesaplanir.

    Returns:
        None: veri yoksa, avg_daily_volume <=0 ise veya elapsed_fraction<=0 ise.
    """
    if avg_daily_volume is None or avg_daily_volume <= 0:
        return None
    if elapsed_fraction <= 0:
        return None
    if intraday_today_df.empty:
        return None
    cumulative_volume = intraday_today_df["Volume"].dropna().sum()
    expected_so_far = avg_daily_volume * min(elapsed_fraction, 1.0)
    if expected_so_far <= 0:
        return None
    return cumulative_volume / expected_so_far


def compute_vwap(intraday_today_df: pd.DataFrame) -> pd.Series:
    """Bugunku gun-ici barlar icin kumulatif hacim-agirlikli ortalama fiyat (VWAP) serisi.

    Args:
        intraday_today_df: SADECE bugunku barlari iceren, kronolojik sirali
            ["High","Low","Close","Volume"] kolonlu DataFrame.

    Returns:
        df ile ayni index'e sahip VWAP Series'i (bos df icin bos Series).
    """
    if intraday_today_df.empty:
        return pd.Series(dtype=float)
    typical_price = (intraday_today_df["High"] + intraday_today_df["Low"] + intraday_today_df["Close"]) / 3.0
    cum_pv = (typical_price * intraday_today_df["Volume"]).cumsum()
    cum_volume = intraday_today_df["Volume"].cumsum().replace(0, np.nan)
    return cum_pv / cum_volume


def vwap_slope(vwap_series: pd.Series, lookback: int = 3) -> float | None:
    """Son `lookback` VWAP noktasi arasindaki ortalama bar-basina egim.

    Pozitif -> VWAP yukseliyor (alici baskisi artiyor), negatif -> dusuyor.
    """
    series = vwap_series.dropna()
    if len(series) < lookback + 1:
        return None
    window = series.iloc[-(lookback + 1):]
    return (window.iloc[-1] - window.iloc[0]) / lookback


def vwap_position_pct(current_price: float, vwap_value: float | None) -> float | None:
    """Guncel fiyatin VWAP'a gore konumu, oran olarak (pozitif = VWAP ustunde)."""
    if vwap_value is None or pd.isna(vwap_value) or vwap_value == 0:
        return None
    return (current_price - vwap_value) / vwap_value


def distance_from_52w_high(daily_df: pd.DataFrame, lookback: int = 252) -> float | None:
    """Guncel fiyatin, son `lookback` islem gunundeki en yuksek kapanisa uzakligi (negatif/0)."""
    close = daily_df["Close"].dropna()
    if close.empty:
        return None
    window = close.iloc[-lookback:]
    high = window.max()
    if high == 0:
        return None
    return (close.iloc[-1] - high) / high


def distance_from_52w_low(daily_df: pd.DataFrame, lookback: int = 252) -> float | None:
    """Guncel fiyatin, son `lookback` islem gunundeki en dusuk kapanisa uzakligi (pozitif/0)."""
    close = daily_df["Close"].dropna()
    if close.empty:
        return None
    window = close.iloc[-lookback:]
    low = window.min()
    if low == 0:
        return None
    return (close.iloc[-1] - low) / low


def atr_percentile(daily_df: pd.DataFrame, period: int = GOZCU_ATR_PERIOD, lookback: int = 252) -> float | None:
    """Bugunku ATR(period) degerinin, son `lookback` gunluk ATR dagilimindaki yuzdelik dilimi (0-100).

    ATR hesaplamasi icin backtest.engine.compute_atr() yeniden kullanilir
    (paper trading/backtest ile AYNI Wilder ATR formulu) - yeni bir ATR
    mantigi yazilmaz.
    """
    atr_series = compute_atr(daily_df, period=period).dropna()
    if atr_series.empty:
        return None
    window = atr_series.iloc[-lookback:]
    today_atr = window.iloc[-1]
    if len(window) < 2:
        return None
    rank = (window <= today_atr).sum()
    return (rank / len(window)) * 100.0
