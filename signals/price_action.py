"""Kart 5 - Price Action Breakout + Hacim Onayi sinyal mantigi.

Kaynak: faz2_strateji_kartlari.md (Kart 5) ve
faz3.5_matematiksel_formalizasyon.md SS3.

Formal tanim (SS3, long; short simetrik):
    b_t = 1[C_t > max(H_{t-n},...,H_{t-1})]
        * 1[|C_t - O_t| >= beta * mean(|C-O|)_{5 onceki bar}]
        * 1[V_t >= gamma * mean(V)_{20 onceki bar}]

Kapsam notu: Kart 5, Model A (pullback girisi) ve Model B (dogrudan
kirilim girisi) olmak uzere iki giris modeli tanimliyor. Model A, onceden
tanimli yapisal seviyelerin (ucgen, destek/direnc, swing high/low) otomatik
tespitini gerektirir ve formalizasyon dokumaninda kodlanabilir kapali
formda verilmemistir. Bu ilk surumde SADECE Model B (formal SS3
tanimindaki, hacim + govde onayli dogrudan kirilim) uygulanmistir; Model A
sonraki bir iterasyonda eklenebilir (bkz. README "Kapsam disi" bolumu).

Cikis, Donchian'dan farkli olarak trailing DEGIL, sabit R/R'dir (SS3):
    stop_t   = kirilim barinin en dusuk noktasi (long) / en yuksek
               noktasi (short)
    target_t = C_t + RR * (C_t - stop_t)          (long)
             = C_t - RR * (stop_t - C_t)           (short)
"""

from __future__ import annotations

import pandas as pd

from config import (
    PA_BODY_LOOKBACK,
    PA_BODY_MULT,
    PA_BREAKOUT_N,
    PA_RISK_REWARD,
    PA_VOLUME_LOOKBACK,
    PA_VOLUME_MULT,
)

REQUIRED_COLUMNS: list[str] = ["Open", "High", "Low", "Close", "Volume"]


def compute_breakout_levels(df: pd.DataFrame, breakout_n: int = PA_BREAKOUT_N) -> pd.DataFrame:
    """n-barlik onceki yuksek/dusuk kirilim seviyelerini hesaplar (lookahead-free).

    Args:
        df: ["High","Low"] kolonlarini iceren, kronolojik sirali DataFrame.
        breakout_n: Kirilim seviyesi icin lookback periyodu.

    Returns:
        ["breakout_upper", "breakout_lower"] kolonlarina sahip DataFrame.
    """
    out = pd.DataFrame(index=df.index)
    out["breakout_upper"] = df["High"].shift(1).rolling(breakout_n).max()
    out["breakout_lower"] = df["Low"].shift(1).rolling(breakout_n).min()
    return out


def compute_confirmation_filters(
    df: pd.DataFrame,
    body_mult: float = PA_BODY_MULT,
    body_lookback: int = PA_BODY_LOOKBACK,
    volume_mult: float = PA_VOLUME_MULT,
    volume_lookback: int = PA_VOLUME_LOOKBACK,
) -> pd.DataFrame:
    """Govde (beta) ve hacim (gamma) onay filtrelerini hesaplar.

    Args:
        df: ["Open","Close","Volume"] kolonlarini iceren DataFrame.
        body_mult: Govde carpani esigi (beta, varsayilan 2.0).
        body_lookback: Govde ortalamasi lookback'i (varsayilan 5).
        volume_mult: Hacim carpani esigi (gamma, varsayilan 1.5).
        volume_lookback: Hacim ortalamasi lookback'i (varsayilan 20).

    Returns:
        ["body_ok", "volume_ok"] boolean kolonlarina sahip DataFrame.
    """
    out = pd.DataFrame(index=df.index)

    body = (df["Close"] - df["Open"]).abs()
    avg_body = body.shift(1).rolling(body_lookback).mean()
    out["body_ok"] = (body >= body_mult * avg_body).fillna(False)

    avg_volume = df["Volume"].shift(1).rolling(volume_lookback).mean()
    out["volume_ok"] = (df["Volume"] >= volume_mult * avg_volume).fillna(False)

    return out


def generate_signals(
    df: pd.DataFrame,
    breakout_n: int = PA_BREAKOUT_N,
    body_mult: float = PA_BODY_MULT,
    body_lookback: int = PA_BODY_LOOKBACK,
    volume_mult: float = PA_VOLUME_MULT,
    volume_lookback: int = PA_VOLUME_LOOKBACK,
    risk_reward: float = PA_RISK_REWARD,
) -> pd.DataFrame:
    """Price Action Breakout (Model B) giris/stop/hedef seviyelerini uretir.

    Args:
        df: ["Open","High","Low","Close","Volume"] kolonlarini iceren,
            kronolojik sirali, DatetimeIndex'li DataFrame.
        breakout_n: Kirilim seviyesi lookback'i.
        body_mult: Govde filtresi carpani (beta).
        body_lookback: Govde ortalamasi lookback'i.
        volume_mult: Hacim filtresi carpani (gamma).
        volume_lookback: Hacim ortalamasi lookback'i.
        risk_reward: Sabit R/R cikis orani (varsayilan 2.0 -> 2:1).

    Returns:
        df ile ayni index'e sahip, su kolonlari iceren DataFrame:
        - "entry_long", "entry_short" (bool)
        - "stop_long", "stop_short" (float): giris barinin en dusuk/yuksek
          noktasi (yalnizca ilgili entry True oldugunda anlamlidir)
        - "target_long", "target_short" (float): sabit R/R hedefi

    Raises:
        ValueError: gerekli kolonlar df'te yoksa.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"df icinde eksik kolon(lar): {missing}")

    levels = compute_breakout_levels(df, breakout_n=breakout_n)
    filters = compute_confirmation_filters(
        df,
        body_mult=body_mult,
        body_lookback=body_lookback,
        volume_mult=volume_mult,
        volume_lookback=volume_lookback,
    )
    filters_ok = filters["body_ok"] & filters["volume_ok"]

    out = pd.DataFrame(index=df.index)
    out["entry_long"] = ((df["Close"] > levels["breakout_upper"]) & filters_ok).fillna(False)
    out["entry_short"] = ((df["Close"] < levels["breakout_lower"]) & filters_ok).fillna(False)

    out["stop_long"] = df["Low"]
    out["stop_short"] = df["High"]

    out["target_long"] = df["Close"] + risk_reward * (df["Close"] - out["stop_long"])
    out["target_short"] = df["Close"] - risk_reward * (out["stop_short"] - df["Close"])

    return out
