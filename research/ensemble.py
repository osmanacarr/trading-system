"""Model kombinasyonu / ensemble - Modul 5 (sistematik arastirma mimarisi).

Kaynak: quant2.md (Quantopian risk-optimizasyon dersi). Birebir alinti
(yeni bir faktor eklemeden once korelasyon kontrolu ilkesi):

    "a very common pattern is you'll develop a supposedly new model but
    then you'll just find out that it's actually not that different from
    other stuff" - yeni faktorun MEVCUT faktorlerle ne kadar benzer
    (korele) oldugu kontrol edilmeli; yuksek korelasyon = cesitlendirme
    SAGLAMAZ, dusuk agirlik/eleme uygulanmali.

    "the information coefficient is precisely just the correlation...
    Spearman rank... you'll compare it to existing things... do I want to
    weight it highly, do I want to weight it low, do I want to make them
    all equally [weighted]" - IC-agirlikli kompozit skor bu ilkeyi uygular.

Bu modul validation/alpha_evaluation.py'nin (Modul 3) IC/decay ciktilarini
GIRDI olarak alir - IC/decay hesaplama mantigini burada TEKRAR YAZMAZ.

NOT (basitlestirme): quant2.md'deki "tam" yontem, her faktorun naive-
agirlikli PORTFOY GETIRISINI birbirine regress etmektir (asıl faktor
DEGERLERINI degil). Bu modul, research/factor_history.py'nin ELINDEKI
veriden (dogrudan faktor DEGERLERININ kesitsel korelasyonu) dahaha ucuz
ve dogrudan hesaplanabilir bir yaklasiklama kullanir - iki faktor
DEGERCE yuksek korele ise, onlardan turetilecek pozisyonlar da buyuk
olcude ortusecektir, bu da "cesitlendirme saglamiyor" sonucuna pratikte
ayni sekilde goturur.
"""

from __future__ import annotations

import pandas as pd

from config import (
    RESEARCH_ENSEMBLE_DECAY_PENALTY,
    RESEARCH_FACTOR_CORRELATION_REDUNDANCY_THRESHOLD,
)


def factor_correlation_matrix(factor_long_df: pd.DataFrame) -> pd.DataFrame:
    """Faktorler ARASI kesitsel korelasyon matrisini hesaplar.

    Args:
        factor_long_df: research/factor_history.py formatinda
            ["date","symbol","factor_name","value"] uzun-format DataFrame.

    Returns:
        Faktor adlarini satir/kolon olarak kullanan (Pearson) korelasyon
        matrisi. Girdi bossa bos DataFrame doner.
    """
    if factor_long_df.empty:
        return pd.DataFrame()
    wide = factor_long_df.pivot_table(index=["date", "symbol"], columns="factor_name", values="value")
    return wide.corr()


def flag_redundant_factors(
    corr_matrix: pd.DataFrame,
    threshold: float = RESEARCH_FACTOR_CORRELATION_REDUNDANCY_THRESHOLD,
) -> list[tuple[str, str, float]]:
    """Mutlak korelasyonu esigi asan faktor ciftlerini isaretler ("redundant" - cesitlendirme saglamiyor).

    Args:
        corr_matrix: factor_correlation_matrix ciktisi.
        threshold: Bu mutlak korelasyonu ASAN ciftler isaretlenir (varsayilan
            config.RESEARCH_FACTOR_CORRELATION_REDUNDANCY_THRESHOLD, 0.8).
            Guclu NEGATIF korelasyon da isaretlenir - biri digerinin isareti
            ters cevrilmis hali oldugunda da cesitlendirme SAGLANMAZ.

    Returns:
        (faktor_a, faktor_b, korelasyon) uclulerinin listesi (her cift bir
        kez, i<j sirasiyla).
    """
    if corr_matrix.empty:
        return []
    columns = list(corr_matrix.columns)
    pairs: list[tuple[str, str, float]] = []
    for i, a in enumerate(columns):
        for b in columns[i + 1 :]:
            corr = corr_matrix.loc[a, b]
            if pd.notna(corr) and abs(corr) >= threshold:
                pairs.append((a, b, float(corr)))
    return pairs


def compute_ic_weights(
    ic_by_factor: dict[str, float],
    decay_by_factor: dict[str, dict] | None = None,
    decay_penalty: float = RESEARCH_ENSEMBLE_DECAY_PENALTY,
) -> dict[str, float]:
    """Faktor agirliklarini IC degerlerinden turetir (ISARETLI IC = agirlik).

    ISARETLI IC kullanilir (mutlak deger DEGIL): boylece negatif IC'li bir
    faktor, kompozit skora dogru YONDE (ters cevrilerek) katkida bulunur -
    standart IC-agirlikli kombinasyon yontemi.

    Args:
        ic_by_factor: {faktor_adi: IC} (validation.alpha_evaluation.
            ic_time_series().mean() gibi bir kaynaktan).
        decay_by_factor: Opsiyonel {faktor_adi: validation.alpha_evaluation.
            detect_decay() ciktisi}. "decayed": True olan faktorlerin
            agirligi decay_penalty orani kadar AZALTILIR (elenmez -
            quant2.md: "decay, stratejinin tamamen ise yaramadigi anlamina
            gelmez, sadece daha az guven" ilkesi).
        decay_penalty: Azaltma orani (varsayilan config.
            RESEARCH_ENSEMBLE_DECAY_PENALTY, 0.3 = %30 kesinti).

    Returns:
        {faktor_adi: agirlik} sozlugu.
    """
    weights: dict[str, float] = {}
    for name, ic in ic_by_factor.items():
        weight = ic
        if decay_by_factor is not None and decay_by_factor.get(name, {}).get("decayed"):
            weight *= 1.0 - decay_penalty
        weights[name] = weight
    return weights


def downweight_redundant_factors(
    weights: dict[str, float],
    redundant_pairs: list[tuple[str, str, float]],
    reduction: float = 0.5,
) -> dict[str, float]:
    """Redundant (yuksek korele) ciftlerde, ZAYIF olan (dusuk |agirlik|) faktoru daha da azaltir.

    Guclu (yuksek |agirlik|/IC) faktor DOKUNULMADAN kalir; onunla neredeyse
    ayni bilgiyi tasiyan zayif faktorun agirligi `reduction` ile carpilir -
    quant2.md'nin "dusuk agirlik/eleme uygula" onerisinin KADEMELI (silmeyen)
    versiyonu.

    Args:
        weights: compute_ic_weights ciktisi.
        redundant_pairs: flag_redundant_factors ciktisi.
        reduction: Zayif faktorun agirliginin carpilacagi oran (0-1).

    Returns:
        Guncellenmis {faktor_adi: agirlik} sozlugu (girdi mutasyona ugratilmaz).
    """
    adjusted = dict(weights)
    for a, b, _corr in redundant_pairs:
        weight_a, weight_b = adjusted.get(a, 0.0), adjusted.get(b, 0.0)
        if abs(weight_a) >= abs(weight_b):
            adjusted[b] = weight_b * reduction
        else:
            adjusted[a] = weight_a * reduction
    return adjusted


def composite_score(factor_values: dict[str, float], weights: dict[str, float]) -> float:
    """IC-agirlikli kompozit skoru hesaplar (agirliklarin mutlak toplamiyla normalize edilmis).

    Args:
        factor_values: {faktor_adi: deger} (orn. research.factors.FACTOR_REGISTRY
            fonksiyonlarinin ciktisi).
        weights: {faktor_adi: agirlik} (compute_ic_weights / downweight_redundant_factors ciktisi).

    Returns:
        sum(weight_i * value_i) / sum(|weight_i|) - NaN degerli ya da
        agirligi olmayan faktorler atlanir. Toplam agirlik 0 ise (ya da
        eslesen faktor yoksa) 0.0 doner.
    """
    weighted_sum = 0.0
    total_abs_weight = 0.0
    for name, value in factor_values.items():
        if name not in weights or pd.isna(value):
            continue
        weight = weights[name]
        weighted_sum += weight * value
        total_abs_weight += abs(weight)
    if total_abs_weight == 0:
        return 0.0
    return weighted_sum / total_abs_weight
