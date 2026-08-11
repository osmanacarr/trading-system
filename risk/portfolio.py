"""Risk-kisitli portfoy insasi - Modul 6 (sistematik arastirma mimarisi).

Kaynak: quant2.md (Quantopian `optimize.maximize_alpha` dersi). Bu modul
o API'nin basit bir `scipy.optimize` (SLSQP) versiyonudur - HARICI bir
platforma (cvxpy dahil) BAGIMLI DEGILDIR (scipy zaten repo'nun mevcut
bagimliligi, validation/significance.py'de de kullaniliyor).

Objektif: kompozit skora (research/ensemble.py::composite_score ciktisi)
gore agirliklandirilmis TOPLAM skoru maksimize et (yani -skor'u minimize
et). Kisitlar (quant2.md'deki sirayla, birebir alintilarla):

    - max brut leverage: "we wouldn't use more than 100 percent of our
      available capital"
    - max tek pozisyon buyuklugu: "we can't be more than 15 percent short
      any one thing and we can't be more than 30 percent long any one
      thing"
    - sektor maruziyeti: "we're totally overexposed to technology... we
      don't have anything in energy" (asiri yogunlasmayi onlemek icin)
    - dollar-neutral (opsiyonel): "sector exposures have to be equal...
      this is kind of something that's very hard to achieve"

UYARI (birebir, quant2.md - bu modulun KRITIK varsayimi, docstring'de
KORUNMALI): "it can be the case that risk constraining just completely
destroys your model... some models are just not risk-aware... it's not
necessarily the model's fault." Bu YUZDEN constraint_impact_report()
kisitlama ONCESI/SONRASI agirlik korelasyonunu raporlar - dusuk korelasyon
"optimizasyon bozuk" degil, "bu skor seti risk-kisitlari altinda iyi
davranmiyor olabilir" anlamina gelir; yorumlama cagiran tarafa aittir.

Sektor haritasi: bu depoda GUVENILIR bir sembol->sektor eslemesi YOK -
UYDURULMAYACAK. sector_map (opsiyonel) cagiran kod tarafindan saglanmalidir.
"""

from __future__ import annotations

import logging

import numpy as np
from scipy.optimize import minimize

from config import (
    RISK_MAX_GROSS_LEVERAGE,
    RISK_MAX_POSITION_SIZE,
    RISK_MAX_SECTOR_EXPOSURE,
)

log = logging.getLogger("risk.portfolio")


def naive_weights_from_scores(
    scores: dict[str, float],
    max_gross_leverage: float = RISK_MAX_GROSS_LEVERAGE,
) -> dict[str, float]:
    """Risk kisiti UYGULANMAMIS, sadece skorlarla ORANTILI "naive" hedef agirliklari hesaplar.

    Bu, "modelin GERCEKTEN ne istedigi" referans noktasidir - optimize_portfolio()
    ciktisiyla constraint_impact_report() araciligiyla karsilastirilir.

    Args:
        scores: {sembol: kompozit_skor}.
        max_gross_leverage: Toplam |agirlik| bu degere olceklenir.

    Returns:
        {sembol: agirlik}. Tum skorlar 0 ise (ya da scores bossa) tum
        agirliklar 0.0 doner.
    """
    total_abs_score = sum(abs(v) for v in scores.values())
    if total_abs_score == 0:
        return {symbol: 0.0 for symbol in scores}
    return {symbol: (value / total_abs_score) * max_gross_leverage for symbol, value in scores.items()}


def optimize_portfolio(
    scores: dict[str, float],
    max_gross_leverage: float = RISK_MAX_GROSS_LEVERAGE,
    max_position_size: float = RISK_MAX_POSITION_SIZE,
    sector_map: dict[str, str] | None = None,
    max_sector_exposure: float = RISK_MAX_SECTOR_EXPOSURE,
    dollar_neutral: bool = False,
) -> dict[str, float]:
    """Kompozit skorlara gore, risk kisitlari altinda agirliklandirilmis-getiriyi maksimize eden portfoy insa eder.

    Args:
        scores: {sembol: kompozit_skor} (research.ensemble.composite_score
            ciktilari - yuksek skor = daha guclu beklenen getiri).
        max_gross_leverage: sum(|w_i|) <= bu deger (varsayilan %100).
        max_position_size: |w_i| <= bu deger, HER sembol icin (simetrik
            long/short sinir).
        sector_map: Opsiyonel {sembol: sektor_adi}. None ise sektor kisiti
            UYGULANMAZ (guvenilir veri olmadan kisit uydurulmaz).
        max_sector_exposure: sector_map verildiyse, her sektor icin
            |sum(w_i in sektor)| <= bu deger.
        dollar_neutral: True ise sum(w_i) == 0 kisiti eklenir (esit
            long/short tutar).

    Returns:
        {sembol: agirlik}. scores bossa bos sozluk doner. Optimizasyon
        yakinsamazsa (result.success=False) en iyi bulunan nokta yine de
        donulur ve bir uyari loglanir (COKMEZ - cagiran kod feasibility'yi
        constraint_impact_report ile kontrol edebilir).
    """
    symbols = sorted(scores.keys())
    n = len(symbols)
    if n == 0:
        return {}

    score_arr = np.array([scores[s] for s in symbols], dtype=float)

    def objective(w: np.ndarray) -> float:
        return -float(np.dot(w, score_arr))

    def objective_grad(w: np.ndarray) -> np.ndarray:
        return -score_arr

    bounds = [(-max_position_size, max_position_size)] * n

    constraints: list[dict] = [
        {"type": "ineq", "fun": lambda w: max_gross_leverage - np.sum(np.abs(w))},
    ]
    if dollar_neutral:
        constraints.append({"type": "eq", "fun": lambda w: np.sum(w)})

    if sector_map is not None:
        sectors = sorted({sector_map[s] for s in symbols if s in sector_map})
        for sector in sectors:
            idx = np.array([i for i, s in enumerate(symbols) if sector_map.get(s) == sector])

            def sector_upper(w: np.ndarray, idx: np.ndarray = idx) -> float:
                return max_sector_exposure - np.sum(w[idx])

            def sector_lower(w: np.ndarray, idx: np.ndarray = idx) -> float:
                return max_sector_exposure + np.sum(w[idx])

            constraints.append({"type": "ineq", "fun": sector_upper})
            constraints.append({"type": "ineq", "fun": sector_lower})

    w0 = np.zeros(n)
    result = minimize(
        objective,
        w0,
        jac=objective_grad,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 200, "ftol": 1e-9},
    )
    if not result.success:
        log.warning("Portfoy optimizasyonu yakinsamadi: %s", result.message)

    return dict(zip(symbols, result.x))


def constraint_impact_report(pre_weights: dict[str, float], post_weights: dict[str, float]) -> dict:
    """Kisitlama ONCESI (naive) ve SONRASI (optimize edilmis) agirliklari karsilastirir.

    quant2.md'nin uyarisina gore ("risk constraining just completely
    destroys your model" olabilir) - DUSUK korelasyon bir HATA DEGIL, bir
    TEshis noktasidir: ya kisitlar gevsetilmeli ya da skorlama modeli
    risk-farkinda yeniden tasarlanmali (bkz. modul docstring'i).

    Args:
        pre_weights: naive_weights_from_scores ciktisi (ya da baska bir
            kisitsiz hedef agirlik seti).
        post_weights: optimize_portfolio ciktisi.

    Returns:
        {"n_symbols", "weight_correlation" (None ya da [-1,1]),
        "l2_distance", "signal_preserved" (korelasyon > 0.7 sezgisel esigi)}.
    """
    symbols = sorted(set(pre_weights) | set(post_weights))
    if not symbols:
        return {"n_symbols": 0, "weight_correlation": None, "l2_distance": 0.0, "signal_preserved": False}

    pre = np.array([pre_weights.get(s, 0.0) for s in symbols])
    post = np.array([post_weights.get(s, 0.0) for s in symbols])

    correlation = None
    if len(symbols) >= 2 and not np.all(pre == pre[0]) and not np.all(post == post[0]):
        raw_corr = np.corrcoef(pre, post)[0, 1]
        correlation = float(raw_corr) if np.isfinite(raw_corr) else None

    return {
        "n_symbols": len(symbols),
        "weight_correlation": correlation,
        "l2_distance": float(np.linalg.norm(pre - post)),
        "signal_preserved": correlation is not None and correlation > 0.7,
    }
