"""Faktor gecmisi biriktirme - Modul 2 (sistematik arastirma mimarisi).

research/factors.py'deki (ve istenirse disaridan gelen herhangi bir)
faktorlerin her hesaplamada uretilen TUM degerlerini (sadece en sonuncusunu
degil) UZUN FORMATTA (date, symbol, factor_name, value) research/data/
factor_history.parquet dosyasina ekler. Bu birikim, validation/
alpha_evaluation.py'nin (Modul 3) IC/decay hesaplamalari ve research/
ensemble.py'nin (Modul 5) korelasyon analizi icin ham veridir.

MIMARI KARAR: bu modul GOZCU'nun tarama dongusune (gozcu/scanner.py)
KANCALANMAZ - gozcu/scanner.py'ye dokunulmadi, boylece GOZCU'nun mevcut
davranisi/testleri risk altina girmedi. Bunun yerine kendi bagimsiz
toplama fonksiyonu (`collect_factor_history`) vardir ve backtest/paper
trading ile AYNI stabil evreni (config.BIST_TICKERS + config.CRYPTO_TICKERS)
kullanir - GOZCU'nun genis/kesifsel "dikkat taramasi" evreninden BILEREK
farklidir (research, GOZCU'nun "hangi sembole bakmali" isini degil,
"zaten takip ettigimiz enstrumanlarda faktorler gercekten isliyor mu"
sorusunu cevaplar).

Atomic yazma: gozcu/scanner.py::_write_snapshot_atomic ile AYNI desen
(tmp dosya + Path.replace) - parquet icin de yarim-yazma riskine karsi.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from config import CRYPTO_TICKERS, BIST_TICKERS, RESEARCH_FACTOR_HISTORY_PATH
from data.fetch import fetch_universe
from research.factors import FACTOR_REGISTRY

log = logging.getLogger("research.factor_history")

LONG_FORMAT_COLUMNS: list[str] = ["date", "symbol", "factor_name", "value"]


def _normalize_date(date) -> pd.Timestamp:
    return pd.Timestamp(date).normalize()


def load_factor_history(path: Path = RESEARCH_FACTOR_HISTORY_PATH) -> pd.DataFrame:
    """Biriktirilmis faktor gecmisini okur. Dosya yoksa bos (dogru kolonlu) DataFrame doner."""
    if not path.exists():
        return pd.DataFrame(columns=LONG_FORMAT_COLUMNS)
    df = pd.read_parquet(path)
    return df[LONG_FORMAT_COLUMNS]


def _write_parquet_atomic(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    df.to_parquet(tmp_path, index=False)
    tmp_path.replace(path)


def append_factor_history(
    new_rows: pd.DataFrame, path: Path = RESEARCH_FACTOR_HISTORY_PATH
) -> pd.DataFrame:
    """Uzun-format yeni satirlari mevcut parquet'e ekler (oku+concat+dedupe+atomic-yaz).

    Ayni (date, symbol, factor_name) ucluye sahip bir satir zaten varsa,
    YENI deger eskisinin USTUNE yazilir (idempotent - ayni gun icin tarama
    tekrar calistirilirsa veri katlanmaz).

    Args:
        new_rows: LONG_FORMAT_COLUMNS kolonlarina sahip DataFrame.
        path: Hedef parquet yolu.

    Returns:
        Guncel (birlestirilmis) tam tarihce DataFrame'i.
    """
    missing = [c for c in LONG_FORMAT_COLUMNS if c not in new_rows.columns]
    if missing:
        raise ValueError(f"new_rows icinde eksik kolon(lar): {missing}")

    new_rows = new_rows.copy()
    new_rows["date"] = pd.to_datetime(new_rows["date"]).dt.normalize()

    existing = load_factor_history(path)
    combined = pd.concat([existing, new_rows[LONG_FORMAT_COLUMNS]], ignore_index=True)
    combined = combined.drop_duplicates(
        subset=["date", "symbol", "factor_name"], keep="last"
    )
    combined = combined.sort_values(["date", "symbol", "factor_name"]).reset_index(drop=True)

    _write_parquet_atomic(combined, path)
    return combined


def append_factor_values(
    date,
    symbol: str,
    factor_values: dict[str, float],
    path: Path = RESEARCH_FACTOR_HISTORY_PATH,
) -> pd.DataFrame:
    """Tek bir (tarih, sembol) icin bir grup faktor degerini biriktirir.

    Args:
        date: Tarih (str/Timestamp/date - gun cozunurlugune normalize edilir).
        symbol: Sembol adi.
        factor_values: {faktor_adi: deger} sozlugu.
        path: Hedef parquet yolu.
    """
    normalized_date = _normalize_date(date)
    rows = pd.DataFrame(
        {
            "date": [normalized_date] * len(factor_values),
            "symbol": [symbol] * len(factor_values),
            "factor_name": list(factor_values.keys()),
            "value": list(factor_values.values()),
        }
    )
    return append_factor_history(rows, path=path)


def compute_symbol_factor_row(
    symbol: str, df: pd.DataFrame, date=None
) -> pd.DataFrame:
    """Tek bir sembol icin FACTOR_REGISTRY'deki TUM faktorleri hesaplayip uzun-format satirlar uretir.

    Yetersiz veri/hesaplama hatasi olan faktorler NaN olarak KAYDEDILIR
    (sessizce atlanmaz) - "TUM degerleri biriktir" gereksinimine sadik
    kalinir; NaN'lari eleme sorumlulugu tuketen taraftadir (orn. IC
    hesaplamasi).
    """
    if df.empty:
        resolved_date = _normalize_date(date) if date is not None else pd.NaT
    else:
        resolved_date = _normalize_date(date) if date is not None else df.index[-1]

    values: dict[str, float] = {}
    for name, factor_fn in FACTOR_REGISTRY.items():
        try:
            values[name] = factor_fn(df, date=date)
        except Exception:
            log.exception("Faktor hesaplanamadi: %s / %s", symbol, name)
            values[name] = float("nan")

    return pd.DataFrame(
        {
            "date": [resolved_date] * len(values),
            "symbol": [symbol] * len(values),
            "factor_name": list(values.keys()),
            "value": list(values.values()),
        }
    )


def collect_factor_history(
    symbols: list[str],
    daily_data: dict[str, pd.DataFrame],
    date=None,
    path: Path = RESEARCH_FACTOR_HISTORY_PATH,
) -> pd.DataFrame:
    """Verilen sembol evreni icin TUM faktorleri hesaplayip TEK seferde parquet'e ekler.

    Her sembol icin ayri ayri append yerine, tum sembollerin satirlari
    birlestirilip TEK bir append_factor_history cagrisiyla yazilir
    (N kez degil 1 kez oku+yaz - N sembol icin performans).

    Args:
        symbols: Sembol listesi.
        daily_data: {symbol: OHLCV DataFrame} - data.fetch.fetch_universe ciktisi.
        date: Faktorlerin hesaplanacagi tarih (None ise her sembolun kendi
            son barı kullanılır).
        path: Hedef parquet yolu.
    """
    all_rows = [
        compute_symbol_factor_row(symbol, daily_data.get(symbol, pd.DataFrame()), date=date)
        for symbol in symbols
    ]
    if not all_rows:
        return load_factor_history(path)
    combined_new = pd.concat(all_rows, ignore_index=True)
    combined_new = combined_new.dropna(subset=["date"])  # bos df -> tarih yok, atla
    if combined_new.empty:
        return load_factor_history(path)
    return append_factor_history(combined_new, path=path)


def run_daily_collection(
    lookback_days: int = 400, path: Path = RESEARCH_FACTOR_HISTORY_PATH
) -> pd.DataFrame:
    """CLI/scheduled-run giris noktasi: stabil evren (BIST+kripto) icin veri ceker ve biriktirir."""
    symbols = list(BIST_TICKERS) + list(CRYPTO_TICKERS)
    end = pd.Timestamp.today().normalize()
    start = (end - pd.Timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    daily_data = fetch_universe(symbols, start=start)
    return collect_factor_history(symbols, daily_data, path=path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_daily_collection()
    log.info("Faktor gecmisi guncellendi: %d satir (toplam)", len(result))
