"""paper_trading/logger.py ve paper_trading/report.py icin testler."""

from __future__ import annotations

import datetime as dt
import json

from paper_trading.logger import PaperTradingLogger
from paper_trading.report import generate_weekly_report
from paper_trading.state import PaperTradingState


def _sample_trade_event(event_type="exit", pnl=50.0, r_multiple=1.0, date="2024-01-10"):
    return {
        "event_type": event_type,
        "date": date,
        "symbol": "FAKE-USD",
        "strategy": "donchian",
        "direction": 1,
        "price": 105.0,
        "stop_price": 95.0,
        "target_price": None,
        "size": 10.0,
        "pnl": pnl if event_type == "exit" else None,
        "r_multiple": r_multiple if event_type == "exit" else None,
        "exit_reason": "trailing" if event_type == "exit" else None,
        "equity_after": 10_050.0,
    }


def test_log_trade_writes_csv_and_jsonl(tmp_path):
    logger = PaperTradingLogger(log_dir=tmp_path)
    logger.log_trade(_sample_trade_event())

    assert logger.trades_jsonl_path.exists()
    assert logger.trades_csv_path.exists()

    with logger.trades_jsonl_path.open() as f:
        record = json.loads(f.readline())
    assert record["symbol"] == "FAKE-USD"
    assert record["pnl"] == 50.0


def test_log_trade_appends_multiple_records(tmp_path):
    logger = PaperTradingLogger(log_dir=tmp_path)
    logger.log_trade(_sample_trade_event(event_type="entry", date="2024-01-05"))
    logger.log_trade(_sample_trade_event(event_type="exit", date="2024-01-10"))

    df = logger.read_trades()
    assert len(df) == 2
    assert list(df["event_type"]) == ["entry", "exit"]


def test_log_equity_snapshot_roundtrip(tmp_path):
    logger = PaperTradingLogger(log_dir=tmp_path)
    logger.log_equity_snapshot(
        {"date": "2024-01-10", "realized_equity": 10_000.0, "unrealized_pnl": 25.0, "total_equity": 10_025.0, "open_positions": 1}
    )
    df = logger.read_equity()
    assert len(df) == 1
    assert df.iloc[0]["total_equity"] == 10_025.0


def test_update_summary_overwrites_json(tmp_path):
    logger = PaperTradingLogger(log_dir=tmp_path)
    logger.update_summary({"total_equity": 10_000.0, "open_positions": 0})
    logger.update_summary({"total_equity": 10_500.0, "open_positions": 2})

    data = json.loads(logger.summary_json_path.read_text())
    assert data["total_equity"] == 10_500.0
    assert data["open_positions"] == 2


def test_read_trades_empty_when_no_file(tmp_path):
    logger = PaperTradingLogger(log_dir=tmp_path)
    df = logger.read_trades()
    assert df.empty


def test_generate_weekly_report_with_open_position_and_trades(tmp_path):
    state = PaperTradingState(db_path=tmp_path / "state.db", initial_capital=10_000.0)
    state.open_position("FAKE-USD", "donchian", 1, dt.date(2024, 1, 12), 105.0, 95.0, 10.0)

    logger = PaperTradingLogger(log_dir=tmp_path / "logs")
    logger.log_trade(_sample_trade_event(event_type="exit", pnl=50.0, r_multiple=1.5, date="2024-01-10"))
    logger.log_equity_snapshot(
        {"date": "2024-01-12", "realized_equity": 10_050.0, "unrealized_pnl": 0.0, "total_equity": 10_050.0, "open_positions": 1}
    )

    report = generate_weekly_report(state, logger, as_of=dt.date(2024, 1, 14), initial_capital=10_000.0)

    assert "FAKE-USD" in report
    assert "10,050.00" in report
    assert "Win rate" in report
    state.close()


def test_generate_weekly_report_empty_state(tmp_path):
    state = PaperTradingState(db_path=tmp_path / "state.db", initial_capital=10_000.0)
    logger = PaperTradingLogger(log_dir=tmp_path / "logs")

    report = generate_weekly_report(state, logger, as_of=dt.date(2024, 1, 14), initial_capital=10_000.0)

    assert "Acik pozisyon yok" in report
    assert "Henuz kapanan islem yok" in report
    state.close()
