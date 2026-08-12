"""research/opportunity_score.py icin sentetik veriyle testler.

signals/donchian.py'ye HIC dokunulmuyor - bu testler SADECE yeni,
BAGIMSIZ compute_donchian_breakout_quality() fonksiyonunu dogrular.
"""

from __future__ import annotations

import pandas as pd
import pytest

from research.opportunity_score import compute_donchian_breakout_quality
from tests.conftest import append_bars, make_flat_range_df


def _breakout_df(breakout_close: float, volume: float = 1000.0) -> pd.DataFrame:
    base = make_flat_range_df(n=30, price=100.0, half_range=1.0, volume=1000.0)
    bar = {"Open": 101.0, "High": breakout_close + 1.0, "Low": 100.5, "Close": breakout_close, "Volume": volume}
    return append_bars(base, [bar])


def _breakdown_df(breakdown_close: float, volume: float = 1000.0) -> pd.DataFrame:
    base = make_flat_range_df(n=30, price=100.0, half_range=1.0, volume=1000.0)
    bar = {"Open": 99.0, "High": 99.5, "Low": breakdown_close - 1.0, "Close": breakdown_close, "Volume": volume}
    return append_bars(base, [bar])


def test_returns_none_when_insufficient_bars():
    df = make_flat_range_df(n=5, price=100.0, half_range=1.0, volume=1000.0)
    assert compute_donchian_breakout_quality(df, direction=1) is None


def test_returns_none_when_atr_is_degenerate_zero():
    # half_range=0 -> High==Low==Open==Close her barda, TR/ATR daima 0.
    df = make_flat_range_df(n=40, price=100.0, half_range=0.0, volume=1000.0)
    assert compute_donchian_breakout_quality(df, direction=1) is None


def test_larger_breakout_gives_larger_atr_distance():
    small = compute_donchian_breakout_quality(_breakout_df(breakout_close=103.0), direction=1)
    large = compute_donchian_breakout_quality(_breakout_df(breakout_close=115.0), direction=1)
    assert small is not None and large is not None
    assert large["atr_distance"] > small["atr_distance"] > 0


def test_short_direction_uses_lower_channel():
    quality = compute_donchian_breakout_quality(_breakdown_df(breakdown_close=85.0), direction=-1)
    assert quality is not None
    assert quality["atr_distance"] > 0


def test_volume_ratio_reflects_volume_surge():
    normal = compute_donchian_breakout_quality(_breakout_df(breakout_close=110.0, volume=1000.0), direction=1)
    surge = compute_donchian_breakout_quality(_breakout_df(breakout_close=110.0, volume=6000.0), direction=1)
    assert normal is not None and surge is not None
    assert surge["volume_ratio"] > normal["volume_ratio"]
    assert surge["volume_ratio"] == pytest.approx(6.0, rel=0.1)


def test_body_ratio_reflects_body_size():
    quality = compute_donchian_breakout_quality(_breakout_df(breakout_close=115.0), direction=1)
    assert quality is not None
    assert quality["body_ratio"] > 1.0  # kirilim mumu, sakin zemin ortalamasindan cok daha buyuk govdeli
