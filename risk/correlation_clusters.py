"""risk/correlation_clusters.py - gercek getiri korelasyonundan bir "kume"
haritasi uretir; bu, risk/portfolio.py::optimize_portfolio'nun sector_map
parametresine DEGISTIRMEDEN yerine gecirilir.

Gerekce (faz3.5_matematiksel_formalizasyon.md SS6): BIST'teki semboller
ortak makro faktorlere (TL, yerel faiz, BIST endeksi) maruz kalir - bu,
"sektor" etiketiyle yakalanamayan ama gercek olan bir risk. Bu depoda
guvenilir bir sembol->sektor eslemesi YOK ve UYDURULMAYACAK (bkz.
risk/portfolio.py modul docstring'i) - onun yerine ampirik getiri
korelasyonu kullanilir.

Tam kovaryans-bazli portfoy optimizasyonu (Markowitz) BILINCLI OLARAK
kullanilmadi: kucuk orneklemli kovaryans matrisleri dengesizdir ve
kisitlama modeli tamamen bozabilir (bkz. risk/portfolio.py modul
docstring'indeki constraint_impact_report uyarisi, Faz3.5 SS6). Bunun
yerine basit, saglam bir tek-baglantili (single-linkage) greedy kumeleme +
mevcut sector_map/max_sector_exposure kisit motoru (degistirilmeden)
kullanilir. Single-linkage'in bilinen "zincirleme" (A-B ve B-C korelasyonlu
ama A-C degil, ucu de ayni kumeye girer) egilimi burada BILINCLI: kucuk
sermayede fazla temkinli olmanin maliyeti, az temkinli olmaktan dusuktur.
"""

from __future__ import annotations

import pandas as pd

from config import (
    RISK_CORRELATION_CLUSTER_LOOKBACK_DAYS,
    RISK_CORRELATION_CLUSTER_THRESHOLD,
)


def compute_return_matrix(
    price_data: dict[str, pd.DataFrame],
    lookback_days: int = RISK_CORRELATION_CLUSTER_LOOKBACK_DAYS,
) -> pd.DataFrame:
    """Sembol basina Close serisinden, ortak tarihlerde hizalanmis gunluk getiri matrisi uretir.

    Args:
        price_data: {sembol: OHLCV DataFrame} ("Close" kolonu ve
            DatetimeIndex icermeli, kronolojik sirali).
        lookback_days: Sondan geriye kac barlik pencere kullanilacak.

    Returns:
        Sutunlari sembol, satirlari tarih olan getiri (pct_change)
        DataFrame'i (ic kesisim tarihlerinde hizalanmis, NaN satirlar
        atilmis). Gecerli veri < 2 sembolse veya ortak tarih < 2 ise bos
        DataFrame doner.
    """
    closes: dict[str, pd.Series] = {}
    for symbol, df in price_data.items():
        if df is None or df.empty or "Close" not in df.columns:
            continue
        closes[symbol] = df["Close"].tail(lookback_days + 1)

    if len(closes) < 2:
        return pd.DataFrame()

    price_df = pd.DataFrame(closes).dropna(how="any")
    if len(price_df) < 2:
        return pd.DataFrame()

    return price_df.pct_change().dropna(how="all")


def build_correlation_clusters(
    returns_df: pd.DataFrame,
    threshold: float = RISK_CORRELATION_CLUSTER_THRESHOLD,
) -> dict[str, str]:
    """Getiri korelasyonuna gore tek-baglantili (single-linkage) greedy kumeleme yapar.

    Algoritma: sutun sirasina gore (deterministik) her sembol, mevcut
    kumelerden EN AZ BIR uyeyle |korelasyonu| >= threshold olan ILK kumeye
    eklenir; hicbir kume uymuyorsa yeni (tek elemanli) bir kume acilir. Bu,
    yuksek korelasyonlu sembolleri AYNI kumede toplar (dusuk korelasyonluları
    degil) - amac, ayni kumedeki toplam agirligi
    risk.portfolio.optimize_portfolio'nun max_sector_exposure kisitiyla
    sinirlamak.

    NaN korelasyon (ortak veri yetersizse) 0.0 (korelasyonsuz) kabul edilir
    - kanitlanamayan bir korelasyonu varmis gibi kumelemek yerine.

    Args:
        returns_df: compute_return_matrix ciktisi (sutun=sembol, satir=tarih).
        threshold: Bu korelasyonun USTUNDEKI (|corr|>=threshold) ciftler
            ayni kumeye konur.

    Returns:
        {sembol: "cluster_N"} - risk.portfolio.optimize_portfolio'nun
        sector_map parametresine dogrudan verilebilir. returns_df bossa {}
        doner; tek sutunluysa o sembol kendi kumesinde doner.
    """
    symbols = list(returns_df.columns)
    if len(symbols) == 0:
        return {}
    if len(symbols) == 1:
        return {symbols[0]: "cluster_0"}

    corr = returns_df.corr()

    clusters: list[list[str]] = []
    assignment: dict[str, str] = {}

    for symbol in symbols:
        placed = False
        for cluster_idx, members in enumerate(clusters):
            max_corr = max(
                (abs(corr.loc[symbol, member]) if pd.notna(corr.loc[symbol, member]) else 0.0)
                for member in members
            )
            if max_corr >= threshold:
                members.append(symbol)
                assignment[symbol] = f"cluster_{cluster_idx}"
                placed = True
                break
        if not placed:
            clusters.append([symbol])
            assignment[symbol] = f"cluster_{len(clusters) - 1}"

    return assignment
