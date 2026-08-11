"""risk/portfolio.py testleri - sentetik veriyle (Modul 6)."""

from __future__ import annotations

import numpy as np
import pytest

from risk import portfolio


def test_naive_weights_from_scores_proportional_and_scaled_to_leverage():
    scores = {"A": 1.0, "B": -1.0, "C": 2.0}
    weights = portfolio.naive_weights_from_scores(scores, max_gross_leverage=1.0)
    assert np.isclose(sum(abs(w) for w in weights.values()), 1.0)
    assert weights["C"] > weights["A"] > 0 > weights["B"]


def test_naive_weights_from_scores_all_zero_scores_returns_zero_weights():
    weights = portfolio.naive_weights_from_scores({"A": 0.0, "B": 0.0})
    assert weights == {"A": 0.0, "B": 0.0}


def test_optimize_portfolio_empty_scores_returns_empty_dict():
    assert portfolio.optimize_portfolio({}) == {}


def test_optimize_portfolio_respects_max_gross_leverage():
    scores = {f"S{i}": float(i + 1) for i in range(10)}
    weights = portfolio.optimize_portfolio(scores, max_gross_leverage=1.0, max_position_size=0.5)
    gross = sum(abs(w) for w in weights.values())
    assert gross <= 1.0 + 1e-6


def test_optimize_portfolio_respects_max_position_size():
    scores = {"A": 100.0, "B": 1.0}  # A cok daha yuksek skorlu, sinir olmasa hepsini A'ya yatirir
    weights = portfolio.optimize_portfolio(scores, max_gross_leverage=1.0, max_position_size=0.3)
    for w in weights.values():
        assert abs(w) <= 0.3 + 1e-6


def test_optimize_portfolio_favors_higher_score_symbol():
    scores = {"A": 5.0, "B": 1.0}
    weights = portfolio.optimize_portfolio(scores, max_gross_leverage=1.0, max_position_size=0.5)
    assert weights["A"] > weights["B"]
    assert weights["A"] > 0


def test_optimize_portfolio_negative_score_gets_short_weight():
    scores = {"A": 5.0, "B": -5.0}
    weights = portfolio.optimize_portfolio(scores, max_gross_leverage=1.0, max_position_size=0.5)
    assert weights["A"] > 0
    assert weights["B"] < 0


def test_optimize_portfolio_dollar_neutral_sums_to_zero():
    scores = {"A": 5.0, "B": 1.0, "C": -3.0}
    weights = portfolio.optimize_portfolio(
        scores, max_gross_leverage=1.0, max_position_size=0.5, dollar_neutral=True
    )
    assert np.isclose(sum(weights.values()), 0.0, atol=1e-6)


def test_optimize_portfolio_respects_sector_exposure():
    scores = {"A": 5.0, "B": 5.0, "C": 1.0}
    sector_map = {"A": "tech", "B": "tech", "C": "energy"}
    weights = portfolio.optimize_portfolio(
        scores,
        max_gross_leverage=1.0,
        max_position_size=0.5,
        sector_map=sector_map,
        max_sector_exposure=0.4,
    )
    tech_exposure = abs(weights["A"] + weights["B"])
    assert tech_exposure <= 0.4 + 1e-6


def test_constraint_impact_report_identical_weights_gives_perfect_correlation():
    weights = {"A": 0.3, "B": -0.2, "C": 0.1}
    report = portfolio.constraint_impact_report(weights, weights)
    assert np.isclose(report["weight_correlation"], 1.0)
    assert np.isclose(report["l2_distance"], 0.0)
    assert report["signal_preserved"] is True


def test_constraint_impact_report_detects_destroyed_signal():
    pre_weights = {"A": 1.0, "B": -1.0, "C": 0.5, "D": -0.5}
    # kisitlar sinyali tamamen bozdu: hepsi ayni kucuk pozitif agirlikta
    post_weights = {"A": 0.1, "B": 0.1, "C": 0.1, "D": 0.1}
    report = portfolio.constraint_impact_report(pre_weights, post_weights)
    assert report["signal_preserved"] is False


def test_constraint_impact_report_empty_inputs():
    report = portfolio.constraint_impact_report({}, {})
    assert report["n_symbols"] == 0
    assert report["weight_correlation"] is None
