"""Paper trading icin kalici (SQLite) state: acik pozisyonlar, sanal hesap
sermayesi, ve idempotency icin sembol basina "son islenen tarih".

SQLite tercih edildi (JSON degil): ayni state dosyasina yaziurken islem
yarida kesilirse (crash, guc kesintisi) JSON tek bir buyuk yazma islemidir
ve bozulabilir; SQLite WAL modu + tek satirlik UPDATE/INSERT/DELETE
komutlari atomik oldugundan es zamanlilik ve yarim-yazma riskine karsi
daha dayaniklidir.

Kisitlar:
- Sembol basina EN FAZLA 1 acik pozisyon (positions.symbol PRIMARY KEY +
  open_position()'daki acik kontrol).
- symbol_run_state, runner.py'nin ayni gun icinde birden fazla
  calistirilmasinda ayni sinyali iki kere islememesini saglar
  (bkz. paper_trading/runner.py IDEMPOTENCY notu).
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from config import PAPER_TRADING_INITIAL_CAPITAL, PAPER_TRADING_STATE_DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS account (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    equity REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS positions (
    symbol TEXT PRIMARY KEY,
    strategy TEXT NOT NULL,
    direction INTEGER NOT NULL,
    entry_date TEXT NOT NULL,
    entry_price REAL NOT NULL,
    stop_price REAL NOT NULL,
    target_price REAL,
    size REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS symbol_run_state (
    symbol TEXT PRIMARY KEY,
    last_processed_date TEXT NOT NULL
);
"""


class PositionAlreadyOpenError(RuntimeError):
    """Bir sembol icin zaten acik pozisyon varken yeni pozisyon acilmaya calisildi."""


class PositionNotFoundError(RuntimeError):
    """Acik pozisyonu olmayan bir sembol kapatilmaya calisildi."""


@dataclass
class PositionRecord:
    """Kalici olarak saklanan acik pozisyonun bellek-ici temsili."""

    symbol: str
    strategy: str
    direction: int  # +1 long, -1 short
    entry_date: dt.date
    entry_price: float
    stop_price: float
    size: float
    target_price: float | None = None


class PaperTradingState:
    """Paper trading hesabinin SQLite-destekli kalici durumu.

    Ayni db_path'e isaret eden birden fazla PaperTradingState ornegi
    (orn. programi kapatip yeniden acmak, ya da ayri bir process) ayni
    kalici veriyi gorur - state bir dosyada tutulur, process bellegi
    degil.

    read_only=True (runner.py'de --dry-run tarafindan kullanilir) ve
    db_path'te henuz bir dosya YOKSA, diske hicbir sey yazilmaz: bunun
    yerine bellek-ici (sqlite ":memory:") gecici bir state acilir - "hicbir
    state degisikligi yapmadan ne yapacagini goster" sozu boylece ilk
    calistirmada bile tutulur. db_path zaten mevcutsa (daha once gercek bir
    calistirma yapilmissa), read_only=True yine de o dosyayi acar (mevcut
    pozisyonlari gormek icin gerekli) - runner.py bu modda hicbir yazma
    metodunu cagirmadigindan dosya degismeden kalir.
    """

    def __init__(
        self,
        db_path: str | Path = PAPER_TRADING_STATE_DB_PATH,
        initial_capital: float = PAPER_TRADING_INITIAL_CAPITAL,
        read_only: bool = False,
    ) -> None:
        self.db_path = Path(db_path)
        self.read_only = read_only
        self._in_memory = read_only and not self.db_path.exists()

        if self._in_memory:
            self._conn = sqlite3.connect(":memory:")
        else:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.execute("PRAGMA journal_mode=WAL")

        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        self._ensure_account(initial_capital)

    def _ensure_account(self, initial_capital: float) -> None:
        row = self._conn.execute("SELECT equity FROM account WHERE id = 1").fetchone()
        if row is None:
            self._conn.execute("INSERT INTO account (id, equity) VALUES (1, ?)", (initial_capital,))
            self._conn.commit()

    # -- Hesap sermayesi -----------------------------------------------

    def get_equity(self) -> float:
        """Guncel (gerceklesmis/realized) sanal hesap sermayesini dondurur."""
        row = self._conn.execute("SELECT equity FROM account WHERE id = 1").fetchone()
        return float(row[0])

    def set_equity(self, value: float) -> None:
        """Hesap sermayesini dogrudan belirtilen degere ayarlar."""
        self._conn.execute("UPDATE account SET equity = ? WHERE id = 1", (value,))
        self._conn.commit()

    def adjust_equity(self, delta: float) -> float:
        """Hesap sermayesine delta ekler (islem PnL'i/komisyonu icin) ve yeni degeri dondurur."""
        new_value = self.get_equity() + delta
        self.set_equity(new_value)
        return new_value

    # -- Pozisyonlar ------------------------------------------------------

    def get_position(self, symbol: str) -> PositionRecord | None:
        """Bir sembol icin acik pozisyon varsa dondurur, yoksa None."""
        row = self._conn.execute(
            "SELECT symbol, strategy, direction, entry_date, entry_price, stop_price, target_price, size "
            "FROM positions WHERE symbol = ?",
            (symbol,),
        ).fetchone()
        if row is None:
            return None
        return _row_to_position(row)

    def list_open_positions(self) -> list[PositionRecord]:
        """Tum acik pozisyonlari sembol adina gore sirali dondurur."""
        rows = self._conn.execute(
            "SELECT symbol, strategy, direction, entry_date, entry_price, stop_price, target_price, size "
            "FROM positions ORDER BY symbol"
        ).fetchall()
        return [_row_to_position(row) for row in rows]

    def open_position(
        self,
        symbol: str,
        strategy: str,
        direction: int,
        entry_date: dt.date,
        entry_price: float,
        stop_price: float,
        size: float,
        target_price: float | None = None,
    ) -> None:
        """Yeni bir pozisyon acar.

        Raises:
            PositionAlreadyOpenError: symbol icin zaten acik bir pozisyon varsa
                (sembol basina en fazla 1 pozisyon kurali).
        """
        if self.get_position(symbol) is not None:
            raise PositionAlreadyOpenError(f"{symbol} icin zaten acik pozisyon var")
        self._conn.execute(
            "INSERT INTO positions "
            "(symbol, strategy, direction, entry_date, entry_price, stop_price, target_price, size) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (symbol, strategy, direction, entry_date.isoformat(), entry_price, stop_price, target_price, size),
        )
        self._conn.commit()

    def close_position(self, symbol: str) -> None:
        """Bir sembolun acik pozisyonunu siler.

        Raises:
            PositionNotFoundError: symbol icin acik pozisyon yoksa.
        """
        cur = self._conn.execute("DELETE FROM positions WHERE symbol = ?", (symbol,))
        self._conn.commit()
        if cur.rowcount == 0:
            raise PositionNotFoundError(f"{symbol} icin acik pozisyon bulunamadi")

    # -- Idempotency: sembol basina son islenen bar tarihi -----------------

    def get_last_processed_date(self, symbol: str) -> dt.date | None:
        """Bu sembol icin en son islenmis sinyal barinin tarihini dondurur (yoksa None)."""
        row = self._conn.execute(
            "SELECT last_processed_date FROM symbol_run_state WHERE symbol = ?", (symbol,)
        ).fetchone()
        if row is None:
            return None
        return dt.date.fromisoformat(row[0])

    def set_last_processed_date(self, symbol: str, date_value: dt.date) -> None:
        """Bu sembol icin son islenen sinyal bari tarihini kalici olarak kaydeder."""
        self._conn.execute(
            "INSERT INTO symbol_run_state (symbol, last_processed_date) VALUES (?, ?) "
            "ON CONFLICT(symbol) DO UPDATE SET last_processed_date = excluded.last_processed_date",
            (symbol, date_value.isoformat()),
        )
        self._conn.commit()

    # -- Yedekleme ------------------------------------------------------

    def backup(self, backup_dir: str | Path | None = None) -> Path | None:
        """state.db'nin zaman damgali, tutarli bir yedegini alir.

        SQLite'in yerlesik backup API'si (Connection.backup) kullanilir -
        basit dosya kopyalamanin aksine, WAL modunda henuz ana .db dosyasina
        checkpoint edilmemis commit'leri de dogru sekilde yakalar. Eski
        yedekleri otomatik silme YOK (gorev kapsaminda istenmedi).

        Args:
            backup_dir: Yedeklerin yazilacagi dizin (varsayilan:
                db_path'in yaninda "backups/" alt dizini).

        Returns:
            Olusturulan yedek dosyasinin yolu; bellek-ici (dry-run,
            henuz hic gercek state.db yokken) state icin None (yedeklenecek
            bir dosya yok).
        """
        if self._in_memory:
            return None

        target_dir = Path(backup_dir) if backup_dir is not None else self.db_path.parent / "backups"
        target_dir.mkdir(parents=True, exist_ok=True)
        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = target_dir / f"{self.db_path.stem}_{timestamp}.db"

        dest_conn = sqlite3.connect(str(backup_path))
        try:
            self._conn.backup(dest_conn)
        finally:
            dest_conn.close()
        return backup_path

    # -- Yasam dongusu ------------------------------------------------------

    def close(self) -> None:
        """Alttaki veritabani baglantisini kapatir."""
        self._conn.close()

    def __enter__(self) -> "PaperTradingState":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def _row_to_position(row: tuple) -> PositionRecord:
    symbol, strategy, direction, entry_date, entry_price, stop_price, target_price, size = row
    return PositionRecord(
        symbol=symbol,
        strategy=strategy,
        direction=int(direction),
        entry_date=dt.date.fromisoformat(entry_date),
        entry_price=float(entry_price),
        stop_price=float(stop_price),
        size=float(size),
        target_price=float(target_price) if target_price is not None else None,
    )
