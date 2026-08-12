"""research/opportunity_score.py - Donchian kirilimlarinin SUREKLI kalite
metrikleri ("En Iyi N Firsat" ozelligi icin, bkz. paper_trading/opportunities.py).

DURUSTLUK KISITLARI (kullanicinin arastirma talebine dogrudan cevap - bkz.
ilgili konusma):

1. signals/donchian.py'ye HIC DOKUNULMAZ. Donchian'in dogrulanmis kirilim-
   onay mekanizmasi (t=5.43, LONG-only) kullanicinin acik talimatiyla asla
   degistirilmez. Bu modul SADECE OKUR (ayni df/kanal/ATR hesaplarini
   TEKRAR - ama BAGIMSIZ - kullanir), hicbir sinyal/pozisyon uretmez.

2. Burada uretilen metrikler, signals/donchian.py::compute_breakout_filters
   icindeki AYNI body/volume esiklerinin (body_mult, volume_mult) SUREKLI
   (ikili degil, orantisal) versiyonudur - YENI/dogrulanmamis bir faktor
   DEGIL, zaten Colab'da dogrulanmis Kart 4 parametrelerinin ic gorunumu.

3. research/ensemble.py::composite_score KASITLI OLARAK kullanilmaz: IC-
   agirikli kompozit skor, factor_history.parquet'in HENUZ yeterli
   birikime sahip olmadigi bir veri talep eder (bkz. M6 erteleme
   gerekcesi) - burada kullanmak sahte kesinlik/otorite yaratirdi.

4. gozcu/'nun "dikkat skoru" BURAYA KARISTIRILMAZ: o skor gunluk anormal
   FIYAT HAREKETINI olcer (hic geriye donuk dogrulanmamis, gozcu kendi
   belgelerinde "YATIRIM TAVSIYESI DEGILDIR" der) - Donchian'in dogrulanmis
   kirilim edge'iyle ayni siralamada BIRLESTIRILMESI, dogrulanmamis bir
   sezgiyi dogrulanmis bir sinyalin itibarina ortak eder. Cagiran kod
   (dashboard) gozcu skorunu ISTERSE AYRI, acikca etiketlenmis bir bilgi
   olarak gosterebilir - bu modul onu HESAPLAMAZ/DONDURMEZ bile.

Uc ham bilesen (atr_distance, volume_ratio, body_ratio) KASITLI OLARAK
TEK bir opak sayiya (agirlikli toplam) SIKISTIRILMAZ - siralama SADECE
atr_distance (kirilimin ATR-normalize mesafesi - en dogrudan "ne kadar
guclu kirildi" olcusu) ile yapilir, digger ikisi cagiran kod tarafindan
AYRI gosterilsin diye dondurulur (kullanici NEDEN yuksek siraladigini
gorebilsin - tek bir "skor" kutusuna guvenmek yerine).
"""

from __future__ import annotations

import pandas as pd

from backtest.engine import compute_atr
from config import (
    DONCHIAN_ATR_PERIOD,
    DONCHIAN_BODY_LOOKBACK,
    DONCHIAN_ENTRY_N,
    DONCHIAN_VOLUME_LOOKBACK,
)
from signals.donchian import compute_donchian_channels


def compute_donchian_breakout_quality(
    df: pd.DataFrame,
    direction: int,
    entry_n: int = DONCHIAN_ENTRY_N,
    atr_period: int = DONCHIAN_ATR_PERIOD,
    body_lookback: int = DONCHIAN_BODY_LOOKBACK,
    volume_lookback: int = DONCHIAN_VOLUME_LOOKBACK,
) -> dict[str, float] | None:
    """Bugunku barin Donchian kirilimini, kanalin NE KADAR OTESINDE
    kapandigini (ATR birimiyle) + hacim/govde oranlarini hesaplar.

    Args:
        df: signals.donchian.generate_signals ile AYNI OHLCV DataFrame'i
            (bkz. paper_trading.runner.EntryCandidate.df).
        direction: +1 (long kirilim, ust kanal) veya -1 (short kirilim, alt kanal).
        entry_n, atr_period, body_lookback, volume_lookback: signals/donchian.py
            ve backtest/engine.py ile AYNI varsayilanlar (config.py) - farkli
            bir parametre seti test etmek icin degistirilebilir.

    Returns:
        {"atr_distance", "volume_ratio", "body_ratio"} - herhangi biri
        hesaplanamazsa (yetersiz veri, ATR<=0, ortalama hacim/govde 0) o
        anahtar None degeriyle doner. ATR hic hesaplanamiyorsa (tum
        metrikler normalize edilemez oldugundan) dogrudan None doner.
    """
    if len(df) < max(entry_n, atr_period, volume_lookback) + 1:
        return None

    atr_series = compute_atr(df, period=atr_period)
    current_atr = atr_series.iloc[-1]
    if pd.isna(current_atr) or current_atr <= 0:
        return None

    channels = compute_donchian_channels(df, entry_n=entry_n)
    last = df.iloc[-1]
    last_close = float(last["Close"])

    if direction == 1:
        threshold = channels["entry_upper"].iloc[-1]
        atr_distance = (last_close - threshold) / current_atr if pd.notna(threshold) else None
    else:
        threshold = channels["entry_lower"].iloc[-1]
        atr_distance = (threshold - last_close) / current_atr if pd.notna(threshold) else None

    avg_volume = df["Volume"].shift(1).rolling(volume_lookback).mean().iloc[-1]
    volume_ratio = float(last["Volume"] / avg_volume) if pd.notna(avg_volume) and avg_volume > 0 else None

    body = abs(float(last["Close"]) - float(last["Open"]))
    avg_body = (df["Close"] - df["Open"]).abs().shift(1).rolling(body_lookback).mean().iloc[-1]
    body_ratio = float(body / avg_body) if pd.notna(avg_body) and avg_body > 0 else None

    return {
        "atr_distance": float(atr_distance) if atr_distance is not None and pd.notna(atr_distance) else None,
        "volume_ratio": volume_ratio,
        "body_ratio": body_ratio,
    }
