"""risk/net_exposure.py testleri - sentetik veriyle (M2 eki)."""

from __future__ import annotations

import numpy as np
import pytest

from risk import net_exposure, portfolio


def test_compute_net_exposure_all_short():
    exposures = {"A": -0.15, "B": -0.10, "C": -0.05}
    assert np.isclose(net_exposure.compute_net_exposure(exposures), -0.30)


def test_compute_net_exposure_all_long():
    exposures = {"A": 0.15, "B": 0.10, "C": 0.05}
    assert np.isclose(net_exposure.compute_net_exposure(exposures), 0.30)


def test_compute_net_exposure_balanced_is_zero():
    exposures = {"A": 0.20, "B": -0.20}
    assert np.isclose(net_exposure.compute_net_exposure(exposures), 0.0)


def test_compute_net_exposure_empty_is_zero():
    assert net_exposure.compute_net_exposure({}) == 0.0


# -- optimize_portfolio entegrasyonu (scipy uzerinden) ----------------------


def test_optimize_portfolio_without_max_net_exposure_is_unconstrained():
    """max_net_exposure verilmezse (varsayilan None), net maruziyet
    kisiti hic UYGULANMAMALI - mevcut davranis DEGISMEMELI."""
    scores = {"A": 5.0, "B": 5.0, "C": 5.0}
    weights = portfolio.optimize_portfolio(scores, max_gross_leverage=1.0, max_position_size=0.5)
    # Kisit yoksa uc pozisyonun tumu de ayni yonde (hepsi pozitif skor)
    # agirlik alabilir, net maruziyet potansiyel olarak yuksek olabilir.
    assert sum(weights.values()) > 0.5  # herhangi bir net-maruziyet sinirina takilmadan


def test_optimize_portfolio_respects_max_net_exposure_all_same_direction():
    """Tum adaylar AYNI yonde (pozitif skor) ise, net maruziyet kisiti
    toplam agirligi max_net_exposure'a KISITLAMALI (gross leverage daha
    gevsek olsa bile)."""
    scores = {"A": 5.0, "B": 5.0, "C": 5.0}
    weights = portfolio.optimize_portfolio(
        scores, max_gross_leverage=1.0, max_position_size=0.5,
        max_net_exposure=0.3,
    )
    net = sum(weights.values())
    assert net <= 0.3 + 1e-6


def test_optimize_portfolio_existing_net_exposure_reduces_available_budget():
    """MEVCUT acik pozisyonlarin net maruziyeti (existing_net_exposure)
    zaten sinira yakinsa, YENI adaylara kalan pay azalmali - M7a'daki
    capraz-gun kume mantigiyla AYNI ilke."""
    scores = {"A": 5.0, "B": 5.0}
    weights_no_existing = portfolio.optimize_portfolio(
        scores, max_gross_leverage=1.0, max_position_size=0.5,
        existing_net_exposure=0.0, max_net_exposure=0.4,
    )
    weights_with_existing = portfolio.optimize_portfolio(
        scores, max_gross_leverage=1.0, max_position_size=0.5,
        existing_net_exposure=0.35, max_net_exposure=0.4,
    )
    assert sum(weights_with_existing.values()) < sum(weights_no_existing.values())
    # existing (0.35) + yeni agirlik toplami 0.4'u asmamali
    assert 0.35 + sum(weights_with_existing.values()) <= 0.4 + 1e-6


def test_optimize_portfolio_balanced_candidates_not_blocked_by_net_exposure():
    """Adaylar birbirini DENGELIYORSA (biri LONG biri SHORT skorlu),
    net maruziyet kisiti onlari GEREKSIZ yere kisitlamamali - kisit
    yalnizca TEK YONE asiri yaslanmayi hedefler."""
    scores = {"A": 5.0, "B": -5.0}
    weights = portfolio.optimize_portfolio(
        scores, max_gross_leverage=1.0, max_position_size=0.5,
        max_net_exposure=0.1,  # SIKI bir net-maruziyet siniri
    )
    # Dengeli oldugu icin (A pozitif, B negatif, esit buyuklukte) her
    # ikisi de max_position_size'a (0.5) kadar acilabilmeli, cunku
    # net toplam ~0'a yakin kalir.
    assert weights["A"] > 0.3
    assert weights["B"] < -0.3


def test_optimize_portfolio_net_exposure_exactly_at_limit_allowed():
    """Sinira TAM oturan bir senaryo reddedilmemeli (kucuk toleransla)."""
    scores = {"A": 5.0}
    weights = portfolio.optimize_portfolio(
        scores, max_gross_leverage=1.0, max_position_size=0.5,
        existing_net_exposure=0.0, max_net_exposure=0.5,
    )
    assert np.isclose(weights["A"], 0.5, atol=1e-4)


def test_optimize_portfolio_existing_net_exposure_already_over_limit_blocks_same_direction():
    """Mevcut pozisyonlar ZATEN siniri asmissa (orn. baska bir kisittan
    kacarak), AYNI yonde yeni bir aday agirlik ALAMAMALI (0'a yakin)."""
    scores = {"A": 5.0}  # pozitif skor -> LONG yonunde
    weights = portfolio.optimize_portfolio(
        scores, max_gross_leverage=1.0, max_position_size=0.5,
        existing_net_exposure=0.55, max_net_exposure=0.5,  # zaten asmis
    )
    assert weights["A"] <= 1e-3
