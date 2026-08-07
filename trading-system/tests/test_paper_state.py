"""paper_trading/state.py icin sentetik/ge cici SQLite dosyasiyla testler."""

from __future__ import annotations

import datetime as dt

import pytest

from paper_trading.state import (
    PaperTradingState,
    PositionAlreadyOpenError,
    PositionNotFoundError,
)


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "state.db"


def test_initial_equity_matches_configured_capital(db_path):
    state = PaperTradingState(db_path=db_path, initial_capital=10_000.0)
    assert state.get_equity() == 10_000.0
    state.close()


def test_open_and_get_position(db_path):
    state = PaperTradingState(db_path=db_path)
    state.open_position(
        "THYAO.IS", "donchian", direction=1, entry_date=dt.date(2024, 1, 10),
        entry_price=100.0, stop_price=95.0, size=20.0,
    )
    pos = state.get_position("THYAO.IS")
    assert pos is not None
    assert pos.symbol == "THYAO.IS"
    assert pos.direction == 1
    assert pos.entry_price == 100.0
    assert pos.stop_price == 95.0
    assert pos.size == 20.0
    assert pos.target_price is None
    state.close()


def test_get_position_returns_none_when_absent(db_path):
    state = PaperTradingState(db_path=db_path)
    assert state.get_position("NOPE.IS") is None
    state.close()


def test_open_position_twice_raises(db_path):
    state = PaperTradingState(db_path=db_path)
    state.open_position("BTC-USD", "donchian", 1, dt.date(2024, 1, 1), 50000.0, 48000.0, 0.01)
    with pytest.raises(PositionAlreadyOpenError):
        state.open_position("BTC-USD", "donchian", 1, dt.date(2024, 1, 2), 51000.0, 49000.0, 0.01)
    state.close()


def test_close_position_removes_it(db_path):
    state = PaperTradingState(db_path=db_path)
    state.open_position("BTC-USD", "donchian", 1, dt.date(2024, 1, 1), 50000.0, 48000.0, 0.01)
    state.close_position("BTC-USD")
    assert state.get_position("BTC-USD") is None
    state.close()


def test_close_nonexistent_position_raises(db_path):
    state = PaperTradingState(db_path=db_path)
    with pytest.raises(PositionNotFoundError):
        state.close_position("NOPE.IS")
    state.close()


def test_multiple_symbols_independent_positions(db_path):
    state = PaperTradingState(db_path=db_path)
    state.open_position("THYAO.IS", "donchian", 1, dt.date(2024, 1, 1), 100.0, 95.0, 10.0)
    state.open_position("BTC-USD", "donchian", -1, dt.date(2024, 1, 1), 50000.0, 52000.0, 0.01)
    positions = state.list_open_positions()
    assert {p.symbol for p in positions} == {"THYAO.IS", "BTC-USD"}
    state.close()


def test_equity_adjust_roundtrip(db_path):
    state = PaperTradingState(db_path=db_path, initial_capital=10_000.0)
    new_equity = state.adjust_equity(-50.0)
    assert new_equity == 9_950.0
    assert state.get_equity() == 9_950.0
    state.adjust_equity(200.0)
    assert state.get_equity() == 10_150.0
    state.close()


def test_last_processed_date_roundtrip(db_path):
    state = PaperTradingState(db_path=db_path)
    assert state.get_last_processed_date("THYAO.IS") is None
    state.set_last_processed_date("THYAO.IS", dt.date(2024, 3, 5))
    assert state.get_last_processed_date("THYAO.IS") == dt.date(2024, 3, 5)
    # ayni sembol icin ikinci kez set etmek (UPSERT) guncellemeli
    state.set_last_processed_date("THYAO.IS", dt.date(2024, 3, 6))
    assert state.get_last_processed_date("THYAO.IS") == dt.date(2024, 3, 6)
    state.close()


def test_state_persists_across_instances(db_path):
    """Programi 'kapatip acinca' (yeni bir PaperTradingState orneginde) pozisyon korunmali."""
    state1 = PaperTradingState(db_path=db_path, initial_capital=10_000.0)
    state1.open_position("THYAO.IS", "donchian", 1, dt.date(2024, 1, 10), 100.0, 95.0, 20.0)
    state1.adjust_equity(-5.0)
    state1.set_last_processed_date("THYAO.IS", dt.date(2024, 1, 10))
    state1.close()

    state2 = PaperTradingState(db_path=db_path, initial_capital=10_000.0)
    pos = state2.get_position("THYAO.IS")
    assert pos is not None
    assert pos.entry_price == 100.0
    assert state2.get_equity() == 9_995.0
    assert state2.get_last_processed_date("THYAO.IS") == dt.date(2024, 1, 10)
    state2.close()


def test_read_only_without_existing_file_does_not_touch_disk(db_path):
    assert not db_path.exists()
    state = PaperTradingState(db_path=db_path, initial_capital=10_000.0, read_only=True)
    # Bellek-ici fallback yine de tutarli "taze" degerler dondurmeli
    assert state.get_equity() == 10_000.0
    assert state.get_position("THYAO.IS") is None
    assert state.list_open_positions() == []
    state.close()
    assert not db_path.exists()  # diske hicbir sey yazilmamis olmali


def test_read_only_with_existing_file_reads_real_state(db_path):
    writer = PaperTradingState(db_path=db_path, initial_capital=10_000.0)
    writer.open_position("THYAO.IS", "donchian", 1, dt.date(2024, 1, 10), 100.0, 95.0, 20.0)
    writer.close()

    reader = PaperTradingState(db_path=db_path, initial_capital=10_000.0, read_only=True)
    pos = reader.get_position("THYAO.IS")
    assert pos is not None
    assert pos.entry_price == 100.0
    reader.close()


def test_backup_creates_timestamped_copy_with_same_data(db_path, tmp_path):
    state = PaperTradingState(db_path=db_path, initial_capital=10_000.0)
    state.open_position("BTC-USD", "donchian", 1, dt.date(2024, 1, 1), 50000.0, 48000.0, 0.01)

    backup_path = state.backup()
    assert backup_path is not None
    assert backup_path.exists()
    assert backup_path.parent == db_path.parent / "backups"

    backup_state = PaperTradingState(db_path=backup_path, initial_capital=10_000.0)
    pos = backup_state.get_position("BTC-USD")
    assert pos is not None
    assert pos.entry_price == 50000.0
    backup_state.close()
    state.close()


def test_backup_returns_none_for_in_memory_state(db_path):
    state = PaperTradingState(db_path=db_path, initial_capital=10_000.0, read_only=True)
    assert state.backup() is None
    state.close()
