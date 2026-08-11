"""Volatilite rejimi tespiti - Modul 4 (sistematik arastirma mimarisi).

Kaynak: quant.md/quant2.md ("regime switching" prensibi). Birebir alinti
(bu modulun tasarim kurali - kod yorumlarinda da korunmali):

    "I can easily hypothesize that markets go through volatility regimes...
    that's a reasonable hypothesis, a testable hypothesis. You can test for
    the existence of those volatility regimes, you can test for the
    behavior of the strategy in the different volatility regimes, and then
    you can have a strong theoretical basis for why you might have
    different parameters [per regime]." Kontrast: "[without a hypothesis]
    you simply say... I'm just going to test them all and choose the best
    one - well... we've almost certainly overfit our data."

BU MODUL PARAMETRE OTOMATIK DEGISTIRMEZ. Sadece: (1) ATR yuzdelik dilimine
gore dusuk/normal/yuksek rejim ETIKETLER, (2) MEVCUT bir stratejinin
rejimler arasinda expectancy/win-rate/profit-factor farki gosterip
gostermedigini RAPORLAR (backtest_by_regime). "Rejime gore farkli ATR
carpani daha iyi calisir mi" HIPOTEZINI test etmek icin gerekli VERIYI
saglar - hipotezi otomatik kabul edip parametreyi degistirmek bu modulun
KAPSAMI DISINDADIR (kor optimizasyon riski, yukaridaki alintiya gore).

ATR: backtest.engine.compute_atr yeniden kullanilir. Yuzdelik dilim
mantigi gozcu.metrics.atr_percentile ile AYNI tanimi kullanir (bugunku
ATR'nin trailing `lookback` pencerelik ATR dagilimindaki sirasi) ama
BURADA TAM ZAMAN SERISI olarak (vektorize, backtest_by_regime'in TUM
gecmis barlar icin rejim etiketine ihtiyaci oldugu icin) - gozcu'nun
kendisi degistirilmedi (bkz. research/factors.py'deki ayni gerekce).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtest.engine import compute_atr, run_backtest
from backtest.metrics import expectancy_r, mae_mfe_summary, median_r, profit_factor, win_rate
from config import (
    RESEARCH_REGIME_ATR_LOOKBACK,
    RESEARCH_REGIME_ATR_PERIOD,
    RESEARCH_REGIME_HIGH_PCT,
    RESEARCH_REGIME_LOW_PCT,
)

REGIME_LABELS: tuple[str, str, str] = ("low", "normal", "high")


def _rolling_percentile_rank(window: np.ndarray) -> float:
    today = window[-1]
    if np.isnan(today):
        return np.nan
    valid = window[~np.isnan(window)]
    if len(valid) < 2:
        return np.nan
    rank = (valid <= today).sum()
    return (rank / len(valid)) * 100.0


def compute_atr_percentile_series(
    df: pd.DataFrame,
    period: int = RESEARCH_REGIME_ATR_PERIOD,
    lookback: int = RESEARCH_REGIME_ATR_LOOKBACK,
) -> pd.Series:
    """Her bar icin, o barin ATR'sinin trailing `lookback` pencerelik ATR dagilimindaki yuzdelik dilimi (0-100).

    gozcu.metrics.atr_percentile'in (yalniz son bar icin skaler) TAM ZAMAN
    SERISI karsiligi - ayni tanim (bugunku ATR pencereye DAHIL edilir).
    """
    atr = compute_atr(df, period=period)
    return atr.rolling(lookback, min_periods=2).apply(_rolling_percentile_rank, raw=True)


def compute_regime_labels(
    df: pd.DataFrame,
    period: int = RESEARCH_REGIME_ATR_PERIOD,
    lookback: int = RESEARCH_REGIME_ATR_LOOKBACK,
    low_threshold: float = RESEARCH_REGIME_LOW_PCT,
    high_threshold: float = RESEARCH_REGIME_HIGH_PCT,
) -> pd.Series:
    """Her bar icin "low"/"normal"/"high" volatilite rejimi etiketi (yeterli veri yoksa None).

    Args:
        df: ["High","Low","Close"] kolonlarina sahip OHLCV DataFrame.
        period, lookback: compute_atr_percentile_series parametreleri.
        low_threshold: Bu yuzdelik dilimin ALTI -> "low".
        high_threshold: Bu yuzdelik dilimin USTU -> "high"; arasi -> "normal".
    """
    percentile = compute_atr_percentile_series(df, period=period, lookback=lookback)

    def _label(p: float) -> str | None:
        if pd.isna(p):
            return None
        if p < low_threshold:
            return "low"
        if p > high_threshold:
            return "high"
        return "normal"

    return percentile.apply(_label)


def backtest_by_regime(
    df: pd.DataFrame,
    signals: pd.DataFrame,
    strategy: str,
    regime_labels: pd.Series,
    **backtest_kwargs,
) -> dict[str, dict]:
    """Stratejiyi BIR KEZ backtest eder, islemleri GIRIS barindaki rejime gore gruplayip ayri ayri ozetler.

    Parametre DEGISTIRMEZ - sadece "bu strateji farkli rejimlerde farkli mi
    calisiyor" HIPOTEZINI test etmek icin veri saglar (bkz. modul docstring'i).

    Args:
        df: Fiyat verisi (backtest.engine.run_backtest'e aktarilir).
        signals: Ilgili signals modulunun generate_signals ciktisi.
        strategy: "donchian" veya "price_action" (backtest.engine.run_backtest).
        regime_labels: compute_regime_labels ciktisi (df ile ayni index).
        **backtest_kwargs: run_backtest'e aktarilan ek parametreler.

    Returns:
        {rejim_adi: {"n_trades","win_rate","expectancy_r","median_r",
        "profit_factor","mae_mfe"}} - sadece EN AZ 1 islem iceren rejimler
        icin anahtar uretilir. Drawdown/Sharpe gibi sermaye-egrisi
        metrikleri KASITLI OLARAK burada YOK (rejime gore bolunmus bir
        sermaye egrisi anlamli degildir - bkz. modul docstring'i, sadece
        islem-bazli metrikler raporlanir).
    """
    trades, _equity_curve = run_backtest(df, signals, strategy=strategy, **backtest_kwargs)
    if trades.empty:
        return {}

    trades = trades.copy()
    trades["regime"] = trades["entry_date"].map(regime_labels)

    result: dict[str, dict] = {}
    for regime_name, group in trades.groupby("regime"):
        if regime_name is None or pd.isna(regime_name):
            continue
        result[regime_name] = {
            "n_trades": int(len(group)),
            "win_rate": win_rate(group),
            "expectancy_r": expectancy_r(group),
            "median_r": median_r(group),
            "profit_factor": profit_factor(group),
            "mae_mfe": mae_mfe_summary(group),
        }
    return result
