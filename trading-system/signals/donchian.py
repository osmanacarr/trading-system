"""Kart 4 - Donchian Channel Breakout sinyal mantigi.

Kaynak: faz2_strateji_kartlari.md (Kart 4) ve
faz3.5_matematiksel_formalizasyon.md SS2.

Formal tanim (SS2.1):
    U_t = max(H_{t-n},...,H_{t-1}),  L_t = min(L_{t-n},...,L_{t-1})
    b_t = +1  eger C_t > U_t ve filtreler saglaniyorsa
          -1  eger C_t < L_t ve filtreler saglaniyorsa
          b_{t-1}  aksi halde (pozisyon korunur)

Cikis (trailing): L_exit_t = min(L_{t-m},...,L_{t-1}), m < n (n=20, m=10).
Kisa pozisyonlar icin simetrik olarak ust kanal (H_exit_t) kullanilir.

Bu modul yalnizca GIRIS/CIKIS SEVIYELERINI hesaplar; pozisyon durumu,
ilk ATR stop'u ve pozisyon buyuklugu backtest/engine.py'de yonetilir
(bkz. formalizasyon dokumani SS2.3 - pozisyon buyuklugu backtest/risk
katmaninin sorumlulugundadir).
"""

from __future__ import annotations

import pandas as pd

from config import (
    DONCHIAN_BODY_LOOKBACK,
    DONCHIAN_BODY_MULT,
    DONCHIAN_ENTRY_N,
    DONCHIAN_EXIT_N,
    DONCHIAN_VOLUME_LOOKBACK,
    DONCHIAN_VOLUME_MULT,
)

REQUIRED_COLUMNS: list[str] = ["Open", "High", "Low", "Close", "Volume"]


def compute_donchian_channels(
    df: pd.DataFrame,
    entry_n: int = DONCHIAN_ENTRY_N,
    exit_n: int = DONCHIAN_EXIT_N,
) -> pd.DataFrame:
    """Giris (n-gunluk) ve cikis (m-gunluk) Donchian kanallarini hesaplar.

    Lookahead-bias'i onlemek icin her kanal, MEVCUT bari HARIC tutarak
    (shift(1)) onceki n/m bara bakar; yani t barindaki kanal degeri,
    yalnizca t anindan ONCE bilinen bilgiyi kullanir.

    Args:
        df: ["High","Low"] kolonlarini iceren, kronolojik sirali DataFrame.
        entry_n: Giris kanali lookback periyodu (varsayilan 20).
        exit_n: Cikis (trailing) kanali lookback periyodu (varsayilan 10).

    Returns:
        Su kolonlari iceren yeni bir DataFrame (df ile ayni index):
        "entry_upper", "entry_lower", "exit_upper", "exit_lower".
    """
    out = pd.DataFrame(index=df.index)
    out["entry_upper"] = df["High"].shift(1).rolling(entry_n).max()
    out["entry_lower"] = df["Low"].shift(1).rolling(entry_n).min()
    out["exit_upper"] = df["High"].shift(1).rolling(exit_n).max()
    out["exit_lower"] = df["Low"].shift(1).rolling(exit_n).min()
    return out


def compute_breakout_filters(
    df: pd.DataFrame,
    body_mult: float = DONCHIAN_BODY_MULT,
    body_lookback: int = DONCHIAN_BODY_LOOKBACK,
    volume_mult: float = DONCHIAN_VOLUME_MULT,
    volume_lookback: int = DONCHIAN_VOLUME_LOOKBACK,
) -> pd.DataFrame:
    """Sahte kirilim filtrelerini hesaplar (Kart 4 "Not" bolumu).

    Filtre kosulu: kirilim mumunun govdesi, onceki `body_lookback` mumun
    ortalama govde buyuklugunun en az `body_mult` kati OLMALI VE hacim,
    onceki `volume_lookback` barin ortalama hacminin en az `volume_mult`
    kati OLMALI.

    Args:
        df: ["Open","Close","Volume"] kolonlarini iceren DataFrame.
        body_mult: Govde carpani esigi (varsayilan 1.5).
        body_lookback: Govde ortalamasi icin bakilacak onceki bar sayisi (5).
        volume_mult: Hacim carpani esigi (varsayilan 1.0).
        volume_lookback: Hacim ortalamasi icin bakilacak onceki bar sayisi (20).

    Returns:
        ["body_ok", "volume_ok"] boolean kolonlarina sahip DataFrame.
    """
    out = pd.DataFrame(index=df.index)

    body = (df["Close"] - df["Open"]).abs()
    avg_body = body.shift(1).rolling(body_lookback).mean()
    out["body_ok"] = body >= body_mult * avg_body

    avg_volume = df["Volume"].shift(1).rolling(volume_lookback).mean()
    out["volume_ok"] = df["Volume"] >= volume_mult * avg_volume

    out["body_ok"] = out["body_ok"].fillna(False)
    out["volume_ok"] = out["volume_ok"].fillna(False)
    return out


def generate_signals(
    df: pd.DataFrame,
    entry_n: int = DONCHIAN_ENTRY_N,
    exit_n: int = DONCHIAN_EXIT_N,
    body_mult: float = DONCHIAN_BODY_MULT,
    body_lookback: int = DONCHIAN_BODY_LOOKBACK,
    volume_mult: float = DONCHIAN_VOLUME_MULT,
    volume_lookback: int = DONCHIAN_VOLUME_LOOKBACK,
) -> pd.DataFrame:
    """Donchian Breakout giris tetikleyicilerini ve trailing cikis seviyelerini uretir.

    Args:
        df: ["Open","High","Low","Close","Volume"] kolonlarini iceren,
            kronolojik sirali, DatetimeIndex'li DataFrame.
        entry_n: Giris kanali periyodu.
        exit_n: Cikis (trailing) kanali periyodu.
        body_mult: Govde filtresi carpani.
        body_lookback: Govde ortalamasi lookback'i.
        volume_mult: Hacim filtresi carpani.
        volume_lookback: Hacim ortalamasi lookback'i.

    Returns:
        df ile ayni index'e sahip, su kolonlari iceren DataFrame:
        - "entry_long" (bool): bu barda yeni long giris sinyali var mi
        - "entry_short" (bool): bu barda yeni short giris sinyali var mi
        - "exit_long_level" (float): long pozisyon icin trailing cikis
          seviyesi (m-gunluk dusuk kanali)
        - "exit_short_level" (float): short pozisyon icin trailing cikis
          seviyesi (m-gunluk yuksek kanali)

    Raises:
        ValueError: gerekli kolonlar df'te yoksa.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"df icinde eksik kolon(lar): {missing}")

    channels = compute_donchian_channels(df, entry_n=entry_n, exit_n=exit_n)
    filters = compute_breakout_filters(
        df,
        body_mult=body_mult,
        body_lookback=body_lookback,
        volume_mult=volume_mult,
        volume_lookback=volume_lookback,
    )

    filters_ok = filters["body_ok"] & filters["volume_ok"]

    out = pd.DataFrame(index=df.index)
    out["entry_long"] = (df["Close"] > channels["entry_upper"]) & filters_ok
    out["entry_short"] = (df["Close"] < channels["entry_lower"]) & filters_ok
    out["exit_long_level"] = channels["exit_lower"]
    out["exit_short_level"] = channels["exit_upper"]

    out["entry_long"] = out["entry_long"].fillna(False)
    out["entry_short"] = out["entry_short"].fillna(False)
    return out
