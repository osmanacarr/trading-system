"""gozcu/scoring.py icin testler."""

from __future__ import annotations

import numpy as np

from gozcu import scoring


def test_compute_attention_score_combines_components():
    score = scoring.compute_attention_score(
        0.05, 2.0, 3.0, True,
        weight_daily_change=1.0, weight_volume_zscore=1.0, weight_rvol=1.0, momentum_bonus=2.0,
    )
    # 0.05*100=5 + max(2,0)=2 + max(3-1,0)=2 + 2(bonus) = 11
    assert np.isclose(score, 11.0)


def test_compute_attention_score_negative_zscore_and_low_rvol_dont_subtract():
    score = scoring.compute_attention_score(0.0, -3.0, 0.5, False)
    assert score == 0.0


def test_compute_attention_score_handles_none_inputs():
    assert scoring.compute_attention_score(None, None, None, False) == 0.0


def test_rank_by_attention_orders_descending_and_limits_top_n():
    scores = {"A": 5.0, "B": 9.0, "C": 1.0, "D": 7.0}
    ranked = scoring.rank_by_attention(scores, top_n=2)
    assert ranked == [("B", 9.0), ("D", 7.0)]


def test_rank_by_attention_empty_input():
    assert scoring.rank_by_attention({}, top_n=20) == []
