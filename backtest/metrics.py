"""Backtest performans metrikleri: win rate, expectancy_R, medyan R,
maksimum drawdown, Sharpe orani, profit factor, win/loss orani, MAE/MFE
ozeti.

Kaynak: faz3.5_matematiksel_formalizasyon.md SS4 (R-katlari, Sharpe) ve
quant.md/quant2.md (Modul 8 - tam islem istatistik paketi):
    - profit factor: "anything between 1.2 and 2.6 in our opinion is
      good... profit factors of 20 and higher... those are over-optimized."
      (SERT bir kural degil, bkz. PROFIT_FACTOR_OVERFIT_WARNING_THRESHOLD).
    - "aggregate statistics... can be very dangerous [with] not enough
      trades... for validity" -> summarize() dusuk islem sayisinda
      low_sample_warning bayragi dondurur (kaynakta net "<30" rakami
      YOK, MIN_TRADES_FOR_RELIABLE_STATS sezgisel bir esiktir).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import MIN_TRADES_FOR_RELIABLE_STATS, PROFIT_FACTOR_OVERFIT_WARNING_THRESHOLD


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


def profit_factor(trades: pd.DataFrame) -> float:
    """Profit factor'u hesaplar: brut kazanc / brut kayip (mutlak deger).

    Args:
        trades: "pnl" kolonunu iceren islem DataFrame'i.

    Returns:
        Brut kazanc/brut kayip orani. Islem yoksa 0.0; kayip YOKSA (ve
        kazanc varsa) float('inf'); ne kazanc ne kayip varsa 0.0 doner.
    """
    if trades.empty:
        return 0.0
    gross_profit = float(trades.loc[trades["pnl"] > 0, "pnl"].sum())
    gross_loss = float(-trades.loc[trades["pnl"] < 0, "pnl"].sum())
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def win_loss_ratio(trades: pd.DataFrame) -> float:
    """Ortalama kazanan islem / ortalama kaybeden islem (mutlak deger) oranini hesaplar.

    Args:
        trades: "pnl" kolonunu iceren islem DataFrame'i.

    Returns:
        Islem yoksa ya da kazanan islem yoksa 0.0; kaybeden islem YOKSA
        (ve kazanan varsa) float('inf') doner.
    """
    if trades.empty:
        return 0.0
    wins = trades.loc[trades["pnl"] > 0, "pnl"]
    losses = trades.loc[trades["pnl"] < 0, "pnl"]
    if wins.empty:
        return 0.0
    if losses.empty:
        return float("inf")
    return float(wins.mean() / abs(losses.mean()))


def mae_mfe_summary(trades: pd.DataFrame) -> dict[str, float]:
    """MAE/MFE dagilim ozetini hesaplar (quant2.md - blotter MAE analizi).

    Args:
        trades: "mae_r", "mfe_r", "r_multiple" kolonlarini iceren islem
            DataFrame'i (bkz. backtest/engine.py::close_position).

    Returns:
        {"mean_mae_r", "mean_mfe_r", "median_mae_r", "median_mfe_r",
        "pct_closed_near_mfe"} - son alan, kapanis R'sinin kendi MFE'sinin
        en az %90'ina ulastigi islemlerin orani ("kazanci geri vermeden
        kapanan" islemler, kaynaktaki "closed on their highs" fikrinin
        nicel karsiligi).
    """
    if trades.empty or "mae_r" not in trades.columns or "mfe_r" not in trades.columns:
        return {
            "mean_mae_r": 0.0,
            "mean_mfe_r": 0.0,
            "median_mae_r": 0.0,
            "median_mfe_r": 0.0,
            "pct_closed_near_mfe": 0.0,
        }
    mae, mfe, r = trades["mae_r"], trades["mfe_r"], trades["r_multiple"]
    near_mfe = (mfe > 0) & (r >= 0.9 * mfe)
    return {
        "mean_mae_r": float(mae.mean()),
        "mean_mfe_r": float(mfe.mean()),
        "median_mae_r": float(mae.median()),
        "median_mfe_r": float(mfe.median()),
        "pct_closed_near_mfe": float(near_mfe.mean()),
    }


def summarize(trades: pd.DataFrame, equity_curve: pd.Series) -> dict:
    """Tum temel metrikleri tek bir sozlukte toplar.

    Args:
        trades: run_*_backtest ciktisi islem DataFrame'i.
        equity_curve: run_*_backtest ciktisi sermaye Series'i.

    Returns:
        {"n_trades", "win_rate", "expectancy_r", "median_r", "max_drawdown",
        "sharpe", "profit_factor", "win_loss_ratio", "mae_mfe",
        "low_sample_warning", "overfit_profit_factor_warning"} anahtarlarina
        sahip sozluk. low_sample_warning: n_trades < config.
        MIN_TRADES_FOR_RELIABLE_STATS ise True (agregat istatistiklerin
        yaniltici olabilecegi uyarisi - quant2.md). overfit_profit_factor_warning:
        profit_factor, config.PROFIT_FACTOR_OVERFIT_WARNING_THRESHOLD'i
        asarsa True (asiri-optimize edilmis olabilecegi sezgisel uyarisi).
    """
    n_trades = len(trades)
    pf = profit_factor(trades)
    return {
        "n_trades": int(n_trades),
        "win_rate": win_rate(trades),
        "expectancy_r": expectancy_r(trades),
        "median_r": median_r(trades),
        "max_drawdown": max_drawdown(equity_curve),
        "sharpe": sharpe_ratio(equity_curve),
        "profit_factor": pf,
        "win_loss_ratio": win_loss_ratio(trades),
        "mae_mfe": mae_mfe_summary(trades),
        "low_sample_warning": n_trades < MIN_TRADES_FOR_RELIABLE_STATS,
        "overfit_profit_factor_warning": np.isfinite(pf) and pf > PROFIT_FACTOR_OVERFIT_WARNING_THRESHOLD,
    }
