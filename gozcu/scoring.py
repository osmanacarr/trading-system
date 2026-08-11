"""gozcu/scoring.py - Kompozit "Dikkat Skoru" ve siralama.

ONEMLI: Bu skor bir AL-SAT tavsiyesi degildir. Sadece "en cok hareket eden /
konusulan" sembolleri one cikaran bir SIRALAMA olcusudur (bkz. gorev
tanimi, Bolum 3). Agirliklar config.py'de degistirilebilir sabitlerdir.
"""

from __future__ import annotations

from config import (
    GOZCU_ATTENTION_LIST_TOP_N,
    GOZCU_SCORE_MOMENTUM_BONUS,
    GOZCU_SCORE_WEIGHT_DAILY_CHANGE,
    GOZCU_SCORE_WEIGHT_RVOL,
    GOZCU_SCORE_WEIGHT_VOLUME_ZSCORE,
)


def compute_attention_score(
    daily_change_pct: float | None,
    volume_zscore: float | None,
    rvol: float | None,
    momentum_flag: bool,
    weight_daily_change: float = GOZCU_SCORE_WEIGHT_DAILY_CHANGE,
    weight_volume_zscore: float = GOZCU_SCORE_WEIGHT_VOLUME_ZSCORE,
    weight_rvol: float = GOZCU_SCORE_WEIGHT_RVOL,
    momentum_bonus: float = GOZCU_SCORE_MOMENTUM_BONUS,
) -> float:
    """Bir sembolun dikkat skorunu hesaplar.

    Skor = w1*|gunluk %degisim (puan)| + w2*max(hacim_zskoru, 0)
         + w3*max(RVOL - 1, 0) + (momentum mumu ise bonus, degilse 0)

    |gunluk %degisim| yuzde PUANINA (0.05 -> 5.0) cevrilir ki z-skoru/RVOL
    ile karsilastirilabilir bir olcekte olsun. Sadece POZITIF hacim_zskoru
    ve normalin USTUNDEKI RVOL (RVOL-1 > 0) "dikkat" olarak sayilir - dusuk
    hacim/RVOL skoru asagi cekmez, sadece katki vermez.

    Eksik (None) girdiler o bilesenin katkisini 0 sayar, hicbir istisna
    firlatmaz.
    """
    score = 0.0
    if daily_change_pct is not None:
        score += weight_daily_change * abs(daily_change_pct) * 100.0
    if volume_zscore is not None:
        score += weight_volume_zscore * max(volume_zscore, 0.0)
    if rvol is not None:
        score += weight_rvol * max(rvol - 1.0, 0.0)
    if momentum_flag:
        score += momentum_bonus
    return score


def rank_by_attention(
    symbol_scores: dict[str, float],
    top_n: int = GOZCU_ATTENTION_LIST_TOP_N,
) -> list[tuple[str, float]]:
    """Sembolleri dikkat skoruna gore azalan sirada siralar, ilk `top_n`'i doner.

    Bu bir "en iyi" listesi DEGIL, "en cok hareket eden" listesidir.
    """
    ordered = sorted(symbol_scores.items(), key=lambda item: item[1], reverse=True)
    return ordered[:top_n]
