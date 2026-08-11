"""gozcu/correlation.py - Korelasyon ozeti (tam NxN matris yerine, evrenin
referans endekse gore ORTALAMA korelasyonu - performans icin).

Yuksek ortalama korelasyon = "cogu hisse ayni yone hareket ediyor,
cesitlendirme sinirli" uyarisi (faz3.5_matematiksel_formalizasyon.md SS6'daki
prensibin canli versiyonu, bkz. gorev tanimi Bolum 5).

Referans sembol secimi (BIST: XU100.IS/^XU100, NASDAQ: QQQ) gozcu/scanner.py
tarafinda config.py sabitleriyle yonetilir - bu modul sadece hesaplamayi yapar.
"""

from __future__ import annotations

import pandas as pd


def compute_returns(daily_df: pd.DataFrame, lookback: int = 20) -> pd.Series:
    """Son `lookback` gunluk basit getiri serisini hesaplar (Close.pct_change)."""
    close = daily_df["Close"].dropna()
    if len(close) < 2:
        return pd.Series(dtype=float)
    returns = close.pct_change().dropna()
    return returns.iloc[-lookback:]


def average_correlation_to_reference(
    returns_by_symbol: dict[str, pd.Series],
    reference_returns: pd.Series,
    min_overlap: int = 10,
) -> float | None:
    """Evrendeki sembollerin getirilerinin referans endeks getirisiyle ORTALAMA korelasyonu.

    Args:
        returns_by_symbol: {sembol: getiri Series'i} (gozcu.correlation.compute_returns ile uretilir).
        reference_returns: Referans endeks/ETF'in ayni tip getiri Series'i.
        min_overlap: Bir sembolun korelasyona dahil edilmesi icin gereken
            minimum ORTAK (hizalanmis) gun sayisi.

    Returns:
        None: referans veri bos veya hicbir sembol yeterli ortak veriye sahip degilse.
    """
    if reference_returns.empty:
        return None

    correlations: list[float] = []
    for returns in returns_by_symbol.values():
        if returns.empty:
            continue
        aligned = pd.concat([returns, reference_returns], axis=1, join="inner").dropna()
        if len(aligned) < min_overlap:
            continue
        corr = aligned.iloc[:, 0].corr(aligned.iloc[:, 1])
        if corr is not None and not pd.isna(corr):
            correlations.append(float(corr))

    if not correlations:
        return None
    return sum(correlations) / len(correlations)
