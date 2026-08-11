"""gozcu/psychology.py icin testler."""

from __future__ import annotations

import numpy as np

from gozcu import psychology


def test_compute_breadth_pct_basic():
    changes = [0.01, -0.02, 0.03, None, 0.0]
    # gecerli 4 degerden 2'si pozitif (0.0 pozitif sayilmaz)
    assert np.isclose(psychology.compute_breadth_pct(changes), 50.0)


def test_compute_breadth_pct_none_when_no_data():
    assert psychology.compute_breadth_pct([None, None]) is None


def test_compute_volatility_regime_thresholds():
    assert psychology.compute_volatility_regime([0.001, -0.001]) == "normal"
    assert psychology.compute_volatility_regime([0.025, -0.025]) == "yuksek"
    assert psychology.compute_volatility_regime([0.05, -0.05]) == "asiri"


def test_compute_volatility_regime_unknown_when_no_data():
    assert psychology.compute_volatility_regime([None]) == "bilinmiyor"
