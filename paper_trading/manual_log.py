"""paper_trading/manual_log.py - kullanicinin sistem sinyaline karsi GERCEKTEN
(kendi hesabindan, manuel) actigi islemlerin kaydi.

Bu modul HICBIR sekilde gercek bir borsa/aracı kurum API'siyle konusmaz;
yalnizca "bu sinyali aldim, gercek giris fiyatim/miktarim su" seklinde
kullanicinin kendi elle girdigi notu kalici olarak saklar
(paper_trading/logs/manual_trades.jsonl). Sistemin kendi (sanal)
trades.jsonl'inden BAGIMSIZDIR - amac, sistemin onerdigi fiyat ile
kullanicinin gercekte aldigi fiyat arasindaki farki (slipaj) sonradan
(dashboard'da) karsilastirabilmek.

Dashboard (Next.js) bu dosyayi KENDI TARAFINDA (TypeScript) ayni JSONL
semasiyla okuyup yaziyor - bkz. dashboard/lib/manualLog.ts. Bu modul,
Python tarafindan (test, CLI, gelecekte otomatik raporlama) ayni kaydi
tutarli sekilde okuyup yazabilmek icin var; iki taraf da MANUAL_LOG_COLUMNS
semasina birebir uymalidir.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from config import PAPER_TRADING_MANUAL_LOG_PATH

MANUAL_LOG_COLUMNS: list[str] = [
    "symbol",
    "signal_date",  # sistemin sinyal tarihi (trades.jsonl'deki "date" ile eslesir)
    "system_entry_price",  # sistemin onerdigi giris fiyati (varsa, referans icin)
    "user_entry_price",  # kullanicinin gercekte girdigi fiyat
    "user_size",  # kullanicinin gercekte aldigi miktar
    "note",
    "marked_at",  # bu kaydin olusturuldugu zaman damgasi (ISO datetime, UTC)
]


def record_manual_entry(
    symbol: str,
    signal_date: dt.date,
    user_entry_price: float,
    user_size: float,
    system_entry_price: float | None = None,
    note: str = "",
    log_path: str | Path = PAPER_TRADING_MANUAL_LOG_PATH,
) -> dict:
    """Bir manuel islem kaydini log_path'e (JSONL, append-only) ekler.

    Args:
        symbol: Islem sembolu (orn. "EREGL.IS").
        signal_date: Sistemin bu islem icin sinyal urettigi tarih.
        user_entry_price: Kullanicinin gercekte girdigi fiyat.
        user_size: Kullanicinin gercekte aldigi miktar.
        system_entry_price: Sistemin onerdigi giris fiyati (varsa; slipaj
            hesaplamasi icin kullanilir - bkz. slippage_pct).
        note: Serbest metin not (opsiyonel).
        log_path: Kaydin yazilacagi JSONL dosyasi.

    Returns:
        Yazilan kaydin sozluk hali (marked_at dahil).
    """
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "symbol": symbol,
        "signal_date": signal_date.isoformat(),
        "system_entry_price": system_entry_price,
        "user_entry_price": user_entry_price,
        "user_size": user_size,
        "note": note,
        "marked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def read_manual_entries(log_path: str | Path = PAPER_TRADING_MANUAL_LOG_PATH) -> list[dict]:
    """log_path'teki tum manuel islem kayitlarini okur.

    Args:
        log_path: Okunacak JSONL dosyasi.

    Returns:
        Kayit sozlukleri listesi; dosya yoksa (henuz hic isaretleme
        yapilmamis) bos liste.
    """
    path = Path(log_path)
    if not path.exists():
        return []
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def slippage_pct(record: dict) -> float | None:
    """Sistem onerisi ile kullanicinin gercek giris fiyati arasindaki farki
    yuzde olarak hesaplar.

    Args:
        record: record_manual_entry() ile uretilmis (veya ayni semaya sahip)
            bir kayit sozlugu.

    Returns:
        (user_entry_price - system_entry_price) / system_entry_price.
        system_entry_price yoksa/0 ise veya user_entry_price yoksa None.
    """
    system_price = record.get("system_entry_price")
    user_price = record.get("user_entry_price")
    if system_price is None or system_price == 0 or user_price is None:
        return None
    return (user_price - system_price) / system_price
