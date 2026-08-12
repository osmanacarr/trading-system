"""research/gozcu_timing.py testleri - sentetik snapshot verisiyle (git'e dokunmadan)."""

from __future__ import annotations

import pandas as pd
import pytest

from research.gozcu_timing import (
    build_attention_history,
    extract_attention_records,
    first_vs_last_daily_change,
    summarize_timing,
)


def _snapshot(market_open: bool, entries: list[dict]) -> dict:
    return {"markets": {"bist": {"market_open": market_open, "attention_list": entries}}}


def test_extract_attention_records_market_closed_returns_empty():
    snap = _snapshot(market_open=False, entries=[{"symbol": "AAA.IS", "daily_change_pct": 0.05}])
    assert extract_attention_records(snap, "2026-08-11T10:00:00Z") == []


def test_extract_attention_records_preserves_rank_order():
    snap = _snapshot(
        market_open=True,
        entries=[
            {"symbol": "AAA.IS", "daily_change_pct": 0.05, "score": 10.0},
            {"symbol": "BBB.IS", "daily_change_pct": 0.03, "score": 8.0},
        ],
    )
    records = extract_attention_records(snap, "2026-08-11T10:00:00Z")
    assert [r["symbol"] for r in records] == ["AAA.IS", "BBB.IS"]
    assert [r["rank"] for r in records] == [1, 2]


def test_build_attention_history_uses_injected_commits_and_loader():
    fake_snapshots = {
        "hash1": _snapshot(True, [{"symbol": "AAA.IS", "daily_change_pct": 0.02, "score": 5.0}]),
        "hash2": _snapshot(True, [{"symbol": "AAA.IS", "daily_change_pct": 0.06, "score": 9.0}]),
        "hash3": _snapshot(False, [{"symbol": "AAA.IS", "daily_change_pct": 0.10, "score": 20.0}]),
    }
    commits = [
        ("hash2", "2026-08-11T11:00:00Z"),
        ("hash1", "2026-08-11T10:00:00Z"),
        ("hash3", "2026-08-11T20:00:00Z"),  # piyasa kapali -> disarida kalmali
    ]

    def loader(commit_hash, repo_root):
        return fake_snapshots[commit_hash]

    history = build_attention_history(market="bist", commits=commits, snapshot_loader=loader)

    assert len(history) == 2  # hash3 (piyasa kapali) haric
    assert list(history["symbol"]) == ["AAA.IS", "AAA.IS"]
    # kronolojik sirali olmali (10:00 -> 11:00)
    assert history["ts"].is_monotonic_increasing
    assert history["daily_change_pct"].tolist() == [0.02, 0.06]


def test_build_attention_history_skips_failed_loads():
    commits = [("bad-hash", "2026-08-11T10:00:00Z")]

    def failing_loader(commit_hash, repo_root):
        raise RuntimeError("git show basarisiz")

    history = build_attention_history(market="bist", commits=commits, snapshot_loader=failing_loader)
    assert history.empty
    assert list(history.columns) == ["ts", "symbol", "rank", "daily_change_pct", "score"]


def test_build_attention_history_empty_commits_returns_empty_df():
    history = build_attention_history(market="bist", commits=[], snapshot_loader=lambda h, r: {})
    assert history.empty


def _history_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    return df


def test_first_vs_last_daily_change_computes_diff():
    history = _history_df(
        [
            {"ts": "2026-08-11T10:00:00Z", "symbol": "AAA.IS", "rank": 1, "daily_change_pct": 0.02, "score": 5.0},
            {"ts": "2026-08-11T14:00:00Z", "symbol": "AAA.IS", "rank": 2, "daily_change_pct": 0.06, "score": 9.0},
        ]
    )
    result = first_vs_last_daily_change(history)
    assert len(result) == 1
    row = result.iloc[0]
    assert row["symbol"] == "AAA.IS"
    assert row["n_observations"] == 2
    assert row["first_pct"] == pytest.approx(2.0)
    assert row["last_pct"] == pytest.approx(6.0)
    assert row["diff_pct_points"] == pytest.approx(4.0)


def test_first_vs_last_daily_change_excludes_single_observation_pairs():
    history = _history_df(
        [{"ts": "2026-08-11T10:00:00Z", "symbol": "AAA.IS", "rank": 1, "daily_change_pct": 0.02, "score": 5.0}]
    )
    result = first_vs_last_daily_change(history, min_observations=2)
    assert result.empty


def test_first_vs_last_daily_change_groups_by_calendar_day():
    """Ayni sembol farkli GUNLERDE gorulduyse, AYRI ciftler olusturulmali - birlestirilmemeli."""
    history = _history_df(
        [
            {"ts": "2026-08-11T10:00:00Z", "symbol": "AAA.IS", "rank": 1, "daily_change_pct": 0.02, "score": 5.0},
            {"ts": "2026-08-11T14:00:00Z", "symbol": "AAA.IS", "rank": 1, "daily_change_pct": 0.05, "score": 5.0},
            {"ts": "2026-08-12T10:00:00Z", "symbol": "AAA.IS", "rank": 1, "daily_change_pct": -0.01, "score": 5.0},
            {"ts": "2026-08-12T14:00:00Z", "symbol": "AAA.IS", "rank": 1, "daily_change_pct": -0.03, "score": 5.0},
        ]
    )
    result = first_vs_last_daily_change(history)
    assert len(result) == 2
    assert set(result["day"].astype(str)) == {"2026-08-11", "2026-08-12"}


def test_first_vs_last_daily_change_empty_history_returns_empty_df():
    result = first_vs_last_daily_change(pd.DataFrame(columns=["ts", "symbol", "rank", "daily_change_pct", "score"]))
    assert result.empty


def test_summarize_timing_computes_ratio_for_same_sign_pairs_only():
    comparison = pd.DataFrame(
        [
            {"day": "2026-08-11", "symbol": "AAA.IS", "n_observations": 2, "first_ts": None, "first_pct": 2.0,
             "last_ts": None, "last_pct": 6.0, "diff_pct_points": 4.0},
            {"day": "2026-08-11", "symbol": "BBB.IS", "n_observations": 2, "first_ts": None, "first_pct": 5.0,
             "last_ts": None, "last_pct": -3.0, "diff_pct_points": -8.0},  # yon degistirdi -> oran DISI
        ]
    )
    summary = summarize_timing(comparison)
    assert summary["n_pairs"] == 2
    assert summary["n_same_sign_pairs"] == 1
    assert summary["mean_already_moved_ratio_pct"] == pytest.approx(2.0 / 6.0 * 100)


def test_summarize_timing_empty_comparison():
    summary = summarize_timing(pd.DataFrame(columns=["day", "symbol", "n_observations", "first_ts", "first_pct", "last_ts", "last_pct", "diff_pct_points"]))
    assert summary["n_pairs"] == 0
    assert summary["mean_diff_pct_points"] is None
