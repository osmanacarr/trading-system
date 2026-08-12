"""Istatistiksel anlamlilik araclari: t-istatistigi, walk-forward split,
Sharpe guven araligi.

Kaynak: faz3.5_matematiksel_formalizasyon.md SS4.

SS4.1 - Ortalama R'nin standart hatasi:
    SE(R_bar) = sigma_R / sqrt(n),  t = R_bar * sqrt(n) / sigma_R
    t > 2 ~ %95 guven esigi olarak kullanilir.

SS4.2 - Sharpe orani ve zaman ufku:
    Bir stratejinin getirisinin pozitif oldugundan istatistiksel olarak
    emin olabilmek icin gereken sure ~ 1 / Sharpe^2 yil.

SS4.3 - Walk-forward: Colab'da kullanilan tek sabit (anchored olmayan)
    kesimin yaninda, gercek "rolling walk-forward" (parametreleri train'de
    optimize edip bir sonraki periyoda kaydirarak test etme) burada
    saglanir.

Coklu-test duzeltmesi (Harvey & Liu 2014, quant2.md): sabit t>2.0 esigi tek
bir hipotez test edilirken makuldur, ama bir strateji/faktor HAVUZUNDA ne
kadar cok deneme yapilirsa sans eseri "anlamli" cikan sonuc bulma olasiligi
o kadar artar. bkz. multi_test_t_threshold / is_significant_multi_test.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from config import (
    CONFIDENCE_LEVEL,
    SIGNIFICANCE_MULTI_TEST_MID_MAX,
    SIGNIFICANCE_MULTI_TEST_SINGLE_MAX,
    SIGNIFICANCE_T_THRESHOLD,
    SIGNIFICANCE_T_THRESHOLD_MULTI_TEST,
    SIGNIFICANCE_T_THRESHOLD_MULTI_TEST_STRICT,
)


def standard_error_r(r_values: pd.Series | np.ndarray) -> float:
    """R-katlari orneklemi icin ortalamanin standart hatasini hesaplar.

    Args:
        r_values: Islem basina R-kati degerleri.

    Returns:
        SE(R_bar) = sigma_R / sqrt(n). n < 2 ise 0.0 doner.
    """
    values = np.asarray(r_values, dtype=float)
    values = values[~np.isnan(values)]
    n = len(values)
    if n < 2:
        return 0.0
    return float(np.std(values, ddof=1) / np.sqrt(n))


def t_statistic(r_values: pd.Series | np.ndarray) -> float:
    """Ortalama R'nin sifirdan farkli olup olmadigini test eden t-istatistigini hesaplar.

    Args:
        r_values: Islem basina R-kati degerleri.

    Returns:
        t = R_bar * sqrt(n) / sigma_R. n < 2 veya sigma_R == 0 ise 0.0 doner.
    """
    values = np.asarray(r_values, dtype=float)
    values = values[~np.isnan(values)]
    n = len(values)
    if n < 2:
        return 0.0
    se = standard_error_r(values)
    if se == 0:
        return 0.0
    return float(np.mean(values) / se)


def is_significant(
    r_values: pd.Series | np.ndarray,
    t_threshold: float = SIGNIFICANCE_T_THRESHOLD,
) -> bool:
    """t-istatistigi esigi asiyor mu diye kontrol eder (bkz. SS4.1).

    Args:
        r_values: Islem basina R-kati degerleri.
        t_threshold: Anlamlilik esigi (varsayilan 2.0, ~%95 guven).

    Returns:
        |t| >= t_threshold ise True.
    """
    return abs(t_statistic(r_values)) >= t_threshold


def multi_test_t_threshold(n_strategies_tested: int) -> float:
    """Havuzdaki toplam strateji/faktor sayisina gore kademeli t-esigi dondurur.

    Harvey & Liu (2014) coklu-test mantigi: n_strategies_tested, bu
    degerlendirmeye dahil olan ADAY dahil, ayni havuzda simdiye kadar
    (backtest/canli) test edilmis TOPLAM strateji/faktor sayisidir - sadece
    yeni eklenenler degil. Orn. Donchian+PriceAction zaten var (n=2) iken
    Kart 1 eklenirse n=3 ile degerlendirilir.

    Merdiven (config.py'de SIGNIFICANCE_MULTI_TEST_SINGLE_MAX/MID_MAX):
        n <= 2  -> 2.0 (SIGNIFICANCE_T_THRESHOLD, tek/ikili hipotez)
        n <= 6  -> 3.0 (SIGNIFICANCE_T_THRESHOLD_MULTI_TEST)
        n > 6   -> 3.5 (SIGNIFICANCE_T_THRESHOLD_MULTI_TEST_STRICT)

    Args:
        n_strategies_tested: Havuzdaki toplam strateji/faktor sayisi (>=1).

    Returns:
        Uygulanacak t-esigi.

    Raises:
        ValueError: n_strategies_tested < 1 ise.
    """
    if n_strategies_tested < 1:
        raise ValueError("n_strategies_tested >= 1 olmali")
    if n_strategies_tested <= SIGNIFICANCE_MULTI_TEST_SINGLE_MAX:
        return SIGNIFICANCE_T_THRESHOLD
    if n_strategies_tested <= SIGNIFICANCE_MULTI_TEST_MID_MAX:
        return SIGNIFICANCE_T_THRESHOLD_MULTI_TEST
    return SIGNIFICANCE_T_THRESHOLD_MULTI_TEST_STRICT


def is_significant_multi_test(
    r_values: pd.Series | np.ndarray,
    n_strategies_tested: int,
) -> bool:
    """is_significant'in coklu-test-farkinda versiyonu (bkz. multi_test_t_threshold).

    Args:
        r_values: Islem basina R-kati degerleri.
        n_strategies_tested: Havuzdaki toplam strateji/faktor sayisi (bu
            aday dahil) - bkz. multi_test_t_threshold.

    Returns:
        |t| >= multi_test_t_threshold(n_strategies_tested) ise True.
    """
    threshold = multi_test_t_threshold(n_strategies_tested)
    return abs(t_statistic(r_values)) >= threshold


def min_years_for_confidence(sharpe: float) -> float:
    """Sharpe oranindan, stratejinin pozitif oldugundan istatistiksel olarak
    emin olmak icin gereken yaklasik yil sayisini hesaplar (SS4.2: 1/Sharpe^2).

    Args:
        sharpe: Yillik-lastirilmis Sharpe orani.

    Returns:
        1 / sharpe**2. sharpe == 0 ise sonsuz (float('inf')) doner.
    """
    if sharpe == 0:
        return float("inf")
    return 1.0 / (sharpe**2)


def sharpe_standard_error(sharpe: float, n_periods: int) -> float:
    """Sharpe orani icin Lo (2002) yaklasik standart hatasini hesaplar.

    SE(Sharpe) ~= sqrt((1 + 0.5*Sharpe^2) / n)

    Args:
        sharpe: (Periyot bazinda veya yillik-lastirilmis, n ile tutarli
            olmak kaydiyla) Sharpe orani.
        n_periods: Gozlem sayisi (orn. gunluk getiri sayisi).

    Returns:
        Sharpe'in standart hatasi. n_periods < 2 ise 0.0 doner.
    """
    if n_periods < 2:
        return 0.0
    return float(np.sqrt((1 + 0.5 * sharpe**2) / n_periods))


def sharpe_confidence_interval(
    sharpe: float,
    n_periods: int,
    confidence: float = CONFIDENCE_LEVEL,
) -> tuple[float, float]:
    """Sharpe orani icin (asimptotik normal) guven araligini hesaplar.

    Args:
        sharpe: Sharpe orani.
        n_periods: Gozlem sayisi.
        confidence: Guven duzeyi (varsayilan 0.95).

    Returns:
        (alt_sinir, ust_sinir). n_periods < 2 ise (sharpe, sharpe) doner.
    """
    se = sharpe_standard_error(sharpe, n_periods)
    if se == 0:
        return (sharpe, sharpe)
    z = float(stats.norm.ppf(1 - (1 - confidence) / 2))
    return (sharpe - z * se, sharpe + z * se)


def single_split(df: pd.DataFrame, train_frac: float = 0.7) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Tek bir sabit (kronolojik) train/test kesimi uygular.

    Bu, faz3.5 dokumaninin SS4.3'te bahsettigi "tek bir sabit kesim"
    yaklasimidir (anchored/rolling degil).

    Args:
        df: Kronolojik sirali DataFrame.
        train_frac: Train'e ayrilacak oran (0,1) araliginda.

    Returns:
        (train_df, test_df).

    Raises:
        ValueError: train_frac (0,1) araligi disindaysa.
    """
    if not (0 < train_frac < 1):
        raise ValueError("train_frac (0,1) araliginda olmali")
    split_idx = int(len(df) * train_frac)
    return df.iloc[:split_idx].copy(), df.iloc[split_idx:].copy()


def rolling_walk_forward_splits(
    df: pd.DataFrame,
    n_splits: int = 5,
    min_train_frac: float = 0.5,
) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
    """Anchored (genisleyen pencereli) rolling walk-forward kesimleri uretir.

    Ilk train penceresi verinin ilk `min_train_frac`'ini kapsar; kalan veri
    `n_splits` esit parcaya bolunur ve her adimda train penceresi bir
    onceki test parcasini da icine alarak genisler (anchored walk-forward).
    Bu, SS4.3'te onerilen "parametreleri sadece train'de optimize edip her
    seferinde bir sonraki periyoda kaydirarak test etme" yaklasiminin temel
    iskeletidir; parametre optimizasyonunun kendisi bu fonksiyonun kapsami
    disindadir (cagiran kod, her (train, test) ciftinde kendi grid-search'unu
    calistirir).

    Args:
        df: Kronolojik sirali DataFrame.
        n_splits: Test icin ayrilacak parca sayisi.
        min_train_frac: Ilk train penceresinin minimum orani (0,1).

    Returns:
        Uzunlugu n_splits olan (train_df, test_df) ciftleri listesi.

    Raises:
        ValueError: n_splits < 1 ise, min_train_frac (0,1) araligi disindaysa
            veya df, anlamli bir kesim icin yetersiz uzunluktaysa.
    """
    if n_splits < 1:
        raise ValueError("n_splits >= 1 olmali")
    if not (0 < min_train_frac < 1):
        raise ValueError("min_train_frac (0,1) araliginda olmali")

    n = len(df)
    initial_train_end = int(n * min_train_frac)
    remaining = n - initial_train_end
    test_size = remaining // n_splits
    if initial_train_end < 1 or test_size < 1:
        raise ValueError("df, istenen n_splits/min_train_frac icin cok kisa")

    splits: list[tuple[pd.DataFrame, pd.DataFrame]] = []
    train_end = initial_train_end
    for i in range(n_splits):
        test_start = train_end
        test_end = test_start + test_size if i < n_splits - 1 else n
        train_df = df.iloc[:train_end].copy()
        test_df = df.iloc[test_start:test_end].copy()
        splits.append((train_df, test_df))
        train_end = test_end

    return splits
