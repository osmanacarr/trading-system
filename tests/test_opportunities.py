"""paper_trading/opportunities.py icin sentetik veriyle testler."""

from __future__ import annotations

import datetime as dt
import json

from paper_trading import opportunities
from tests.conftest import append_bars, make_flat_range_df

RUN_DATE = dt.date(2026, 8, 12)


def _breakout_df(breakout_close: float, volume: float = 1000.0) -> "object":
    base = make_flat_range_df(n=30, price=100.0, half_range=1.0, volume=1000.0)
    bar = {"Open": 101.0, "High": breakout_close + 1.0, "Low": 100.5, "Close": breakout_close, "Volume": volume}
    return append_bars(base, [bar])


def _rejected(symbol="THYAO.IS", strategy="donchian", direction=1, breakout_close=110.0, reason="test") -> opportunities.RejectedCandidate:
    return opportunities.RejectedCandidate(
        symbol=symbol, strategy=strategy, direction=direction, entry_price=breakout_close,
        stop_price=breakout_close - 5.0, signal_date=RUN_DATE, reason=reason,
        df=_breakout_df(breakout_close),
    )


def test_build_opportunities_ranks_by_atr_distance_descending():
    weak = _rejected(symbol="A.IS", breakout_close=103.0)
    strong = _rejected(symbol="B.IS", breakout_close=118.0)
    entries = opportunities.build_opportunities([weak, strong])
    assert [e.symbol for e in entries] == ["B.IS", "A.IS"]


def test_build_opportunities_excludes_non_donchian_strategies():
    non_donchian = _rejected(symbol="C.IS", strategy="ma_voting")
    entries = opportunities.build_opportunities([non_donchian])
    assert entries == []


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
