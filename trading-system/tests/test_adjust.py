"""data/adjust.py icin sentetik veri testleri."""

from __future__ import annotations

import numpy as np
import pandas as pd

from data.adjust import adjust_jumps, detect_jumps


def _series_with_jump(jump_ratio: float = 0.5) -> pd.DataFrame:
    """10 barlik duz bir seri + 1 sicrama barindan olusan sentetik veri."""
    dates = pd.date_range("2021-01-01", periods=10, freq="B")
    close = np.array([100.0] * 5 + [100 * jump_ratio] * 5)
    df = pd.DataFrame(
        {
            "Open": close,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": np.full(10, 1000.0),
        },
        index=dates,
    )
    return df


def test_detect_jumps_finds_the_jump_bar():
    df = _series_with_jump(jump_ratio=0.5)  # %50 dusus
    jumps = detect_jumps(df, threshold=0.40)
    assert len(jumps) == 1
    assert jumps[0] == df.index[5]


def test_detect_jumps_ignores_small_moves():
    df = _series_with_jump(jump_ratio=0.85)  # %15 dusus, esigin altinda
    jumps = detect_jumps(df, threshold=0.40)
    assert len(jumps) == 0


def test_adjust_jumps_removes_discontinuity():
    df = _series_with_jump(jump_ratio=0.5)
    adjusted = adjust_jumps(df, threshold=0.40)

    # Sicrama sonrasi getiri artik esigin altinda olmali
    returns = adjusted["Close"].pct_change()
    assert returns.abs().max() < 0.40

    # Sicramadan sonraki barlar degismemis olmali
    pd.testing.assert_series_equal(
        adjusted["Close"].iloc[5:], df["Close"].iloc[5:], check_names=False
    )
    # Sicramadan onceki barlar olceklenmis olmali (orijinalden farkli)
    assert not np.allclose(adjusted["Close"].iloc[:5], df["Close"].iloc[:5])


def test_adjust_jumps_noop_when_no_jump():
    df = _series_with_jump(jump_ratio=0.95)  # %5, esigin cok altinda
    adjusted = adjust_jumps(df, threshold=0.40)
    pd.testing.assert_frame_equal(adjusted, df)
