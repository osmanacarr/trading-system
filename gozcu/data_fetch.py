"""gozcu/data_fetch.py - GOZCU icin toplu (batched) yfinance veri cekme.

data/fetch.py'deki fetch_ohlcv/fetch_universe TEK sembol basina bir
yf.download cagirisi yapar (paper trading'in kucuk, sabit evreni icin
yeterli). GOZCU yuzlerce sembolu ayni ~5 dakikalik pencerede taradigi icin
sembol basina ayri istek atmak hem cok yavas hem de Yahoo/yfinance
tarafinda rate-limit riskini artirir. Bu modul bunun yerine COKLU sembolu
TEK yf.download cagrisinda (buyuk evrenlerde parcalar halinde) ceker.

data/fetch.py'nin OHLCV_COLUMNS sabitini ve "veri yoksa/hata olursa bos
DataFrame don, hicbir zaman istisna firlatma" felsefesini yeniden kullanir.
Gunluk barlar icin data/adjust.py'nin sicrama-duzeltme fonksiyonunu da
yeniden kullanir (bkz. fetch_daily_batch).
"""

from __future__ import annotations

import logging

import pandas as pd
import yfinance as yf

from config import GOZCU_DAILY_LOOKBACK_DAYS, GOZCU_INTRADAY_INTERVAL, GOZCU_INTRADAY_LOOKBACK_DAYS
from data.adjust import adjust_jumps
from data.fetch import OHLCV_COLUMNS

log = logging.getLogger("gozcu.data_fetch")

DEFAULT_CHUNK_SIZE = 100


def _empty_frames(tickers: list[str]) -> dict[str, pd.DataFrame]:
    return {t: pd.DataFrame(columns=OHLCV_COLUMNS) for t in tickers}


def _clean_single_ticker_frame(raw: pd.DataFrame) -> pd.DataFrame:
    if raw is None or raw.empty:
        return pd.DataFrame(columns=OHLCV_COLUMNS)
    missing = [c for c in OHLCV_COLUMNS if c not in raw.columns]
    if missing:
        return pd.DataFrame(columns=OHLCV_COLUMNS)
    df = raw[OHLCV_COLUMNS].copy()
    df.index.name = "Date"
    return df.dropna(subset=["Open", "High", "Low", "Close"])


def _fetch_chunk(
    tickers: list[str],
    start: str | None,
    end: str | None,
    interval: str,
    period: str | None,
) -> dict[str, pd.DataFrame]:
    kwargs: dict = dict(
        tickers=tickers,
        interval=interval,
        auto_adjust=True,
        progress=False,
        group_by="ticker",
        threads=True,
    )
    if period is not None:
        kwargs["period"] = period
    else:
        kwargs["start"] = start
        kwargs["end"] = end

    try:
        raw = yf.download(**kwargs)
    except Exception:
        log.warning("Toplu yfinance cagrisi basarisiz (%d sembol), bu parca atlaniyor", len(tickers))
        return _empty_frames(tickers)

    if raw is None or raw.empty:
        return _empty_frames(tickers)

    result: dict[str, pd.DataFrame] = {}
    is_multi = isinstance(raw.columns, pd.MultiIndex)
    available = set(raw.columns.get_level_values(0)) if is_multi else set()
    for ticker in tickers:
        try:
            if is_multi:
                sub = raw[ticker] if ticker in available else None
            else:
                sub = raw if len(tickers) == 1 else None
            result[ticker] = _clean_single_ticker_frame(sub) if sub is not None else pd.DataFrame(columns=OHLCV_COLUMNS)
        except Exception:
            result[ticker] = pd.DataFrame(columns=OHLCV_COLUMNS)
    return result


def fetch_ohlcv_batch(
    tickers: list[str],
    start: str | None = None,
    end: str | None = None,
    interval: str = "1d",
    period: str | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> dict[str, pd.DataFrame]:
    """Birden fazla sembolu, parcalar halinde TOPLU yf.download cagrilariyla ceker.

    Args:
        tickers: yfinance sembol listesi.
        start/end: "YYYY-MM-DD" tarih araligi (period verilmezse kullanilir).
        interval: yfinance interval kodu.
        period: yfinance period kodu (orn. "5d"); verilirse start/end yerine kullanilir.
        chunk_size: Tek bir yf.download cagrisinda istenecek maksimum sembol
            sayisi. Cok buyuk tek istekler Yahoo tarafinda daha kolay
            basarisiz/kisitlanir; parcalamak bir parca basarisiz olsa bile
            digerlerinin sonuc vermesini saglar.

    Returns:
        {ticker: OHLCV DataFrame} sozlugu. Cekilemeyen/hata alan semboller
        icin bos DataFrame atanir, istisna firlatilmaz.
    """
    if not tickers:
        return {}

    result: dict[str, pd.DataFrame] = {}
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i : i + chunk_size]
        result.update(_fetch_chunk(chunk, start=start, end=end, interval=interval, period=period))
    return result


def fetch_daily_batch(tickers: list[str], chunk_size: int = DEFAULT_CHUNK_SIZE) -> dict[str, pd.DataFrame]:
    """Gunluk (1d) barlar, config.GOZCU_DAILY_LOOKBACK_DAYS kadar geriye donuk.

    data.adjust.adjust_jumps() ile YENIDEN KULLANILARAK %40+ sahte fiyat
    sicramalari (yfinance'in yakalayamadigi bedelli/bedelsiz sermaye
    artirimi vb. kurumsal aksiyonlar) geriye donuk duzeltilir - aksi halde
    boyle bir sicrama, GOZCU'nun dikkat skorunda gercek bir hareketmis gibi
    en tepeye cikardi (canli testte GMSTR.IS'te gozlemlendi, bkz. README).
    """
    raw = fetch_ohlcv_batch(
        tickers,
        interval="1d",
        period=f"{GOZCU_DAILY_LOOKBACK_DAYS}d",
        chunk_size=chunk_size,
    )
    return {ticker: adjust_jumps(df) for ticker, df in raw.items()}


def fetch_intraday_batch(tickers: list[str], chunk_size: int = DEFAULT_CHUNK_SIZE) -> dict[str, pd.DataFrame]:
    """Gun ici (config.GOZCU_INTRADAY_INTERVAL) barlar, GOZCU_INTRADAY_LOOKBACK_DAYS kadar geriye donuk."""
    return fetch_ohlcv_batch(
        tickers,
        interval=GOZCU_INTRADAY_INTERVAL,
        period=f"{GOZCU_INTRADAY_LOOKBACK_DAYS}d",
        chunk_size=chunk_size,
    )
