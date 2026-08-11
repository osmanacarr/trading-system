"""IC (Information Coefficient) ve alpha decay takibi - Modul 3 (sistematik
arastirma mimarisi).

Kaynak: quant2.md (EPAT alpha-decay webinari + Quantopian risk-optimizasyon
dersi). Birebir alinti (IC tanimi):

    "the information coefficient is precisely just the correlation, and the
    specific correlation used is Spearman rank... between your model's
    predictions and the future returns."

IC, GUNLUK/TARIH BAZINDA (cross-sectional: o tarihte evrendeki TUM
sembollerin faktor degeri vs ileri getirisi arasindaki Spearman korelasyonu)
hesaplanir ve zaman serisi olarak izlenir - "you want the mean to be high
and the standard deviation low."

Alpha/publication decay (birebir, quant2.md): "alpha decay is basically
the difference between in-sample and out-of-sample performance... it
doesn't mean the strategy will stop working at all, it only means we can
expect less." Bu modulun decay tespiti (ilk yari vs ikinci yari IC
karsilastirmasi) bu ilkeyi izler: DEGRADASYON bir bayraktir, "stratejiyi
kapat" anlamina gelmez.

Rule burden guard (birebir, quant2.md): "much of the trading literature
suggests first adding your entries... then going back and adding exits...
then risk rules. This will absolutely create a backtest that has
increasing performance as you add more rules; however... you're really
inviting overfitting... strategies with fewer rules are more likely to be
robust out-of-sample." check_rule_burden() bunu SERT bir kisitlama olarak
DEGIL, bir uyari/bayrak olarak uygular.

Stil konvansiyonu: validation/significance.py ile TUTARLI - np.ndarray/
pd.Series girdi, NaN maskeleme, n<2 icin notr (0.0) donus, config.py'den
varsayilan esikler.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy import stats

from config import (
    MAX_FILTER_COUNT,
    RESEARCH_IC_HORIZON_DAYS,
    RESEARCH_MIN_IC_SAMPLE_SIZE,
)

log = logging.getLogger("validation.alpha_evaluation")


def compute_ic(
    factor_values: pd.Series | np.ndarray,
    forward_returns: pd.Series | np.ndarray,
) -> float:
    """Faktor degerleri ile ileri getiriler arasindaki Spearman rank korelasyonunu (IC) hesaplar.

    Args:
        factor_values: Kesitsel (ayni tarihte, farkli sembollerdeki) faktor
            degerleri.
        forward_returns: Ayni semboller icin ilgili N-gun-sonraki getiriler
            (factor_values ile AYNI sirada/index'te hizali olmali).

    Returns:
        Spearman correlation katsayisi. Gecerli (NaN olmayan, eslesen)
        cift sayisi < RESEARCH_MIN_IC_SAMPLE_SIZE ise 0.0 doner
        (significance.py'deki n<2 -> 0.0 konvansiyonuyla tutarli, ama
        cross-sectional IC icin daha yuksek bir minimum kullanilir).
    """
    x = np.asarray(factor_values, dtype=float)
    y = np.asarray(forward_returns, dtype=float)
    if len(x) != len(y):
        raise ValueError("factor_values ve forward_returns ayni uzunlukta olmali")
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]
    if len(x) < RESEARCH_MIN_IC_SAMPLE_SIZE:
        return 0.0
    if np.all(x == x[0]) or np.all(y == y[0]):
        return 0.0  # sabit seri -> korelasyon tanimsiz
    correlation, _p_value = stats.spearmanr(x, y)
    return float(correlation) if pd.notna(correlation) else 0.0


def compute_forward_returns(
    price_data: dict[str, pd.DataFrame],
    horizon_days: int = RESEARCH_IC_HORIZON_DAYS,
) -> pd.DataFrame:
    """Her sembol icin N-gun-sonraki (basit) getiriyi uzun formatta hesaplar.

    Args:
        price_data: {symbol: OHLCV DataFrame} (["Close"] kolonu gerekli).
        horizon_days: Ileri bakis ufku (bar sayisi).

    Returns:
        ["date", "symbol", "forward_return"] kolonlarina sahip uzun-format
        DataFrame. forward_return[t] = Close[t+horizon]/Close[t] - 1.
    """
    rows = []
    for symbol, df in price_data.items():
        if df.empty or "Close" not in df.columns:
            continue
        close = df["Close"]
        forward_return = close.shift(-horizon_days) / close - 1.0
        symbol_rows = pd.DataFrame(
            {
                "date": close.index,
                "symbol": symbol,
                "forward_return": forward_return.to_numpy(),
            }
        )
        rows.append(symbol_rows)
    if not rows:
        return pd.DataFrame(columns=["date", "symbol", "forward_return"])
    return pd.concat(rows, ignore_index=True)


def ic_time_series(
    factor_long_df: pd.DataFrame,
    forward_returns_long_df: pd.DataFrame,
    factor_name: str,
) -> pd.Series:
    """Verilen faktor icin, TARIH BAZINDA kesitsel IC zaman serisini hesaplar.

    Args:
        factor_long_df: research/factor_history.py formatinda
            ["date","symbol","factor_name","value"] DataFrame.
        forward_returns_long_df: compute_forward_returns ciktisi formatinda
            ["date","symbol","forward_return"] DataFrame.
        factor_name: factor_long_df icinde filtrelenecek faktor adi.

    Returns:
        Tarihe gore sirali IC Series'i (index=date). Yeterli veri olmayan
        tarihler dahil EDILMEZ (yalnizca hesaplanabilen tarihler doner).
    """
    factor_slice = factor_long_df[factor_long_df["factor_name"] == factor_name]
    merged = factor_slice.merge(
        forward_returns_long_df, on=["date", "symbol"], how="inner"
    )
    if merged.empty:
        return pd.Series(dtype=float)

    ic_by_date: dict = {}
    for date, group in merged.groupby("date"):
        # len(group) DEGIL, GECERLI (NaN olmayan) cift sayisi kontrol edilir:
        # forward_return, en yeni tarihler icin (henuz horizon_days kadar
        # gun gecmediginden) NaN olabilir - grup buyuklugu esigi gecse bile
        # TUM ciftler NaN ise compute_ic() 0.0 fallback'ine duser ve bu,
        # "IC gercekten sifir" ile "IC henuz bilinmiyor" durumlarini
        # yanlislikla ayni gosterir. Bu yuzden gecerlilik SEPARATE kontrol edilir.
        valid_count = int((group["value"].notna() & group["forward_return"].notna()).sum())
        if valid_count >= RESEARCH_MIN_IC_SAMPLE_SIZE:
            ic_by_date[date] = compute_ic(group["value"], group["forward_return"])

    return pd.Series(ic_by_date).sort_index()


def detect_decay(ic_series: pd.Series) -> dict:
    """IC zaman serisini ilk yari / ikinci yari olarak karsilastirip decay tespiti yapar.

    quant2.md'nin "alpha decay" tanimina uyar: burada "in-sample" ilk yari,
    "out-of-sample" ikinci yaridir. DEGRADASYON (ikinci yari IC'nin daha
    dusuk/dagilmis olmasi) faktorun tamamen ISE YARAMADIGI anlamina GELMEZ -
    sadece daha az guvenilir hale geldigini gosterir (bkz. modul docstring'i).

    Args:
        ic_series: ic_time_series ciktisi (tarih index'li IC degerleri).

    Returns:
        {
            "first_half_mean_ic", "second_half_mean_ic",
            "first_half_std_ic", "second_half_std_ic",
            "decayed": bool,  # ikinci yari ortalama IC, ilk yaridan daha dusukse
            "n_first_half", "n_second_half",
        }
        ic_series bos/tek elemanliysa tum sayisal alanlar None, decayed False.
    """
    clean = ic_series.dropna()
    n = len(clean)
    if n < 2:
        return {
            "first_half_mean_ic": None,
            "second_half_mean_ic": None,
            "first_half_std_ic": None,
            "second_half_std_ic": None,
            "decayed": False,
            "n_first_half": 0,
            "n_second_half": 0,
        }

    mid = n // 2
    first_half = clean.iloc[:mid]
    second_half = clean.iloc[mid:]

    first_mean = float(first_half.mean())
    second_mean = float(second_half.mean())

    return {
        "first_half_mean_ic": first_mean,
        "second_half_mean_ic": second_mean,
        "first_half_std_ic": float(first_half.std()) if len(first_half) >= 2 else 0.0,
        "second_half_std_ic": float(second_half.std()) if len(second_half) >= 2 else 0.0,
        "decayed": second_mean < first_mean,
        "n_first_half": len(first_half),
        "n_second_half": len(second_half),
    }


def count_active_filters(filters: dict[str, bool] | list[bool]) -> int:
    """Bir strateji/faktor konfigurasyonundaki AKTIF (True) filtre/kural sayisini sayar."""
    if isinstance(filters, dict):
        values = filters.values()
    else:
        values = filters
    return int(sum(1 for v in values if bool(v)))


def check_rule_burden(
    filters: dict[str, bool] | list[bool] | int,
    max_filters: int = MAX_FILTER_COUNT,
) -> dict:
    """quant2.md'nin "rule burden" uyarisini uygular: cok fazla ardisik filtre = overfitting riski.

    Bu SERT bir kisitlama DEGILDIR (filtre eklemeyi engellemez) - sadece bir
    bayrak dondurur ve esik asilirsa logging.warning ile loglar (dashboard'da
    gosterilebilir - bkz. Modul dashboard entegrasyonu).

    Args:
        filters: Ya {filtre_adi: aktif_mi} sozlugu, ya bool listesi, ya da
            dogrudan aktif filtre sayisi (int).
        max_filters: Esik (varsayilan config.MAX_FILTER_COUNT).

    Returns:
        {"n_filters": int, "max_filters": int, "overfitting_risk": bool}
    """
    n_filters = filters if isinstance(filters, int) else count_active_filters(filters)
    overfitting_risk = n_filters > max_filters
    if overfitting_risk:
        log.warning(
            "Rule burden uyarisi: %d aktif filtre (esik=%d) - quant2.md'nin "
            "'rule burden' riski: ardisik eklenen filtreler data-snooping/"
            "overfitting'e davetiye cikarabilir.",
            n_filters,
            max_filters,
        )
    return {
        "n_filters": n_filters,
        "max_filters": max_filters,
        "overfitting_risk": overfitting_risk,
    }
