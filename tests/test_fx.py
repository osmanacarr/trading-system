"""data/fx.py icin sentetik veri testleri."""

from __future__ import annotations

import numpy as np
import pandas as pd

from data.fx import convert_to_usd


def _tl_df(n: int = 5) -> pd.DataFrame:
    dates = pd.date_range("2022-01-03", periods=n, freq="B")
    close = np.full(n, 300.0)
    return pd.DataFrame(
        {
            "Open": close,
            "High": close + 5,
            "Low": close - 5,
            "Close": close,
            "Volume": np.full(n, 1000.0),
        },
        index=dates,
    )


def test_convert_to_usd_flat_rate():
    df_tl = _tl_df(5)
    rate = pd.Series(30.0, index=df_tl.index, name="USDTRY")
    usd = convert_to_usd(df_tl, rate)
    assert np.allclose(usd["Close"], 10.0)
    assert np.allclose(usd["Open"], 10.0)
    assert np.allclose(usd["High"], (df_tl["High"] / 30.0).values)


def test_convert_to_usd_ffill_alignment():
    df_tl = _tl_df(5)
    # USDTRY sadece ilk gun icin mevcut -> geri kalanlar ffill ile doldurulmali
    rate = pd.Series([25.0], index=[df_tl.index[0]], name="USDTRY")
    usd = convert_to_usd(df_tl, rate)
    assert np.allclose(usd["Close"], 300.0 / 25.0)


def test_convert_to_usd_empty_rate_returns_unchanged():
    df_tl = _tl_df(3)
    empty_rate = pd.Series(dtype=float, name="USDTRY")
    usd = convert_to_usd(df_tl, empty_rate)
    pd.testing.assert_frame_equal(usd, df_tl)
