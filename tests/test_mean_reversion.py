"""signals/mean_reversion.py (DENEYSEL, bkz. config.py) icin sentetik veri testleri."""

from __future__ import annotations

import numpy as np
import pandas as pd

from signals.mean_reversion import compute_ibs, generate_signals


def _uptrend_with_pullback_df(pullback_bars: list[dict] | None = None) -> pd.DataFrame:
    """200+ barlik durgun bir yukselis trendi + (opsiyonel) ek sert-dusus barlari.

    SMA(200) filtresi anlamli test edilsin diye 250 bar uzunlugunda -
    diger testlerdeki kisa (25-40 bar) sentetik serilerden KASITLI farkli.
    """
    n = 250
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    close = 100 + np.arange(n) * 0.3
    df = pd.DataFrame(
        {
            "Open": close - 0.1,
            "High": close + 0.15,
            "Low": close - 0.15,
            "Close": close,
            "Volume": np.full(n, 1000.0),
        },
        index=dates,
    )
    if pullback_bars:
        start = dates[-1] + pd.tseries.offsets.BDay(1)
        extra_dates = pd.date_range(start, periods=len(pullback_bars), freq="B")
        extra = pd.DataFrame(pullback_bars, index=extra_dates)
        df = pd.concat([df, extra])[["Open", "High", "Low", "Close", "Volume"]]
    return df


def test_entry_long_fires_on_oversold_pullback_within_uptrend():
    base = _uptrend_with_pullback_df()
    last_close = float(base["Close"].iloc[-1])
    df = _uptrend_with_pullback_df(
        pullback_bars=[
            {"Open": last_close, "High": last_close + 0.2, "Low": last_close - 6.0, "Close": last_close - 5.8, "Volume": 5000.0},
            {"Open": last_close - 5.8, "High": last_close - 5.6, "Low": last_close - 9.0, "Close": last_close - 8.8, "Volume": 5000.0},
        ]
    )
    signals = generate_signals(df)
    assert bool(signals["entry_long"].iloc[-1]) is True
    # Close hala SMA(200)'un ustunde olmali (kucuk bir pullback, trend bozulmadi)
    sma200 = df["Close"].rolling(200).mean().iloc[-1]
    assert df["Close"].iloc[-1] > sma200


def test_entry_long_blocked_below_sma_trend():
    """Ayni sert dusus, ama SMA(200)'un ALTINDA (trend zaten asagi) -> giris YOK."""
    n = 250
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    close = 200 - np.arange(n) * 0.3  # DUSUS trendi
    df = pd.DataFrame(
        {"Open": close + 0.1, "High": close + 0.15, "Low": close - 0.15, "Close": close, "Volume": np.full(n, 1000.0)},
        index=dates,
    )
    last_close = float(df["Close"].iloc[-1])
    extra_dates = pd.date_range(dates[-1] + pd.tseries.offsets.BDay(1), periods=2, freq="B")
    extra = pd.DataFrame(
        {
            "Open": [last_close, last_close - 6.0],
            "High": [last_close + 0.2, last_close - 5.6],
            "Low": [last_close - 6.0, last_close - 9.0],
            "Close": [last_close - 5.8, last_close - 8.8],
            "Volume": [5000.0, 5000.0],
        },
        index=extra_dates,
    )
    df = pd.concat([df, extra])[["Open", "High", "Low", "Close", "Volume"]]
    signals = generate_signals(df)
    assert bool(signals["entry_long"].iloc[-1]) is False


def test_entry_short_never_fires():
    """LONG-only tasarim (bkz. modul docstring'i) - entry_short HER ZAMAN False."""
    df = _uptrend_with_pullback_df(
        pullback_bars=[{"Open": 100, "High": 100.5, "Low": 80.0, "Close": 81.0, "Volume": 9000.0}]
    )
    signals = generate_signals(df)
    assert not signals["entry_short"].any()


def test_exit_long_signal_fires_after_rsi_recovery():
    base = _uptrend_with_pullback_df()
    last_close = float(base["Close"].iloc[-1])
    df = _uptrend_with_pullback_df(
        pullback_bars=[
            {"Open": last_close, "High": last_close + 0.2, "Low": last_close - 6.0, "Close": last_close - 5.8, "Volume": 5000.0},
            # guclu toparlanma barlari -> RSI(2) tekrar >= 70
            {"Open": last_close - 5.8, "High": last_close + 2.0, "Low": last_close - 5.9, "Close": last_close + 1.5, "Volume": 5000.0},
            {"Open": last_close + 1.5, "High": last_close + 5.0, "Low": last_close + 1.4, "Close": last_close + 4.5, "Volume": 5000.0},
        ]
    )
    signals = generate_signals(df)
    assert bool(signals["exit_long_signal"].iloc[-1]) is True


def test_compute_ibs_handles_zero_range_bar():
    df = pd.DataFrame(
        {"Open": [100.0], "High": [100.0], "Low": [100.0], "Close": [100.0], "Volume": [1000.0]},
        index=pd.date_range("2020-01-01", periods=1),
    )
    ibs = compute_ibs(df)
    assert pd.isna(ibs.iloc[0])
