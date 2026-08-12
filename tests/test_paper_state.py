"""paper_trading/state.py icin sentetik/gecici SQLite dosyasiyla testler."""

from __future__ import annotations

import datetime as dt
import sqlite3

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
    pos = state.get_position("THYAO.IS", "donchian")
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
    assert state.get_position("NOPE.IS", "donchian") is None
    state.close()


def test_open_position_twice_same_strategy_raises(db_path):
    state = PaperTradingState(db_path=db_path)
    state.open_position("BTC-USD", "donchian", 1, dt.date(2024, 1, 1), 50000.0, 48000.0, 0.01)
    with pytest.raises(PositionAlreadyOpenError):
        state.open_position("BTC-USD", "donchian", 1, dt.date(2024, 1, 2), 51000.0, 49000.0, 0.01)
    state.close()


def test_open_position_same_symbol_different_strategy_allowed(db_path):
    """M3: coklu strateji ayni sembolde PARALEL pozisyon tutabilmeli."""
    state = PaperTradingState(db_path=db_path)
    state.open_position("EREGL.IS", "donchian", 1, dt.date(2024, 1, 1), 100.0, 95.0, 10.0)
    state.open_position("EREGL.IS", "ma_voting", -1, dt.date(2024, 1, 1), 100.0, 105.0, 5.0)
    donchian_pos = state.get_position("EREGL.IS", "donchian")
    ma_voting_pos = state.get_position("EREGL.IS", "ma_voting")
    assert donchian_pos is not None and donchian_pos.direction == 1
    assert ma_voting_pos is not None and ma_voting_pos.direction == -1
    state.close()


def test_close_position_removes_it(db_path):
    state = PaperTradingState(db_path=db_path)
    state.open_position("BTC-USD", "donchian", 1, dt.date(2024, 1, 1), 50000.0, 48000.0, 0.01)
    state.close_position("BTC-USD", "donchian")
    assert state.get_position("BTC-USD", "donchian") is None
    state.close()


def test_close_position_does_not_affect_other_strategy(db_path):
    state = PaperTradingState(db_path=db_path)
    state.open_position("EREGL.IS", "donchian", 1, dt.date(2024, 1, 1), 100.0, 95.0, 10.0)
    state.open_position("EREGL.IS", "ma_voting", -1, dt.date(2024, 1, 1), 100.0, 105.0, 5.0)
    state.close_position("EREGL.IS", "donchian")
    assert state.get_position("EREGL.IS", "donchian") is None
    assert state.get_position("EREGL.IS", "ma_voting") is not None
    state.close()


def test_close_nonexistent_position_raises(db_path):
    state = PaperTradingState(db_path=db_path)
    with pytest.raises(PositionNotFoundError):
        state.close_position("NOPE.IS", "donchian")
    state.close()


def test_multiple_symbols_independent_positions(db_path):
    state = PaperTradingState(db_path=db_path)
    state.open_position("THYAO.IS", "donchian", 1, dt.date(2024, 1, 1), 100.0, 95.0, 10.0)
    state.open_position("BTC-USD", "donchian", -1, dt.date(2024, 1, 1), 50000.0, 52000.0, 0.01)
    positions = state.list_open_positions()
    assert {p.symbol for p in positions} == {"THYAO.IS", "BTC-USD"}
    state.close()


def test_list_open_positions_filters_by_strategy(db_path):
    state = PaperTradingState(db_path=db_path)
    state.open_position("THYAO.IS", "donchian", 1, dt.date(2024, 1, 1), 100.0, 95.0, 10.0)
    state.open_position("EREGL.IS", "ma_voting", 1, dt.date(2024, 1, 1), 50.0, 45.0, 10.0)
    donchian_only = state.list_open_positions(strategy="donchian")
    assert {p.symbol for p in donchian_only} == {"THYAO.IS"}
    all_positions = state.list_open_positions()
    assert {p.symbol for p in all_positions} == {"THYAO.IS", "EREGL.IS"}
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
    assert state.get_last_processed_date("THYAO.IS", "donchian") is None
    state.set_last_processed_date("THYAO.IS", "donchian", dt.date(2024, 3, 5))
    assert state.get_last_processed_date("THYAO.IS", "donchian") == dt.date(2024, 3, 5)
    # ayni (sembol, strateji) icin ikinci kez set etmek (UPSERT) guncellemeli
    state.set_last_processed_date("THYAO.IS", "donchian", dt.date(2024, 3, 6))
    assert state.get_last_processed_date("THYAO.IS", "donchian") == dt.date(2024, 3, 6)
    state.close()


def test_last_processed_date_independent_per_strategy(db_path):
    """M3: ayni sembolde iki strateji ayni gun BAGIMSIZ islenebilmeli (idempotency carpismasin)."""
    state = PaperTradingState(db_path=db_path)
    state.set_last_processed_date("THYAO.IS", "donchian", dt.date(2024, 3, 5))
    assert state.get_last_processed_date("THYAO.IS", "ma_voting") is None
    state.close()


def test_stop_warning_date_roundtrip(db_path):
    state = PaperTradingState(db_path=db_path)
    assert state.get_stop_warning_date("EREGL.IS", "donchian") is None
    state.set_stop_warning_date("EREGL.IS", "donchian", dt.date(2024, 3, 5))
    assert state.get_stop_warning_date("EREGL.IS", "donchian") == dt.date(2024, 3, 5)
    # ayni (sembol, strateji) icin ikinci kez set etmek (UPSERT) guncellemeli
    state.set_stop_warning_date("EREGL.IS", "donchian", dt.date(2024, 3, 6))
    assert state.get_stop_warning_date("EREGL.IS", "donchian") == dt.date(2024, 3, 6)
    state.close()


def test_close_position_clears_stop_warning_date(db_path):
    state = PaperTradingState(db_path=db_path)
    state.open_position("BTC-USD", "donchian", 1, dt.date(2024, 1, 1), 50000.0, 48000.0, 0.01)
    state.set_stop_warning_date("BTC-USD", "donchian", dt.date(2024, 1, 5))
    state.close_position("BTC-USD", "donchian")
    assert state.get_stop_warning_date("BTC-USD", "donchian") is None
    state.close()


def test_state_persists_across_instances(db_path):
    """Programi 'kapatip acinca' (yeni bir PaperTradingState orneginde) pozisyon korunmali."""
    state1 = PaperTradingState(db_path=db_path, initial_capital=10_000.0)
    state1.open_position("THYAO.IS", "donchian", 1, dt.date(2024, 1, 10), 100.0, 95.0, 20.0)
    state1.adjust_equity(-5.0)
    state1.set_last_processed_date("THYAO.IS", "donchian", dt.date(2024, 1, 10))
    state1.close()

    state2 = PaperTradingState(db_path=db_path, initial_capital=10_000.0)
    pos = state2.get_position("THYAO.IS", "donchian")
    assert pos is not None
    assert pos.entry_price == 100.0
    assert state2.get_equity() == 9_995.0
    assert state2.get_last_processed_date("THYAO.IS", "donchian") == dt.date(2024, 1, 10)
    state2.close()


def test_read_only_without_existing_file_does_not_touch_disk(db_path):
    assert not db_path.exists()
    state = PaperTradingState(db_path=db_path, initial_capital=10_000.0, read_only=True)
    # Bellek-ici fallback yine de tutarli "taze" degerler dondurmeli
    assert state.get_equity() == 10_000.0
    assert state.get_position("THYAO.IS", "donchian") is None
    assert state.list_open_positions() == []
    state.close()
    assert not db_path.exists()  # diske hicbir sey yazilmamis olmali


def test_read_only_with_existing_file_reads_real_state(db_path):
    writer = PaperTradingState(db_path=db_path, initial_capital=10_000.0)
    writer.open_position("THYAO.IS", "donchian", 1, dt.date(2024, 1, 10), 100.0, 95.0, 20.0)
    writer.close()

    reader = PaperTradingState(db_path=db_path, initial_capital=10_000.0, read_only=True)
    pos = reader.get_position("THYAO.IS", "donchian")
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
    pos = backup_state.get_position("BTC-USD", "donchian")
    assert pos is not None
    assert pos.entry_price == 50000.0
    backup_state.close()
    state.close()


def test_backup_returns_none_for_in_memory_state(db_path):
    state = PaperTradingState(db_path=db_path, initial_capital=10_000.0, read_only=True)
    assert state.backup() is None
    state.close()


# -- Semi migrasyonu (M3: eski tek-symbol-PK semadan kompozit anahtara) -----


def test_migration_preserves_existing_position_and_backfills_strategy(db_path):
    """Eski semadaki (symbol PK) gercek bir pozisyon, migrasyon sonrasi
    (symbol, strategy) ile erisilebilir olmali - hicbir veri kaybolmamali."""
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """
        CREATE TABLE account (id INTEGER PRIMARY KEY CHECK (id = 1), equity REAL NOT NULL);
        INSERT INTO account (id, equity) VALUES (1, 9998.62);

        CREATE TABLE positions (
            symbol TEXT PRIMARY KEY,
            strategy TEXT NOT NULL,
            direction INTEGER NOT NULL,
            entry_date TEXT NOT NULL,
            entry_price REAL NOT NULL,
            stop_price REAL NOT NULL,
            target_price REAL,
            size REAL NOT NULL
        );
        INSERT INTO positions VALUES
            ('EREGL.IS', 'donchian', -1, '2026-08-07', 38.66, 41.72, NULL, 32.73);

        CREATE TABLE symbol_run_state (
            symbol TEXT PRIMARY KEY,
            last_processed_date TEXT NOT NULL
        );
        INSERT INTO symbol_run_state VALUES ('EREGL.IS', '2026-08-11');

        CREATE TABLE stop_warnings (
            symbol TEXT PRIMARY KEY,
            warned_date TEXT NOT NULL
        );
        INSERT INTO stop_warnings VALUES ('EREGL.IS', '2026-08-10');
        """
    )
    conn.commit()
    conn.close()

    state = PaperTradingState(db_path=db_path, initial_capital=10_000.0)

    assert state.get_equity() == 9998.62
    pos = state.get_position("EREGL.IS", "donchian")
    assert pos is not None
    assert pos.direction == -1
    assert pos.entry_price == 38.66
    assert state.get_last_processed_date("EREGL.IS", "donchian") == dt.date(2026, 8, 11)
    assert state.get_stop_warning_date("EREGL.IS", "donchian") == dt.date(2026, 8, 10)

    # Migrasyon sonrasi yeni bir strateji ayni sembolde bagimsiz calisabilmeli
    state.open_position("EREGL.IS", "ma_voting", 1, dt.date(2026, 8, 12), 40.0, 38.0, 5.0)
    assert state.get_position("EREGL.IS", "ma_voting") is not None
    assert state.get_position("EREGL.IS", "donchian") is not None  # eski pozisyon hala duruyor
    state.close()


def test_migration_is_idempotent_on_reopen(db_path):
    """Migrasyon zaten yapilmis bir db'yi tekrar acmak hata vermemeli/veri bozmamali."""
    state1 = PaperTradingState(db_path=db_path, initial_capital=10_000.0)
    state1.open_position("THYAO.IS", "donchian", 1, dt.date(2024, 1, 1), 100.0, 95.0, 10.0)
    state1.close()

    state2 = PaperTradingState(db_path=db_path, initial_capital=10_000.0)
    assert state2.get_position("THYAO.IS", "donchian") is not None
    state2.close()
