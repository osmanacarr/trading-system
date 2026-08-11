"""validation/walk_forward.py testleri - sentetik veriyle (Modul 3)."""

from __future__ import annotations

import pandas as pd
import pytest

from validation import walk_forward


def _df(n: int) -> pd.DataFrame:
    return pd.DataFrame({"value": range(n)}, index=pd.date_range("2020-01-01", periods=n, freq="B"))


def test_rolling_splits_fixed_train_window_size():
    df = _df(100)
    splits = walk_forward.rolling_splits(df, train_window=20, test_window=10)
    assert len(splits) > 0
    for train_df, test_df in splits:
        assert len(train_df) == 20
        assert len(test_df) == 10


def test_rolling_splits_train_window_slides_forward_not_grows():
    df = _df(60)
    splits = walk_forward.rolling_splits(df, train_window=15, test_window=5)
    first_train_start = splits[0][0].index[0]
    second_train_start = splits[1][0].index[0]
    assert second_train_start > first_train_start
    assert len(splits[0][0]) == len(splits[1][0]) == 15


def test_rolling_splits_no_overlap_between_train_and_test():
    df = _df(50)
    splits = walk_forward.rolling_splits(df, train_window=10, test_window=5)
    for train_df, test_df in splits:
        assert train_df.index[-1] < test_df.index[0]


def test_anchored_splits_train_window_grows():
    df = _df(60)
    splits = walk_forward.anchored_splits(df, min_train_window=15, test_window=5)
    lengths = [len(train_df) for train_df, _ in splits]
    assert lengths == sorted(lengths)  # monoton artan
    assert lengths[0] == 15
    assert lengths[-1] > lengths[0]


def test_anchored_splits_train_always_starts_at_beginning():
    df = _df(60)
    splits = walk_forward.anchored_splits(df, min_train_window=15, test_window=5)
    for train_df, _test_df in splits:
        assert train_df.index[0] == df.index[0]


def test_rolling_and_anchored_produce_same_number_of_splits_for_same_params():
    df = _df(60)
    rolling = walk_forward.rolling_splits(df, train_window=15, test_window=5)
    anchored = walk_forward.anchored_splits(df, min_train_window=15, test_window=5)
    assert len(rolling) == len(anchored)


def test_invalid_window_raises():
    df = _df(30)
    with pytest.raises(ValueError):
        walk_forward.rolling_splits(df, train_window=0, test_window=5)
    with pytest.raises(ValueError):
        walk_forward.anchored_splits(df, min_train_window=5, test_window=-1)


def test_insufficient_data_returns_empty_list():
    df = _df(10)
    assert walk_forward.rolling_splits(df, train_window=20, test_window=5) == []
    assert walk_forward.anchored_splits(df, min_train_window=20, test_window=5) == []


def test_compare_rolling_vs_anchored_reports_means():
    df = _df(60)

    def metric_fn(train_df, test_df):
        return float(len(train_df))

    result = walk_forward.compare_rolling_vs_anchored(df, metric_fn, train_window=15, test_window=5)
    assert result["rolling_mean"] == 15.0  # rolling train hep sabit 15
    assert result["anchored_mean"] > 15.0  # anchored train buyudukce ortalama da artar
