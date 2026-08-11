"""gozcu/psychology.py - Piyasa psikolojisi gostergesi (breadth bazli 0-100 gauge).

ONEMLI: Bu bir ZAMANLAMA ARACI DEGILDIR. Korku/coşku donemleri tarihte uzun
surebilir, tek basina karar vermek icin kullanilmamalidir (bkz. gorev
tanimi Bolum 4 - bu uyari dashboard'da KALICI olarak gosterilecek).

Breadth (% pozitif kapanan) ve oynaklik rejimi BILINCLI OLARAK ayri iki
sinyal olarak tutulur, tek bir sayiya harmanlanmaz: breadth 0-100 araliginda
doganal ve sezgisel bir "% pozitif" anlamina sahipken, |gunluk %degisim|
ortalamasi farkli bir birimdedir (oran) - ikisini tek bir agirlikli toplama
sikistirmak gostergenin "% pozitif kapanan" anlamini bulaniklastirirdi.
"""

from __future__ import annotations

from config import GOZCU_VOLATILITY_REGIME_ELEVATED_PCT, GOZCU_VOLATILITY_REGIME_EXTREME_PCT

VolatilityRegime = str  # "normal" | "yuksek" | "asiri" | "bilinmiyor"


def compute_breadth_pct(daily_changes: list[float | None]) -> float | None:
    """Taranan evrenin yuzde kacinin gunluk pozitif kapandigini hesaplar (0-100).

    Args:
        daily_changes: Her sembol icin gunluk %degisim (None = veri yok, sayilmaz).

    Returns:
        None: hicbir sembol icin gecerli veri yoksa.
    """
    valid = [c for c in daily_changes if c is not None]
    if not valid:
        return None
    positive = sum(1 for c in valid if c > 0)
    return (positive / len(valid)) * 100.0


def compute_volatility_regime(
    daily_changes: list[float | None],
    elevated_threshold: float = GOZCU_VOLATILITY_REGIME_ELEVATED_PCT,
    extreme_threshold: float = GOZCU_VOLATILITY_REGIME_EXTREME_PCT,
) -> VolatilityRegime:
    """Evrenin ortalama |gunluk %degisim|'ine gore oynaklik rejimini etiketler.

    Returns:
        "bilinmiyor" (veri yok), "normal", "yuksek" veya "asiri".
    """
    valid = [c for c in daily_changes if c is not None]
    if not valid:
        return "bilinmiyor"
    avg_abs_change = sum(abs(c) for c in valid) / len(valid)
    if avg_abs_change >= extreme_threshold:
        return "asiri"
    if avg_abs_change >= elevated_threshold:
        return "yuksek"
    return "normal"
