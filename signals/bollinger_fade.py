"""Kart 3 - Bollinger / Keltner Fade sinyal mantigi.

Kaynak: faz2_strateji_kartlari.md (Kart 3).

Ortalamaya-donus (mean-reversion) stratejisi - Donchian (Kart 4) ve
MA-oylamanin (Kart 1) TREND-TAKIP mantiginin TERSI: fiyat bandin disina
tastiginda ortalamaya DONECEGINI varsayar. Bu YUZDEN yalnizca ADX(14) <
esik (dusuk trend gucu / yatay piyasa) iken aktif olmali - Donchian/Kart-1
GUCLU trendde calisir, Kart 3 onlarin SESSIZ kaldigi rejimde devreye girer
(bkz. research/regime.py::compute_adx, M5'te eklendi - proje kokundeki
mimari genisletme planinin "rejime gore hero algoritma" ilkesinin somut
uygulamasi).

Iki bant turu (Kart 3 metni: "ikisi ayri ayri backtest edilip
karsilastirilacak"):
    - "bollinger": SMA(20) +- 2*std(20)
    - "keltner": EMA(20) +- 2*ATR(20) (Kart 3 metni net bir ATR katsayisi
      vermiyor - Kart 4/Kart 1 ile TUTARLI olmasi icin k=2 kullanilir)

Giris (long ornek - fade, ALT banda dokunus; short SIMETRIK, UST bant):
    1. Close <= alt_bant (banda dokunus/asimi)
    2. RSI(14) < 30 (asiri satim)
    3. "Mum onayi": Kart 3 metni Kart 2'nin aksine somut bir mum
       FORMASYONU tanimlamiyor. Bu modul, depodaki diger kartlarin
       (Donchian/Price Action) govde/hacim tarzi MEKANIK onaylarina
       tutarli kalmak icin "kapanis acilistan YUKSEK" (boga mumu) sartini
       kullanir; short icin simetrik "kapanis acilistan DUSUK". Adlandirilmis
       formasyon (engulfing/hammer vb.) tanima SPEKULATIF/OZNEL olurdu -
       price_action.py'nin Model A'yi (yapisal seviye tespiti gerektirir)
       KAPSAM DISI birakma gerekcesiyle AYNI ilke.
    4. ADX(14) < esik (research.regime.compute_adx)

Stop-loss: bandin DISINA ATRx0.5 (Kart 3 metni).
Take-profit: orta bant (SMA/EMA20 - bant turune gore, "orta bant").
"""

from __future__ import annotations

import pandas as pd

from backtest.engine import compute_atr
from config import (
    BOLLINGER_FADE_ATR_PERIOD,
    BOLLINGER_FADE_ATR_STOP_MULT,
    BOLLINGER_FADE_BAND_MULT,
    BOLLINGER_FADE_BAND_PERIOD,
    BOLLINGER_FADE_RSI_OVERBOUGHT,
    BOLLINGER_FADE_RSI_OVERSOLD,
    BOLLINGER_FADE_RSI_PERIOD,
    RESEARCH_REGIME_ADX_PERIOD,
    RESEARCH_REGIME_ADX_TREND_THRESHOLD,
)
from research.factors import compute_rsi
from research.regime import compute_adx

REQUIRED_COLUMNS: list[str] = ["Open", "High", "Low", "Close", "Volume"]
BAND_TYPES: tuple[str, str] = ("bollinger", "keltner")


def compute_bands(
    df: pd.DataFrame,
    band_type: str = "keltner",
    period: int = BOLLINGER_FADE_BAND_PERIOD,
    mult: float = BOLLINGER_FADE_BAND_MULT,
    atr_period: int = BOLLINGER_FADE_ATR_PERIOD,
) -> pd.DataFrame:
    """Bollinger VEYA Keltner bantlarini hesaplar.

    Args:
        df: ["High","Low","Close"] kolonlarini iceren, kronolojik sirali DataFrame.
        band_type: "bollinger" (SMA +- mult*std) veya "keltner" (EMA +- mult*ATR).
        period: Orta bant (SMA/EMA) periyodu.
        mult: Bant genisligi carpani (Bollinger: std carpani; Keltner: ATR carpani).
        atr_period: Yalniz "keltner" icin ATR periyodu.

    Returns:
        ["band_middle","band_upper","band_lower"] kolonlarina sahip DataFrame.

    Raises:
        ValueError: band_type BAND_TYPES disindaysa.
    """
    if band_type not in BAND_TYPES:
        raise ValueError(f"band_type {band_type!r} olmali (biri: {BAND_TYPES})")

    out = pd.DataFrame(index=df.index)
    if band_type == "bollinger":
        middle = df["Close"].rolling(period).mean()
        width = df["Close"].rolling(period).std() * mult
    else:
        middle = df["Close"].ewm(span=period, adjust=False, min_periods=period).mean()
        width = compute_atr(df, period=atr_period) * mult

    out["band_middle"] = middle
    out["band_upper"] = middle + width
    out["band_lower"] = middle - width
    return out


def generate_signals(
    df: pd.DataFrame,
    band_type: str = "keltner",
    band_period: int = BOLLINGER_FADE_BAND_PERIOD,
    band_mult: float = BOLLINGER_FADE_BAND_MULT,
    band_atr_period: int = BOLLINGER_FADE_ATR_PERIOD,
    stop_atr_period: int = BOLLINGER_FADE_ATR_PERIOD,
    stop_atr_mult: float = BOLLINGER_FADE_ATR_STOP_MULT,
    rsi_period: int = BOLLINGER_FADE_RSI_PERIOD,
    rsi_overbought: float = BOLLINGER_FADE_RSI_OVERBOUGHT,
    rsi_oversold: float = BOLLINGER_FADE_RSI_OVERSOLD,
    adx_period: int = RESEARCH_REGIME_ADX_PERIOD,
    adx_threshold: float = RESEARCH_REGIME_ADX_TREND_THRESHOLD,
) -> pd.DataFrame:
    """Bollinger/Keltner Fade giris/stop/hedef seviyelerini uretir.

    Args:
        df: ["Open","High","Low","Close","Volume"] kolonlarini iceren,
            kronolojik sirali, DatetimeIndex'li DataFrame.
        band_type: "bollinger" veya "keltner" (bkz. compute_bands).
        band_period, band_mult, band_atr_period: compute_bands parametreleri.
        stop_atr_period, stop_atr_mult: Stop mesafesi (bandin disina
            stop_atr_mult*ATR) icin ATR parametreleri.
        rsi_period, rsi_overbought, rsi_oversold: RSI asiri-alim/satim esikleri.
        adx_period, adx_threshold: ADX < adx_threshold iken sinyaller aktif.

    Returns:
        df ile ayni index'e sahip, su kolonlari iceren DataFrame:
        - "entry_long", "entry_short" (bool)
        - "stop_long", "stop_short" (float): bandin disina ATRx(stop_atr_mult)
        - "target_long", "target_short" (float): orta bant
        - "adx" (float): bilgi amacli, cagiran kod tarafindan da kullanilabilir

    Raises:
        ValueError: gerekli kolonlar df'te yoksa.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"df icinde eksik kolon(lar): {missing}")

    bands = compute_bands(df, band_type=band_type, period=band_period, mult=band_mult, atr_period=band_atr_period)
    rsi = compute_rsi(df, period=rsi_period)
    adx = compute_adx(df, period=adx_period)
    stop_distance = compute_atr(df, period=stop_atr_period) * stop_atr_mult

    range_regime = (adx < adx_threshold).fillna(False)
    bullish_candle = df["Close"] > df["Open"]
    bearish_candle = df["Close"] < df["Open"]

    touches_lower = df["Close"] <= bands["band_lower"]
    touches_upper = df["Close"] >= bands["band_upper"]
    oversold = rsi < rsi_oversold
    overbought = rsi > rsi_overbought

    out = pd.DataFrame(index=df.index)
    out["entry_long"] = (touches_lower & oversold & bullish_candle & range_regime).fillna(False)
    out["entry_short"] = (touches_upper & overbought & bearish_candle & range_regime).fillna(False)

    out["stop_long"] = bands["band_lower"] - stop_distance
    out["stop_short"] = bands["band_upper"] + stop_distance
    out["target_long"] = bands["band_middle"]
    out["target_short"] = bands["band_middle"]
    out["adx"] = adx

    return out
