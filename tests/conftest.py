"""Testler icin ortak sentetik OHLCV veri uretim yardimcilari."""

from __future__ import annotations

import numpy as np
import pandas as pd


def make_flat_range_df(
    n: int = 40,
    price: float = 100.0,
    half_range: float = 1.0,
    volume: float = 1_000.0,
    start: str = "2020-01-01",
) -> pd.DataFrame:
    """Dar bir aralikta yatay seyreden (range) sentetik OHLCV verisi uretir.

    Deterministiktir (rastgelelik yok); breakout/filtre testleri icin
    "kirilim oncesi durgun zemin" olarak kullanilir.
    """
    dates = pd.date_range(start, periods=n, freq="B")
    # +-half_range araliginda kucuk, deterministik bir salinim
    offsets = np.array([((-1) ** i) * (half_range * 0.3) for i in range(n)])
    close = price + offsets
    open_ = np.roll(close, 1)
    open_[0] = price
    high = np.maximum(open_, close) + half_range * 0.2
    low = np.minimum(open_, close) - half_range * 0.2
    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, volume),
        },
        index=dates,
    )


def append_bars(
    base: pd.DataFrame,
    bars: list[dict],
) -> pd.DataFrame:
    """base'in ardina, is gunu takvimiyle devam eden ek barlar ekler.

    Her eleman {"Open","High","Low","Close","Volume"} anahtarlarina sahip
    bir sozluk olmalidir.
    """
    start = base.index[-1] + pd.tseries.offsets.BDay(1)
    dates = pd.date_range(start, periods=len(bars), freq="B")
    extra = pd.DataFrame(bars, index=dates)
    return pd.concat([base, extra])[["Open", "High", "Low", "Close", "Volume"]]
