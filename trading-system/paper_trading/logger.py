"""Paper trading islem/equity kayitlari + dashboard-hazir ozet.

Ciktilar (hepsi paper_trading/logs/ altinda, dogal olarak kalici/append-only):
- trades.jsonl / trades.csv  : her giris/cikis olayi icin bir kayit
- equity.jsonl / equity.csv  : her runner.py calistirmasinda bir gunluk
                                sermaye anlik-goruntusu (snapshot)
- summary.json                : dashboard'un dogrudan okuyabilecegi, HER
                                calistirmada UZERINE YAZILAN kucuk ozet
                                (en son equity, acik pozisyon sayisi,
                                son 7 gunun islem sayisi)

Hem CSV hem JSONL yazilir: JSONL programatik/dashboard tuketimi icin daha
saglam (satir bazli, append-friendly, iс ice alan gerekmiyor); CSV, Excel'de
acilip hizli goz atmak icin. Sutun adlari iki formatta da AYNIDIR.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd

from config import PAPER_TRADING_LOG_DIR

TRADE_LOG_COLUMNS: list[str] = [
    "event_type",  # "entry" | "exit"
    "date",  # ISO tarih (YYYY-MM-DD) - sinyal barinin tarihi
    "symbol",
    "strategy",
    "direction",  # 1 (long) / -1 (short)
    "price",  # entry: entry_price; exit: exit_price (fiil, slipaj dahil)
    "stop_price",
    "target_price",  # yalnizca price_action icin dolu, donchian'da None
    "size",
    "pnl",  # yalnizca exit event'inde dolu (net, komisyon dahil)
    "r_multiple",  # yalnizca exit event'inde dolu
    "exit_reason",  # yalnizca exit event'inde dolu: stop | trailing | target
    "equity_after",  # bu olaydan hemen sonraki hesap sermayesi (realized)
]

EQUITY_LOG_COLUMNS: list[str] = [
    "date",
    "realized_equity",
    "unrealized_pnl",
    "total_equity",
    "open_positions",
]


class PaperTradingLogger:
    """Trade/equity kayitlarini CSV+JSONL'e yazan ve dashboard ozetini
    guncelleyen basit, bagimliliksiz (stdlib) logger."""

    def __init__(self, log_dir: str | Path = PAPER_TRADING_LOG_DIR) -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.trades_jsonl_path = self.log_dir / "trades.jsonl"
        self.trades_csv_path = self.log_dir / "trades.csv"
        self.equity_jsonl_path = self.log_dir / "equity.jsonl"
        self.equity_csv_path = self.log_dir / "equity.csv"
        self.summary_json_path = self.log_dir / "summary.json"

    def log_trade(self, event: dict) -> None:
        """Bir giris/cikis olayini trades.jsonl + trades.csv'ye ekler.

        Args:
            event: TRADE_LOG_COLUMNS'daki anahtarlarin bir alt kumesini/tamamini
                iceren sozluk (eksik anahtarlar None olarak yazilir). Degerler
                zaten JSON/CSV-uyumlu ilkel tipler olmalidir (orn. tarih icin
                "YYYY-MM-DD" string'i, pd.Timestamp/dt.date DEGIL).
        """
        record = {col: event.get(col) for col in TRADE_LOG_COLUMNS}
        _append_jsonl(self.trades_jsonl_path, record)
        _append_csv(self.trades_csv_path, TRADE_LOG_COLUMNS, record)

    def log_equity_snapshot(self, snapshot: dict) -> None:
        """Bir gunluk equity anlik-goruntusunu equity.jsonl + equity.csv'ye ekler."""
        record = {col: snapshot.get(col) for col in EQUITY_LOG_COLUMNS}
        _append_jsonl(self.equity_jsonl_path, record)
        _append_csv(self.equity_csv_path, EQUITY_LOG_COLUMNS, record)

    def update_summary(self, summary: dict) -> None:
        """summary.json'i (tamamen) UZERINE YAZAR - dashboard'un okuyacagi son durum."""
        self.summary_json_path.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def read_trades(self) -> pd.DataFrame:
        """trades.jsonl'i bir DataFrame olarak okur (rapor uretimi icin)."""
        if not self.trades_jsonl_path.exists():
            return pd.DataFrame(columns=TRADE_LOG_COLUMNS)
        records = _read_jsonl(self.trades_jsonl_path)
        if not records:
            return pd.DataFrame(columns=TRADE_LOG_COLUMNS)
        df = pd.DataFrame(records, columns=TRADE_LOG_COLUMNS)
        df["date"] = pd.to_datetime(df["date"])
        return df

    def read_equity(self) -> pd.DataFrame:
        """equity.jsonl'i bir DataFrame olarak okur (rapor uretimi icin)."""
        if not self.equity_jsonl_path.exists():
            return pd.DataFrame(columns=EQUITY_LOG_COLUMNS)
        records = _read_jsonl(self.equity_jsonl_path)
        if not records:
            return pd.DataFrame(columns=EQUITY_LOG_COLUMNS)
        df = pd.DataFrame(records, columns=EQUITY_LOG_COLUMNS)
        df["date"] = pd.to_datetime(df["date"])
        return df


def _append_jsonl(path: Path, record: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _append_csv(path: Path, columns: list[str], record: dict) -> None:
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        if write_header:
            writer.writeheader()
        writer.writerow(record)


def _read_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records
