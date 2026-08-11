"""research/ensemble.py testleri - sentetik veriyle (Modul 5)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from research import ensemble


def _long_factor_df() -> pd.DataFrame:
    dates = pd.to_datetime(["2020-01-01", "2020-01-01", "2020-01-02", "2020-01-02"])
    wide = pd.DataFrame(
        {
            "date": dates,
            "symbol": ["A", "B", "A", "B"],
            "f1": [1.0, 2.0, 3.0, 4.0],
            "f2": [2.0, 4.0, 6.0, 8.0],  # f1 ile birebir dogru orantili -> corr = 1.0
            "f3": [4.0, 3.0, 2.0, 1.0],  # f1 ile ters orantili -> corr = -1.0
            "f4": [5.0, 1.0, 3.0, 9.0],  # bagimsiz/gurultulu
        }
    )
    return wide.melt(id_vars=["date", "symbol"], var_name="factor_name", value_name="value")


def _find_pair(pairs: list[tuple[str, str, float]], a: str, b: str) -> tuple[str, str, float] | None:
    for pair in pairs:
        if {pair[0], pair[1]} == {a, b}:
            return pair
    return None


def test_factor_correlation_matrix_empty_input_returns_empty_df():
    result = ensemble.factor_correlation_matrix(pd.DataFrame(columns=["date", "symbol", "factor_name", "value"]))
    assert result.empty


def test_factor_correlation_matrix_perfect_positive_correlation():
    corr = ensemble.factor_correlation_matrix(_long_factor_df())
    assert np.isclose(corr.loc["f1", "f2"], 1.0)


def test_factor_correlation_matrix_perfect_negative_correlation():
    corr = ensemble.factor_correlation_matrix(_long_factor_df())
    assert np.isclose(corr.loc["f1", "f3"], -1.0)


def test_factor_correlation_matrix_diagonal_is_one():
    corr = ensemble.factor_correlation_matrix(_long_factor_df())
    for factor in corr.columns:
        assert np.isclose(corr.loc[factor, factor], 1.0)


def test_flag_redundant_factors_detects_positive_and_negative_high_correlation():
    corr = ensemble.factor_correlation_matrix(_long_factor_df())
    pairs = ensemble.flag_redundant_factors(corr, threshold=0.8)
    assert _find_pair(pairs, "f1", "f2") is not None
    assert _find_pair(pairs, "f1", "f3") is not None


def test_flag_redundant_factors_ignores_weakly_correlated_pair():
    corr = ensemble.factor_correlation_matrix(_long_factor_df())
    pairs = ensemble.flag_redundant_factors(corr, threshold=0.999)
    assert _find_pair(pairs, "f1", "f4") is None


def test_flag_redundant_factors_empty_matrix_returns_empty_list():
    assert ensemble.flag_redundant_factors(pd.DataFrame()) == []


def test_compute_ic_weights_uses_signed_ic_directly():
    weights = ensemble.compute_ic_weights({"f1": 0.3, "f2": -0.2})
    assert weights == {"f1": 0.3, "f2": -0.2}


def test_compute_ic_weights_applies_decay_penalty():
    ic_by_factor = {"f1": 0.4}
    decay_by_factor = {"f1": {"decayed": True}}
    weights = ensemble.compute_ic_weights(ic_by_factor, decay_by_factor, decay_penalty=0.5)
    assert np.isclose(weights["f1"], 0.2)


def test_compute_ic_weights_no_penalty_when_not_decayed():
    ic_by_factor = {"f1": 0.4}
    decay_by_factor = {"f1": {"decayed": False}}
    weights = ensemble.compute_ic_weights(ic_by_factor, decay_by_factor, decay_penalty=0.5)
    assert np.isclose(weights["f1"], 0.4)


def test_downweight_redundant_factors_reduces_weaker_of_the_pair():
    weights = {"f1": 0.5, "f2": 0.1}
    pairs = [("f1", "f2", 0.95)]
    adjusted = ensemble.downweight_redundant_factors(weights, pairs, reduction=0.5)
    assert np.isclose(adjusted["f1"], 0.5)  # guclu faktor DOKUNULMAZ
    assert np.isclose(adjusted["f2"], 0.05)  # zayif faktor yariya iner


def test_composite_score_weighted_average():
    factor_values = {"f1": 10.0, "f2": 20.0}
    weights = {"f1": 1.0, "f2": 3.0}
    score = ensemble.composite_score(factor_values, weights)
    assert np.isclose(score, (1.0 * 10.0 + 3.0 * 20.0) / (1.0 + 3.0))


def test_composite_score_skips_nan_and_unweighted_values():
    factor_values = {"f1": 10.0, "f2": float("nan"), "f3": 100.0}
    weights = {"f1": 1.0, "f2": 5.0}  # f3'un agirligi yok -> atlanir
    score = ensemble.composite_score(factor_values, weights)
    assert np.isclose(score, 10.0)  # sadece f1 kaldi (f2 NaN, f3 agirliksiz)


def test_composite_score_empty_weights_returns_zero():
    assert ensemble.composite_score({"f1": 10.0}, {}) == 0.0
