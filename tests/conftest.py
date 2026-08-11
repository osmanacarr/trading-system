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


def build_donchian_trailing_exit_df() -> pd.DataFrame:
    """Kirilim + trend + trailing-exit tetikleyen ters donus iceren sentetik seri.

    tests/test_engine.py ve tests/test_regime.py TARAFINDAN PAYLASILIR
    (ayni "en az bir Donchian islemi ureten" senaryoyu iki yerde
    YENIDEN YAZMAMAK icin buraya tasindi).
    """
    base = make_flat_range_df(n=25, price=100.0, half_range=1.0, volume=1000.0)
    breakout = {"Open": 101.0, "High": 116.0, "Low": 100.5, "Close": 115.0, "Volume": 6000.0}
    uptrend = [
        {"Open": 115.0 + 3 * i + 2, "High": 115.0 + 3 * i + 4, "Low": 115.0 + 3 * i, "Close": 115.0 + 3 * i + 3, "Volume": 1200.0}
        for i in range(12)
    ]
    reversal = {"Open": 140.0, "High": 141.0, "Low": 115.0, "Close": 116.0, "Volume": 1000.0}
    return append_bars(base, [breakout] + uptrend + [reversal])
