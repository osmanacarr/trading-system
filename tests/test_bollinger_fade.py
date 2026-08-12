"""signals/bollinger_fade.py icin sentetik veri testleri (M5 - Kart 3)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from signals import bollinger_fade
from tests.conftest import append_bars


def _choppy_base(n: int = 60, amplitude: float = 0.5, period_bars: int = 10) -> pd.DataFrame:
    """Genuine (sinus) dusuk-ADX zemin - make_flat_range_df BURADA
    KULLANILMAZ (bkz. tests/test_regime.py'deki ayni gerekce: o fixture'in
    High/Low'u bar-bar sabit kalir, bu ADX icin dejenere/gercekci-olmayan
    bir girdidir)."""
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    t = np.arange(n)
    close = 100.0 + amplitude * np.sin(2 * np.pi * t / period_bars)
    high = close + 0.2
    low = close - 0.2
    open_ = np.roll(close, 1)
    open_[0] = 100.0
    volume = np.full(n, 1000.0)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=dates)


def _fade_long_setup_df(mag: float = 2.0) -> pd.DataFrame:
    """Dusuk-ADX zemin + kisa/keskin bir dusus + boga onay mumu - Kart 3'un
    TUM long kosullarini (bant altina inis, RSI asiri-satim, boga mumu,
    ADX<esik) ayni anda saglayacak sekilde KALIBRE edilmis (bkz. M5 rapor -
    genis mag degerleri ADX'i esigin USTUNE cikarip filtreyi haklı olarak
    devreye sokuyor, bu yuzden mag=2.0 kucuk/orta buyuklukte tutuldu)."""
    base = _choppy_base()
    drop_bar = {"Open": 100.0, "High": 100.1, "Low": 100.0 - mag - 0.3, "Close": 100.0 - mag, "Volume": 2000.0}
    confirm_bar = {
        "Open": 100.0 - mag, "High": 100.0 - mag + 0.8, "Low": 100.0 - mag - 0.2,
        "Close": 100.0 - mag + 0.5, "Volume": 2000.0,
    }
    return append_bars(base, [drop_bar, confirm_bar])


def _fade_short_setup_df(mag: float = 2.0) -> pd.DataFrame:
    base = _choppy_base()
    spike_bar = {"Open": 100.0, "High": 100.0 + mag + 0.3, "Low": 99.9, "Close": 100.0 + mag, "Volume": 2000.0}
    confirm_bar = {
        "Open": 100.0 + mag, "High": 100.0 + mag + 0.2, "Low": 100.0 + mag - 0.8,
        "Close": 100.0 + mag - 0.5, "Volume": 2000.0,
    }
    return append_bars(base, [spike_bar, confirm_bar])


_SIG_KWARGS = dict(band_period=20, band_atr_period=14, band_mult=1.0, stop_atr_period=14, rsi_period=5, adx_period=14)


def test_compute_bands_keltner_ordering():
    df = _choppy_base()
    bands = bollinger_fade.compute_bands(df, band_type="keltner", period=20, atr_period=14, mult=1.0)
    valid = bands.dropna()
    assert not valid.empty
    assert (valid["band_upper"] > valid["band_middle"]).all()
    assert (valid["band_middle"] > valid["band_lower"]).all()


def test_compute_bands_bollinger_ordering():
    df = _choppy_base()
    bands = bollinger_fade.compute_bands(df, band_type="bollinger", period=20, mult=2.0)
    valid = bands.dropna()
    assert not valid.empty
    assert (valid["band_upper"] > valid["band_middle"]).all()
    assert (valid["band_middle"] > valid["band_lower"]).all()


def test_compute_bands_invalid_band_type_raises():
    df = _choppy_base()
    with pytest.raises(ValueError):
        bollinger_fade.compute_bands(df, band_type="nonsense")


def test_entry_long_fires_when_all_conditions_align():
    df = _fade_long_setup_df(mag=2.0)
    sig = bollinger_fade.generate_signals(df, band_type="keltner", **_SIG_KWARGS)
    row = sig.iloc[-1]
    assert bool(row["entry_long"]) is True
    assert bool(row["entry_short"]) is False
    assert row["adx"] < 20.0


def test_entry_short_fires_when_all_conditions_align():
    df = _fade_short_setup_df(mag=2.0)
    sig = bollinger_fade.generate_signals(df, band_type="keltner", **_SIG_KWARGS)
    row = sig.iloc[-1]
    assert bool(row["entry_short"]) is True
    assert bool(row["entry_long"]) is False
    assert row["adx"] < 20.0


def test_entry_blocked_when_adx_above_threshold_despite_band_and_rsi():
    """Ayni band-asimi/RSI-asiri-satim kosullari, GUCLU bir hareketten
    (ADX esigi asan) kaynaklaniyorsa giris ENGELLENMELI - Kart 3'un
    "sadece dusuk-ADX'te aktif" filtresinin asil amaci budur."""
    df = _fade_long_setup_df(mag=5.0)
    sig = bollinger_fade.generate_signals(df, band_type="keltner", **_SIG_KWARGS)
    row = sig.iloc[-1]
    assert row["adx"] >= 20.0  # varsayimi dogrula: bu senaryoda ADX gercekten esigi asiyor
    assert bool(row["entry_long"]) is False


def test_stop_long_below_lower_band_by_atr_fraction():
    df = _fade_long_setup_df(mag=2.0)
    sig = bollinger_fade.generate_signals(df, band_type="keltner", stop_atr_mult=0.5, **_SIG_KWARGS)
    bands = bollinger_fade.compute_bands(df, band_type="keltner", period=20, atr_period=14, mult=1.0)
    row = sig.iloc[-1]
    assert row["stop_long"] < bands["band_lower"].iloc[-1]


def test_stop_short_above_upper_band_by_atr_fraction():
    df = _fade_short_setup_df(mag=2.0)
    sig = bollinger_fade.generate_signals(df, band_type="keltner", stop_atr_mult=0.5, **_SIG_KWARGS)
    bands = bollinger_fade.compute_bands(df, band_type="keltner", period=20, atr_period=14, mult=1.0)
    row = sig.iloc[-1]
    assert row["stop_short"] > bands["band_upper"].iloc[-1]


def test_target_equals_middle_band():
    df = _fade_long_setup_df(mag=2.0)
    sig = bollinger_fade.generate_signals(df, band_type="keltner", **_SIG_KWARGS)
    bands = bollinger_fade.compute_bands(df, band_type="keltner", period=20, atr_period=14, mult=1.0)
    row = sig.iloc[-1]
    assert np.isclose(row["target_long"], bands["band_middle"].iloc[-1])
    assert np.isclose(row["target_short"], bands["band_middle"].iloc[-1])


def test_missing_columns_raises():
    with pytest.raises(ValueError):
        bollinger_fade.generate_signals(pd.DataFrame({"Close": [1.0, 2.0]}))
