"""paper_trading/opportunities.py icin sentetik veriyle testler."""

from __future__ import annotations

import datetime as dt
import json

import numpy as np
import pandas as pd

from paper_trading import opportunities
from tests.conftest import append_bars, make_flat_range_df

RUN_DATE = dt.date(2026, 8, 12)


def _breakout_df(breakout_close: float, volume: float = 1000.0) -> "object":
    base = make_flat_range_df(n=30, price=100.0, half_range=1.0, volume=1000.0)
    bar = {"Open": 101.0, "High": breakout_close + 1.0, "Low": 100.5, "Close": breakout_close, "Volume": volume}
    return append_bars(base, [bar])


def _mean_reversion_df() -> pd.DataFrame:
    """test_mean_reversion.py::_uptrend_with_pullback_df ile AYNI desen -
    RSI(2) hesaplanabilir olsun diye 200+ barlik uzun bir seri gerekir."""
    n = 250
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    close = 100 + np.arange(n) * 0.3
    df = pd.DataFrame(
        {"Open": close - 0.1, "High": close + 0.15, "Low": close - 0.15, "Close": close, "Volume": np.full(n, 1000.0)},
        index=dates,
    )
    lc = float(df["Close"].iloc[-1])
    return append_bars(
        df,
        [
            {"Open": lc, "High": lc + 0.2, "Low": lc - 6.0, "Close": lc - 5.8, "Volume": 5000.0},
            {"Open": lc - 5.8, "High": lc - 5.7, "Low": lc - 9.0, "Close": lc - 8.8, "Volume": 5000.0},
        ],
    )


def _rejected(symbol="THYAO.IS", strategy="donchian", direction=1, breakout_close=110.0, reason="test") -> opportunities.RejectedCandidate:
    df = _mean_reversion_df() if strategy == "mean_reversion" else _breakout_df(breakout_close)
    return opportunities.RejectedCandidate(
        symbol=symbol, strategy=strategy, direction=direction, entry_price=breakout_close,
        stop_price=breakout_close - 5.0, signal_date=RUN_DATE, reason=reason,
        df=df,
    )


def test_build_opportunities_ranks_by_atr_distance_descending():
    weak = _rejected(symbol="A.IS", breakout_close=103.0)
    strong = _rejected(symbol="B.IS", breakout_close=118.0)
    entries = opportunities.build_opportunities([weak, strong])
    assert [e.symbol for e in entries] == ["B.IS", "A.IS"]


def test_build_opportunities_excludes_unsupported_strategies():
    unsupported = _rejected(symbol="C.IS", strategy="ma_voting")
    entries = opportunities.build_opportunities([unsupported])
    assert entries == []


def test_build_opportunities_includes_mean_reversion_with_own_ranking():
    mr = _rejected(symbol="AAPL", strategy="mean_reversion", breakout_close=100.0)
    donchian = _rejected(symbol="THYAO.IS", strategy="donchian", breakout_close=110.0)
    entries = opportunities.build_opportunities([mr, donchian])

    by_symbol = {e.symbol: e for e in entries}
    assert set(by_symbol) == {"AAPL", "THYAO.IS"}

    mr_entry = by_symbol["AAPL"]
    assert mr_entry.strategy == "mean_reversion"
    assert mr_entry.validation_status == "deneysel"
    assert mr_entry.rsi_oversold_depth is not None
    assert mr_entry.atr_distance is None  # donchian-only alan, mean_reversion'da None olmali

    donchian_entry = by_symbol["THYAO.IS"]
    assert donchian_entry.validation_status == "dogrulanmis"
    assert donchian_entry.atr_distance is not None
    assert donchian_entry.rsi_oversold_depth is None  # mean_reversion-only alan


def test_build_opportunities_top_n_applies_per_strategy_separately():
    """Her strateji KENDI top_n'ini alir - havuzlanmis TEK bir sinir DEGIL
    (bkz. modul docstring'i madde 2, farkli olcekleri karistirmama ilkesi)."""
    donchian_candidates = [_rejected(symbol=f"D{i}.IS", breakout_close=105.0 + i) for i in range(5)]
    mr_candidates = [_rejected(symbol=f"MR{i}", strategy="mean_reversion", breakout_close=100.0) for i in range(5)]
    entries = opportunities.build_opportunities(donchian_candidates + mr_candidates, top_n=2)

    donchian_entries = [e for e in entries if e.strategy == "donchian"]
    mr_entries = [e for e in entries if e.strategy == "mean_reversion"]
    assert len(donchian_entries) == 2
    assert len(mr_entries) == 2


def test_build_opportunities_respects_top_n():
    candidates = [_rejected(symbol=f"S{i}.IS", breakout_close=105.0 + i) for i in range(8)]
    entries = opportunities.build_opportunities(candidates, top_n=3)
    assert len(entries) == 3


def test_build_opportunities_preserves_rejection_reason():
    reason = "Korelasyon kumesi zaten dolu (bu kumede baska pozisyon(lar) var)"
    entries = opportunities.build_opportunities([_rejected(reason=reason)])
    assert entries[0].rejection_reason == reason


def test_build_opportunities_applicable_flag_follows_direction():
    long_entry = opportunities.build_opportunities([_rejected(direction=1)])[0]
    short_entry = opportunities.build_opportunities([_rejected(symbol="X.IS", direction=-1)])[0]
    assert long_entry.applicable is True
    assert short_entry.applicable is False  # USER_CAN_SHORT=False varsayilani (bkz. config.py)


def test_write_opportunities_json_roundtrip(tmp_path):
    entries = opportunities.build_opportunities([_rejected()])
    out_path = opportunities.write_opportunities_json(entries, RUN_DATE, path=tmp_path / "opportunities.json")
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["run_date"] == RUN_DATE.isoformat()
    assert data["risk_warning"] == opportunities.RISK_WARNING
    assert len(data["entries"]) == 1
    assert data["entries"][0]["symbol"] == "THYAO.IS"


def test_write_opportunities_json_empty_list_when_nothing_rejected(tmp_path):
    out_path = opportunities.write_opportunities_json([], RUN_DATE, path=tmp_path / "opportunities.json")
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["entries"] == []
