"""paper_trading/runner.py::_classify_rejection_reason icin sentetik testler.

"En Iyi N Firsat" ozelliginin (bkz. paper_trading/opportunities.py) her
kartinda ZORUNLU gosterilen red nedeninin dogru siniflandirildigini
dogrular - bkz. _classify_rejection_reason docstring'indeki oncelik sirasi.
"""

from __future__ import annotations

import datetime as dt

from paper_trading.runner import EntryCandidate, _classify_rejection_reason
from tests.conftest import make_flat_range_df


def _candidate(direction: int = 1) -> EntryCandidate:
    return EntryCandidate(
        symbol="THYAO.IS", strategy="donchian", market="bist", direction=direction,
        entry_price=100.0, stop_price=95.0, signal_date=dt.date(2026, 8, 12),
        df=make_flat_range_df(n=30),
    )


def test_gross_budget_exhausted_takes_priority():
    reason = _classify_rejection_reason(
        _candidate(), "THYAO.IS::donchian", remaining_budget=0.0,
        candidate_clusters={"THYAO.IS::donchian": "cluster_1"}, sector_caps={"cluster_1": 0.4},
        existing_net_exposure=0.0, max_net_exposure=0.5,
    )
    assert "kaldirac" in reason.lower()


def test_correlation_cluster_exhausted():
    reason = _classify_rejection_reason(
        _candidate(), "THYAO.IS::donchian", remaining_budget=0.3,
        candidate_clusters={"THYAO.IS::donchian": "cluster_1"}, sector_caps={"cluster_1": 0.0},
        existing_net_exposure=0.0, max_net_exposure=0.5,
    )
    assert "korelasyon" in reason.lower()


def test_net_exposure_near_limit_same_direction():
    reason = _classify_rejection_reason(
        _candidate(direction=1), "THYAO.IS::donchian", remaining_budget=0.3,
        candidate_clusters={}, sector_caps={},
        existing_net_exposure=0.5, max_net_exposure=0.5,
    )
    assert "net yonlu" in reason.lower()


def test_net_exposure_not_flagged_when_opposite_direction():
    # Mevcut maruziyet LONG'a yasli (existing_net_exposure>0) ama aday SHORT (-1) -
    # ayni yonde DEGIL, bu yuzden net-maruziyet nedeni UYGULANMAMALI.
    reason = _classify_rejection_reason(
        _candidate(direction=-1), "THYAO.IS::donchian", remaining_budget=0.3,
        candidate_clusters={}, sector_caps={},
        existing_net_exposure=0.5, max_net_exposure=0.5,
    )
    assert "net yonlu" not in reason.lower()


def test_generic_fallback_when_no_constraint_clearly_binding():
    reason = _classify_rejection_reason(
        _candidate(), "THYAO.IS::donchian", remaining_budget=0.5,
        candidate_clusters={}, sector_caps={},
        existing_net_exposure=0.0, max_net_exposure=0.5,
    )
    assert "oncelik verildi" in reason.lower()
