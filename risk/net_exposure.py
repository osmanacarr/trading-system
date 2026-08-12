"""risk/net_exposure.py - NET yonlu maruziyet kisiti (M2 eki, Modul 6 devam).

Gerekce (2026-08-12 canli gozlem): risk/portfolio.py::optimize_portfolio
GROSS kaldiraci (max_gross_leverage) ve risk/correlation_clusters.py ile
kume-ici yogunlasmayi (max_sector_exposure) sinirliyor, ama bu ikisi
FARKLI bir riski YAKALAMAZ: portfoydeki TUM pozisyonlar FARKLI
korelasyon kumelerinde olsa (yani kume kisiti hicbir sey yapmasa) bile,
hepsi AYNI YONDE (orn. hepsi SHORT) acilirsa portfoy yine de BIST-geneli/
TL yonune TEK TARAFLI, buyuk bir bahis haline gelebilir. Canli
calistirmada 5 acik pozisyon (4 SHORT + 1 LONG, hepsi FARKLI kumelerde)
equity'nin %37.8'i net SHORT'tu - kume kisiti bunu hic gormedi cunku
bakmadigi bir boyuttu.

Kisit: |mevcut_acik_pozisyonlarin_net_maruziyeti + yeni_adaylarin_net_agirligi|
<= MAX_NET_EXPOSURE_PCT. Kume kisitiyle (M7a, paper_trading/runner.py)
AYNI ilke: MEVCUT acik pozisyonlar hesaba katilir, sadece o GUNUN
adaylari degil - bir gunde sinira uyan bir portfoy, ertesi gun ayni
yonde eklenen yeni pozisyonlarla sessizce asilamaz.
"""

from __future__ import annotations

import numpy as np

from config import MAX_NET_EXPOSURE_PCT


def compute_net_exposure(exposures: dict[str, float]) -> float:
    """Isaretli maruziyetlerin (LONG:+ SHORT:-) net toplamini hesaplar.

    Args:
        exposures: {sembol: isaretli_maruziyet} - her deger genelde
            (yon * dolar_degeri) / equity seklinde, cagiran kod
            (bkz. paper_trading/runner.py::allocate_and_open_candidates)
            acik pozisyonlardan hesaplar.

    Returns:
        Net toplam (pozitif = net LONG, negatif = net SHORT, 0 = dengeli).
        exposures bossa 0.0 doner.
    """
    return sum(exposures.values())


def build_constraints(
    existing_net_exposure: float,
    max_net_exposure: float = MAX_NET_EXPOSURE_PCT,
) -> list[dict]:
    """risk.portfolio.optimize_portfolio icin scipy.optimize uyumlu net-maruziyet kisitlari uretir.

    Kisit iki tarafli (ust ve alt sinir) olarak ifade edilir - |x|<=c,
    scipy'nin kolayca isleyebilecegi turevlenebilir bir formda degildir,
    bu yuzden iki ayri ineq kisitina (c-x>=0 ve c+x>=0) bolunur (mevcut
    sektor kisitlariyla AYNI desen, bkz. risk/portfolio.py).

    Args:
        existing_net_exposure: Acik pozisyonlarin (TUM stratejiler,
            optimizasyon disindaki SABIT kisim) net isaretli maruziyeti.
        max_net_exposure: |existing_net_exposure + sum(w)| bu degeri
            asamaz.

    Returns:
        scipy.optimize.minimize'a dogrudan eklenebilecek iki {"type":
        "ineq", "fun": ...} sozlugu icaren liste. w, optimize_portfolio
        icindeki karar degiskeni (aday agirliklari) vektorudur - net
        maruziyet HERHANGI bir sembole ozel olmadigindan (kumeden farkli
        olarak) yalnizca sum(w) yeterlidir, sembol-index eslemesi
        gerekmez.
    """

    def upper(w: np.ndarray) -> float:
        return max_net_exposure - (existing_net_exposure + np.sum(w))

    def lower(w: np.ndarray) -> float:
        return max_net_exposure + (existing_net_exposure + np.sum(w))

    return [
        {"type": "ineq", "fun": upper},
        {"type": "ineq", "fun": lower},
    ]
