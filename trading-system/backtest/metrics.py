"""Backtest performans metrikleri: win rate, expectancy_R, medyan R,
maksimum drawdown, Sharpe orani.

Kaynak: faz3.5_matematiksel_formalizasyon.md SS4 (R-katlari, Sharpe).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def win_rate(trades: pd.DataFrame) -> float:
    """Kazanan islem oranini hesaplar (W).

    Args:
        trades: En az "pnl" kolonunu iceren islem DataFrame'i.

    Returns:
        [0,1] araliginda kazanma orani. Islem yoksa 0.0 doner.
    """
    if trades.empty:
        return 0.0
    return float((trades["pnl"] > 0).mean())


def expectancy_r(trades: pd.DataFrame) -> float:
    """Ortalama R-katini (expectancy_R = mean(R)) hesaplar.

    Args:
        trades: "r_multiple" kolonunu iceren islem DataFrame'i.

    Returns:
        Ortalama R degeri. Islem yoksa 0.0 doner.
    """
    if trades.empty:
        return 0.0
    return float(trades["r_multiple"].mean())


def median_r(trades: pd.DataFrame) -> float:
    """R-katlarinin medyanini hesaplar (trend-takip dagilimlarinda sag
    carpiklik nedeniyle mean'den farkli ve bilgilendirici olabilir).

    Args:
        trades: "r_multiple" kolonunu iceren islem DataFrame'i.

    Returns:
        Medyan R degeri. Islem yoksa 0.0 doner.
    """
    if trades.empty:
        return 0.0
    return float(trades["r_multiple"].median())


def max_drawdown(equity_curve: pd.Series) -> float:
    """Sermaye egrisi uzerinden maksimum drawdown'i (negatif oran) hesaplar.

    Args:
        equity_curve: Kronolojik sirali, gunluk mark-to-market sermaye
            Series'i.

    Returns:
        Maksimum drawdown, 0.0 (drawdown yok) ile -1.0 (tam kayip) arasi bir
        deger (negatif isaretli, orn. -0.23 = %23 dususu). Bos/tek elemanli
        seride 0.0 doner.
    """
    if equity_curve.empty:
        return 0.0
    clean = equity_curve.dropna()
    if clean.empty:
        return 0.0
    running_max = clean.cummax()
    drawdown = (clean - running_max) / running_max
    return float(drawdown.min())


def sharpe_ratio(
    equity_curve: pd.Series,
    periods_per_year: int = 252,
    risk_free_rate: float = 0.0,
) -> float:
    """Gunluk sermaye getirilerinden yillik-lastirilmis Sharpe oranini hesaplar.

    Args:
        equity_curve: Kronolojik sirali, gunluk mark-to-market sermaye
            Series'i.
        periods_per_year: Yillik-lastirme icin periyot sayisi (gunluk veri
            icin 252).
        risk_free_rate: Periyot basina risksiz getiri (varsayilan 0).

    Returns:
        Yillik-lastirilmis Sharpe orani. Getiri std'si 0 veya veri
        yetersizse 0.0 doner.
    """
    clean = equity_curve.dropna()
    if len(clean) < 2:
        return 0.0
    returns = clean.pct_change().dropna()
    excess = returns - risk_free_rate
    std = excess.std()
    if std == 0 or np.isnan(std):
        return 0.0
    return float(excess.mean() / std * np.sqrt(periods_per_year))


def summarize(trades: pd.DataFrame, equity_curve: pd.Series) -> dict[str, float]:
    """Tum temel metrikleri tek bir sozlukte toplar.

    Args:
        trades: run_*_backtest ciktisi islem DataFrame'i.
        equity_curve: run_*_backtest ciktisi sermaye Series'i.

    Returns:
        {"n_trades", "win_rate", "expectancy_r", "median_r",
        "max_drawdown", "sharpe"} anahtarlarina sahip sozluk.
    """
    return {
        "n_trades": int(len(trades)),
        "win_rate": win_rate(trades),
        "expectancy_r": expectancy_r(trades),
        "median_r": median_r(trades),
        "max_drawdown": max_drawdown(equity_curve),
        "sharpe": sharpe_ratio(equity_curve),
    }
