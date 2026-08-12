"""Kart 1 - Coklu Zaman Dilimi MA Crossover (Oylama Sistemi) sinyal mantigi.

Kaynak: faz2_strateji_kartlari.md (Kart 1). Kaynaklarda bu strateji
"matematiksel olarak gerekceli" (agirlikli gecikme toplami formunda bir
zaman serisi tahmincisiyle ayni) olarak isaretleniyor - teknik analiz
yorumundan bagimsiz, kantitatif bir temeli var (bkz. faz3.5 SS1).

Oylama: MA_VOTING_PAIRS'teki her (hizli, yavas) MA cifti icin:
    hizli_MA > yavas_MA  -> +1 oy ("boga")
    hizli_MA < yavas_MA  -> -1 oy ("ayi")
    esit/NaN (isinma donemi) -> 0 oy
net_vote = oylarin toplami, [-len(pairs), +len(pairs)] araliginda (varsayilan
3 cift ile [-3,+3]).

Kart 1 metni yalnizca boga (long) tarafini tanimliyor ("toplam oy 0,1,2,3");
bu modul, Donchian/Price Action ile TUTARLI olmasi icin SIMETRIK long/short
uyguluyor (ayi oylari icin ayna mantik).

Giris: net_vote onceki bara gore ARTTIYSA VE net_vote > 0 ise long (yeni
"boga" crossover'i); net_vote AZALDIYSA VE net_vote < 0 ise short. Pozisyon
zaten acikken (ayni yonde) net_vote'un daha da artmasi/azalmasi da "giris"
olarak isaretlenir - paper_trading/backtest katmani zaten acik pozisyon
varken yeni giris sinyalini yok sayar (bkz. paper_trading/runner.py).

Cikis (sinyal - stop'tan BAGIMSIZ, cagiran kod stop'u AYRICA kontrol eder):
net_vote 0'a/karsi isarete DONDUGUNDE (tum MA'lar sifirlanir/ters doner).

Stop-loss: ATR(14)x2 (bkz. config.py MA_VOTING_ATR_STOP_MULT yorumu - Kart 1
metni "son 20 barin ekstremumu / ATR(14)x2" arasinda net ayrim yapmiyor, bu
modul Kart 4 ile tutarli olani secer).

Pozisyon buyuklugu: Kart 1 "3 oy = tam pozisyon, 1 oy = 1/3 pozisyon" diyor -
bu modul bunu dogrudan UYGULAMAZ (pozisyon buyuklugu backtest/paper_trading
katmaninin sorumlulugu, bkz. signals/donchian.py ile ayni ayrim), bunun
yerine "vote_count" kolonunu dondurur; cagiran kod
abs(vote_count)/len(pairs) oranini bir buyukluk carpani olarak kullanabilir.
"""

from __future__ import annotations

import pandas as pd

from backtest.engine import compute_atr
from config import MA_VOTING_ATR_PERIOD, MA_VOTING_ATR_STOP_MULT, MA_VOTING_PAIRS

REQUIRED_COLUMNS: list[str] = ["Open", "High", "Low", "Close", "Volume"]


def compute_vote_series(df: pd.DataFrame, pairs: list[tuple[int, int]] = MA_VOTING_PAIRS) -> pd.Series:
    """Her (hizli, yavas) MA cifti icin +1/-1 oyunu toplayip net_vote serisini dondurur.

    Args:
        df: "Close" kolonunu iceren, kronolojik sirali DataFrame.
        pairs: (hizli_periyot, yavas_periyot) ciftleri listesi.

    Returns:
        df ile ayni index'e sahip, [-len(pairs), +len(pairs)] araliginda
        tamsayi degerli bir Series. Isinma doneminde (MA'lardan biri NaN)
        o cift 0 oy verir (ne +1 ne -1).
    """
    votes = pd.Series(0, index=df.index, dtype=int)
    for fast_period, slow_period in pairs:
        fast_ma = df["Close"].rolling(fast_period).mean()
        slow_ma = df["Close"].rolling(slow_period).mean()
        votes = votes + (fast_ma > slow_ma).astype(int) - (fast_ma < slow_ma).astype(int)
    return votes


def generate_signals(
    df: pd.DataFrame,
    pairs: list[tuple[int, int]] = MA_VOTING_PAIRS,
    atr_period: int = MA_VOTING_ATR_PERIOD,
    atr_stop_mult: float = MA_VOTING_ATR_STOP_MULT,
) -> pd.DataFrame:
    """MA-oylama giris/cikis-sinyali/stop seviyelerini uretir.

    Args:
        df: ["Open","High","Low","Close","Volume"] kolonlarini iceren,
            kronolojik sirali, DatetimeIndex'li DataFrame.
        pairs: (hizli, yavas) MA cift listesi.
        atr_period: Stop icin ATR periyodu.
        atr_stop_mult: Stop mesafesi carpani (k).

    Returns:
        df ile ayni index'e sahip, su kolonlari iceren DataFrame:
        - "vote_count" (int): net oy sayisi.
        - "entry_long", "entry_short" (bool).
        - "exit_long_signal", "exit_short_signal" (bool): sirasiyla acik
          bir long/short pozisyonun sinyal-bazli (stop'tan bagimsiz) kapanma
          kosulu (net_vote <= 0 / >= 0).
        - "stop_long", "stop_short" (float): ATR(atr_period)*atr_stop_mult
          mesafeli stop seviyesi (yalnizca ilgili entry True oldugunda
          anlamlidir).

    Raises:
        ValueError: gerekli kolonlar df'te yoksa.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"df icinde eksik kolon(lar): {missing}")

    votes = compute_vote_series(df, pairs=pairs)
    prev_votes = votes.shift(1)
    atr = compute_atr(df, period=atr_period)

    out = pd.DataFrame(index=df.index)
    out["vote_count"] = votes
    out["entry_long"] = ((votes > 0) & (votes > prev_votes)).fillna(False)
    out["entry_short"] = ((votes < 0) & (votes < prev_votes)).fillna(False)
    out["exit_long_signal"] = (votes <= 0).fillna(True)
    out["exit_short_signal"] = (votes >= 0).fillna(True)
    out["stop_long"] = df["Close"] - atr_stop_mult * atr
    out["stop_short"] = df["Close"] + atr_stop_mult * atr

    return out
