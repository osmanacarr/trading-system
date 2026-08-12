"""paper_trading/runner.py - gunluk paper trading calistiricisi.

Her sembol icin (TUM aktif stratejiler PAYLASIR - sembol basina veri BIR
KEZ cekilir):
    en guncel veriyi cek (3 deneme + exponential backoff) ->
    her aktif strateji icin sinyal uret (backtest ile AYNI signals.*
    fonksiyonlari) ->
    acik pozisyon VARSA (o strateji icin): stop/trailing kontrolu (tetiklenirse
    HEMEN kapat - exit risk AZALTIR, portfoy tahsisini beklemez) ->
    acik pozisyon YOKSA ve giris sinyali VARSA: HENUZ ACMA, bir
    EntryCandidate olarak biriktir.

PORTFOY TAHSISI (M3 - coklu strateji + evren genisletme ile eklendi):
Tum sembol x strateji taramasi bittikten SONRA, gunun tum yeni giris
adaylari TEK SEFERDE degerlendirilir: mevcut acik pozisyonlarin (tum
stratejiler) tukettigi brut maruziyet hesaplanir, kalan risk butcesi
risk.portfolio.optimize_portfolio ile (getiri-korelasyonu kumelerine gore
kisitlanarak - bkz. risk/correlation_clusters.py) adaylara PAYLASTIRILIR.
Bu adim OLMADAN evren genisletmesi (13 -> ~yuzlerce sembol) devreye
girmez: kontrolsuz genis evren + yonetilmeyen korelasyon riski, ayni
trend gununde onlarca korelasyonlu sembolde es zamanli giris anlamina
gelip brut kaldiraci fiilen anlamsizlastirabilirdi.

GECICI SKOR (M6'dan ONCE): adaylar arasi onceliklendirme su an sadece
yon isaretiyle ESIT agirlik kullaniyor (research.ensemble.composite_score
HENUZ baglanmadi - factor_history yeterince birikmeden IC-agirlikli skoru
guvenilirmis gibi sunmamak icin bilincli bir ara adim, bkz. M6).

IDEMPOTENCY: Her (sembol, strateji) cifti icin islenen son bar'in tarihi
state'e yazilir (PaperTradingState.set_last_processed_date). Runner ayni
gun icinde tekrar calistirilirsa, veri kaynagindaki en guncel bar hala
ayni oldugundan (signal_date degismez), o (sembol, strateji) cifti "zaten
islendi" olarak atlanir.

DAYANIKLILIK: Bir sembolde veri cekme kalici olarak basarisiz olursa
(3 deneme sonrasi) o sembol (TUM stratejiler icin) atlanir ve loglanir;
calisma DURMAZ, digerlerine devam edilir.

Kullanim:
    python -m paper_trading.runner --strategies donchian
    python -m paper_trading.runner --strategies donchian price_action
    python -m paper_trading.runner --strategies donchian --dry-run
    python -m paper_trading.runner --strategies donchian --date 2026-08-05
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import time
from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

from backtest.engine import (
    OpenPosition,
    apply_slippage,
    check_donchian_exit,
    close_position,
    compute_atr,
    compute_position_size,
    plan_donchian_entry,
    resolve_intrabar_exit,
)
from config import (
    COMMISSION_PCT,
    CRYPTO_TICKERS,
    DONCHIAN_ATR_PERIOD,
    DONCHIAN_ATR_STOP_MULT,
    FETCH_MAX_ATTEMPTS,
    FETCH_RETRY_BASE_DELAY_SECONDS,
    MA_VOTING_PAIRS,
    MIN_BARS_REQUIRED,
    PAPER_TRADING_DEFAULT_STRATEGY,
    PAPER_TRADING_LOOKBACK_DAYS,
    RISK_CORRELATION_CLUSTER_LOOKBACK_DAYS,
    RISK_CORRELATION_CLUSTER_THRESHOLD,
    RISK_MAX_GROSS_LEVERAGE,
    RISK_MAX_POSITION_SIZE,
    RISK_MAX_SECTOR_EXPOSURE,
    RISK_PER_TRADE,
    SLIPPAGE_PCT,
    STOP_PROXIMITY_WARNING_PCT,
)
from data.adjust import adjust_jumps
from data.fetch import fetch_ohlcv
from gozcu.universe import get_bist_universe
from notifications.telegram import send_telegram_message
from paper_trading.logger import PaperTradingLogger
from paper_trading.state import PaperTradingState, PositionRecord
from risk import portfolio as risk_portfolio
from risk import correlation_clusters
from risk.correlation_clusters import build_correlation_clusters, compute_return_matrix
from signals import bollinger_fade, donchian, ma_voting, price_action

log = logging.getLogger("paper_trading.runner")

STRATEGY_SIGNAL_FN: dict[str, Callable[[pd.DataFrame], pd.DataFrame]] = {
    "donchian": donchian.generate_signals,
    "price_action": price_action.generate_signals,
    "ma_voting": ma_voting.generate_signals,
    "bollinger_fade": bollinger_fade.generate_signals,
}

FetchFn = Callable[..., pd.DataFrame]

# -- Strateji-basina giris parametreleri (entry_price, stop_price, target_price, size_multiplier) --
#
# Her strateji farkli bir giris/stop/hedef mantigina sahip (Donchian: ATR
# stop + trailing cikis; Price Action: sabit R/R; MA-oylama: ATR stop +
# sinyal-bazli cikis + oy-sayisina orantili buyukluk) - tek bir if/else
# yerine bir REGISTRY kullanilir (M4'te 3. strateji eklenince if/else'in
# okunurlugu/genisleyebilirligi kaybolacagindan bu noktada refactor edildi).


def _donchian_entry_params(
    df: pd.DataFrame, direction: int, last_row: pd.Series, last_signal: pd.Series
) -> tuple[float | None, float | None, float | None, float]:
    atr_series = compute_atr(df, period=DONCHIAN_ATR_PERIOD)
    current_atr = atr_series.iloc[-1]
    if pd.notna(current_atr) and current_atr > 0:
        entry_price, stop_price = plan_donchian_entry(
            last_row["Close"], direction, current_atr, DONCHIAN_ATR_STOP_MULT, SLIPPAGE_PCT
        )
        return entry_price, stop_price, None, 1.0
    return None, None, None, 1.0


def _price_action_entry_params(
    df: pd.DataFrame, direction: int, last_row: pd.Series, last_signal: pd.Series
) -> tuple[float | None, float | None, float | None, float]:
    entry_price = apply_slippage(last_row["Close"], direction, is_entry=True, slippage_pct=SLIPPAGE_PCT)
    stop_price = last_signal["stop_long"] if direction == 1 else last_signal["stop_short"]
    target_price = last_signal["target_long"] if direction == 1 else last_signal["target_short"]
    return entry_price, stop_price, target_price, 1.0


def _ma_voting_entry_params(
    df: pd.DataFrame, direction: int, last_row: pd.Series, last_signal: pd.Series
) -> tuple[float | None, float | None, float | None, float]:
    entry_price = apply_slippage(last_row["Close"], direction, is_entry=True, slippage_pct=SLIPPAGE_PCT)
    stop_price = last_signal["stop_long"] if direction == 1 else last_signal["stop_short"]
    # Kart 1 - "3 oy = tam pozisyon, 1 oy = 1/3 pozisyon": buyukluk carpani
    # abs(vote_count)/toplam_cift_sayisi (bkz. signals/ma_voting.py modul docstring'i).
    size_multiplier = abs(int(last_signal["vote_count"])) / len(MA_VOTING_PAIRS)
    return entry_price, stop_price, None, size_multiplier


STRATEGY_ENTRY_PARAMS_FN: dict[
    str, Callable[[pd.DataFrame, int, pd.Series, pd.Series], tuple[float | None, float | None, float | None, float]]
] = {
    "donchian": _donchian_entry_params,
    "price_action": _price_action_entry_params,
    "ma_voting": _ma_voting_entry_params,
    # bollinger_fade (Kart 3), price_action (Kart 5) ile AYNI mekanigi
    # kullanir: sabit stop + sabit hedef sinyal DataFrame'inden okunur -
    # ayri bir fonksiyon YAZILMADI (bkz. backtest/engine.py::run_backtest
    # dispatch'indeki ayni gerekce).
    "bollinger_fade": _price_action_entry_params,
}


# -- Strateji-basina cikis kontrolu (acik pozisyon -> (fiyat, sebep) | None) --


def _donchian_exit(
    direction: int, last_row: pd.Series, position: PositionRecord, last_signal: pd.Series
) -> tuple[float, str] | None:
    trailing_level = last_signal["exit_long_level"] if direction == 1 else last_signal["exit_short_level"]
    return check_donchian_exit(
        direction, last_row["Open"], last_row["High"], last_row["Low"], last_row["Close"],
        position.stop_price, trailing_level,
    )


def _price_action_exit(
    direction: int, last_row: pd.Series, position: PositionRecord, last_signal: pd.Series
) -> tuple[float, str] | None:
    return resolve_intrabar_exit(
        direction, last_row["Open"], last_row["High"], last_row["Low"], position.stop_price, position.target_price
    )


def _ma_voting_exit(
    direction: int, last_row: pd.Series, position: PositionRecord, last_signal: pd.Series
) -> tuple[float, str] | None:
    # Once stop kontrolu (fiyat-bazli, intrabar) - sinyal HENUZ donmemis
    # olsa bile stop'a takilmis olabilir.
    stop_hit = resolve_intrabar_exit(
        direction, last_row["Open"], last_row["High"], last_row["Low"], position.stop_price, target_price=None
    )
    if stop_hit is not None:
        return stop_hit
    # Sinyal-bazli cikis: oy sayisi 0'a/karsi isarete donduyse (bkz.
    # signals/ma_voting.py modul docstring'i).
    exit_flag = last_signal["exit_long_signal"] if direction == 1 else last_signal["exit_short_signal"]
    if bool(exit_flag):
        return float(last_row["Close"]), "signal"
    return None


STRATEGY_EXIT_FN: dict[str, Callable[[int, pd.Series, PositionRecord, pd.Series], tuple[float, str] | None]] = {
    "donchian": _donchian_exit,
    "price_action": _price_action_exit,
    "ma_voting": _ma_voting_exit,
    "bollinger_fade": _price_action_exit,
}


def _default_markets() -> dict[str, list[str]]:
    """Varsayilan evren: BIST icin Gozcu'nun canli evrenini (dinamik
    Wikipedia cekimi; basarisiz/bos donerse gozcu.universe kendi icinde
    config.BIST_TICKERS - 13 likit sembol - yedegine duser), kripto icin
    sabit CRYPTO_TICKERS (M3 - evren genisletme, risk/correlation_clusters.py
    ile ATOMIK teslim edildi - bkz. modul docstring'i "PORTFOY TAHSISI")."""
    return {"bist": get_bist_universe(), "crypto": list(CRYPTO_TICKERS)}


def _format_entry_telegram_message(
    symbol: str, strategy: str, direction: int, entry_price: float, stop_price: float, signal_date: dt.date
) -> str:
    """GIRIS bildirimi metnini olusturur (orn. "🔴 GIRIS [donchian]: EREGL.IS
    SHORT @ 38.66 | Stop: 41.72 (+7.9%) | 2026-08-07"). Emoji yon renginde:
    LONG=yesil, SHORT=kirmizi (dashboard'daki ayni renk disipliniyle
    tutarli)."""
    emoji = "🟢" if direction == 1 else "🔴"
    yon = "LONG" if direction == 1 else "SHORT"
    stop_pct = abs(stop_price - entry_price) / entry_price * 100
    return (
        f"{emoji} GIRIS [{strategy}]: {symbol} {yon} @ {entry_price:.2f} | "
        f"Stop: {stop_price:.2f} ({stop_pct:+.1f}%) | {signal_date.isoformat()}"
    )


def _format_exit_telegram_message(
    symbol: str, strategy: str, direction: int, exit_price: float, r_multiple: float, exit_reason: str, signal_date: dt.date
) -> str:
    """CIKIS bildirimi metnini olusturur. Emoji kar/zarar renginde: R>=0 yesil,
    R<0 kirmizi (yon degil, sonuc onemli)."""
    emoji = "🟢" if r_multiple >= 0 else "🔴"
    yon = "LONG" if direction == 1 else "SHORT"
    return (
        f"{emoji} CIKIS [{strategy}]: {symbol} {yon} @ {exit_price:.2f} | "
        f"R: {r_multiple:+.2f} ({exit_reason}) | {signal_date.isoformat()}"
    )


def _format_stop_proximity_telegram_message(
    symbol: str, strategy: str, direction: int, current_price: float, stop_price: float
) -> str:
    """Stop'a yaklasma uyari metnini olusturur. Karar/islem degistirmez,
    yalnizca erken bilgilendirme."""
    yon = "LONG" if direction == 1 else "SHORT"
    distance_pct = abs(current_price - stop_price) / current_price * 100
    return (
        f"⚠️ [{strategy}] {symbol} {yon} stop'a yaklasiyor: guncel {current_price:.2f}, "
        f"stop {stop_price:.2f} (mesafe %{distance_pct:.1f})"
    )


@dataclass
class SymbolResult:
    """Bir (sembol, strateji) cifti icin bu calistirmada alinan aksiyonun ozeti."""

    symbol: str
    strategy: str
    market: str
    action: str
    # action degerleri:
    #   skip_weekend, skip_fetch_error, skip_insufficient_data,
    #   skip_already_processed, skip_risk_budget, hold, no_signal,
    #   entry_long, entry_short, exit
    detail: str = ""
    signal_date: dt.date | None = None
    last_close: float | None = None


@dataclass
class EntryCandidate:
    """Yeni bir pozisyon acmaya aday (sembol, strateji) cifti - portfoy
    tahsisi karar verene kadar HENUZ ACILMAMIS durumdadir."""

    symbol: str
    strategy: str
    market: str
    direction: int  # +1 long, -1 short
    entry_price: float
    stop_price: float
    signal_date: dt.date
    df: pd.DataFrame  # korelasyon kumelemesi icin (Close kolonu kullanilir)
    target_price: float | None = None
    size_multiplier: float = 1.0  # Kart 1 oy-sayisi orantili buyukluk (digerlerinde 1.0)


def is_bist_trading_day(date: dt.date) -> bool:
    """BIST icin basit hafta sonu kontrolu.

    Yalnizca Cumartesi/Pazar atlanir; tam resmi tatil takvimi bu surumun
    kapsami disinda (gorev tanimindaki basitlestirme).

    Args:
        date: Kontrol edilecek takvim tarihi.

    Returns:
        Pazartesi-Cuma ise True.
    """
    return date.weekday() < 5


def fetch_with_retry(
    fetch_fn: FetchFn,
    ticker: str,
    start: str,
    end: str | None,
    max_attempts: int = FETCH_MAX_ATTEMPTS,
    base_delay: float = FETCH_RETRY_BASE_DELAY_SECONDS,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> pd.DataFrame | None:
    """fetch_fn'i exponential backoff ile en fazla max_attempts kez dener.

    Args:
        fetch_fn: (ticker, start=..., end=...) imzali veri cekme fonksiyonu.
        ticker: Sembol.
        start, end: fetch_fn'e aktarilacak tarih araligi.
        max_attempts: Toplam deneme sayisi (varsayilan 3).
        base_delay: Ilk bekleme suresi saniye (varsayilan 1.0); her denemede
            2 ile carpilir (1s, 2s, 4s, ...).
        sleep_fn: Bekleme icin cagrilan fonksiyon (testte no-op enjekte edilir).

    Returns:
        Basarili olursa (bos olmayan) DataFrame; tum denemeler basarisiz
        olursa None (istisna FIRLATILMAZ ki cagiran sembolu atlayip devam
        edebilsin).
    """
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            df = fetch_fn(ticker, start=start, end=end)
            if df is None or df.empty:
                raise ValueError("bos veri seti dondu")
            return df
        except Exception as exc:  # noqa: BLE001 - kasitli genis yakalama: devam etmek icin
            last_error = exc
            log.warning("fetch basarisiz (deneme %d/%d) %s: %s", attempt, max_attempts, ticker, exc)
            if attempt < max_attempts:
                sleep_fn(base_delay * (2 ** (attempt - 1)))
    log.error("%s icin veri cekilemedi (%d deneme sonrasi): %s", ticker, max_attempts, last_error)
    return None


def fetch_symbol_bars(
    symbol: str,
    market: str,
    run_date: dt.date,
    fetch_fn: FetchFn,
    fetch_max_attempts: int = FETCH_MAX_ATTEMPTS,
    fetch_base_delay: float = FETCH_RETRY_BASE_DELAY_SECONDS,
    fetch_sleep_fn: Callable[[float], None] = time.sleep,
) -> tuple[pd.DataFrame | None, str | None]:
    """Bir sembol icin (o sembolun TUM aktif stratejilerinin PAYLASACAGI)
    OHLCV barlarini ceker.

    M3 oncesi bu mantik tek bir strateji varsayimiyla sembol basina
    cagiriliyordu; artik coklu strateji ile ayni sembolu N kez cekmek
    israf olacagindan, veri sembol basina BIR KEZ cekilir ve sonucu tum
    aktif stratejiler paylasir (bkz. evaluate_symbol_strategy).

    Returns:
        (df, None) basariliysa; (None, skip_reason) basarisizsa -
        skip_reason "skip_weekend" | "skip_fetch_error" |
        "skip_insufficient_data" degerlerinden biridir.
    """
    if market == "bist" and not is_bist_trading_day(run_date):
        return None, "skip_weekend"

    start = (run_date - dt.timedelta(days=PAPER_TRADING_LOOKBACK_DAYS)).isoformat()
    end = (run_date + dt.timedelta(days=1)).isoformat()
    df = fetch_with_retry(
        fetch_fn, symbol, start, end,
        max_attempts=fetch_max_attempts, base_delay=fetch_base_delay, sleep_fn=fetch_sleep_fn,
    )
    if df is None:
        return None, "skip_fetch_error"

    df = df[df.index.date <= run_date]
    if market == "bist":
        df = adjust_jumps(df)

    if len(df) < MIN_BARS_REQUIRED:
        return None, "skip_insufficient_data"

    return df, None


def evaluate_symbol_strategy(
    symbol: str,
    market: str,
    strategy: str,
    df: pd.DataFrame,
    state: PaperTradingState,
    trade_logger: PaperTradingLogger,
    run_date: dt.date,
    dry_run: bool,
) -> SymbolResult | EntryCandidate:
    """Onceden cekilmis barlarla tek bir (sembol, strateji) cifti icin degerlendirme yapar.

    Acik pozisyon VARSA: cikis kontrolu yapilir ve sonuc HEMEN uygulanir
    (dry_run=False ise state/log yazilir) - exit'ler risk AZALTTIGI icin
    portfoy tahsisini beklemeye gerek yoktur.

    Acik pozisyon YOKSA ve bir giris sinyali VARSA: pozisyon HENUZ
    ACILMAZ - bir EntryCandidate dondurulur, asil acilip acilmayacagina
    (ve ne buyuklukte) run_once icindeki portfoy tahsisi adimi karar verir.

    Returns:
        Acil bir aksiyon alindiysa (veya sinyal yoksa) SymbolResult;
        yeni bir giris sinyali varsa EntryCandidate.
    """
    signal_date = df.index[-1].date()
    last_close = float(df["Close"].iloc[-1])

    last_processed = state.get_last_processed_date(symbol, strategy)
    if last_processed is not None and last_processed >= signal_date:
        return SymbolResult(
            symbol=symbol, strategy=strategy, market=market, action="skip_already_processed",
            signal_date=signal_date, last_close=last_close,
        )

    signal_fn = STRATEGY_SIGNAL_FN[strategy]
    signals = signal_fn(df)
    last_row = df.iloc[-1]
    last_signal = signals.iloc[-1]

    position: PositionRecord | None = state.get_position(symbol, strategy)

    if position is not None:
        direction = position.direction
        exit_fn = STRATEGY_EXIT_FN[strategy]
        exit_result = exit_fn(direction, last_row, position, last_signal)

        action = "hold"
        detail = ""

        if exit_result is not None:
            raw_price, reason = exit_result
            open_pos = OpenPosition(
                direction, pd.Timestamp(position.entry_date), position.entry_price, position.stop_price, position.size
            )
            trade, net_pnl = close_position(
                open_pos, pd.Timestamp(signal_date), raw_price, reason, COMMISSION_PCT, SLIPPAGE_PCT
            )
            action = "exit"
            detail = reason
            if not dry_run:
                new_equity = state.adjust_equity(net_pnl)
                state.close_position(symbol, strategy)
                trade_logger.log_trade(
                    {
                        "event_type": "exit",
                        "date": signal_date.isoformat(),
                        "symbol": symbol,
                        "strategy": strategy,
                        "direction": direction,
                        "price": trade["exit_price"],
                        "stop_price": trade["stop_price"],
                        "target_price": position.target_price,
                        "size": trade["size"],
                        "pnl": trade["pnl"],
                        "r_multiple": trade["r_multiple"],
                        "exit_reason": reason,
                        "equity_after": new_equity,
                    }
                )
                send_telegram_message(
                    _format_exit_telegram_message(
                        symbol, strategy, direction, trade["exit_price"], trade["r_multiple"], reason, signal_date
                    )
                )
        else:
            if not dry_run:
                initial_risk = abs(position.entry_price - position.stop_price)
                distance_to_stop = abs(last_close - position.stop_price)
                if initial_risk > 0 and distance_to_stop < STOP_PROXIMITY_WARNING_PCT * initial_risk:
                    already_warned = state.get_stop_warning_date(symbol, strategy)
                    if already_warned is None or already_warned < signal_date:
                        send_telegram_message(
                            _format_stop_proximity_telegram_message(
                                symbol, strategy, direction, last_close, position.stop_price
                            )
                        )
                        state.set_stop_warning_date(symbol, strategy, signal_date)

        if not dry_run:
            state.set_last_processed_date(symbol, strategy, signal_date)
        return SymbolResult(
            symbol=symbol, strategy=strategy, market=market, action=action, detail=detail,
            signal_date=signal_date, last_close=last_close,
        )

    # Acik pozisyon yok: giris adayi olustur (HENUZ ACILMAZ - bkz. modul docstring'i)
    direction = 1 if bool(last_signal["entry_long"]) else (-1 if bool(last_signal["entry_short"]) else 0)
    entry_price: float | None = None
    stop_price: float | None = None
    target_price: float | None = None
    size_multiplier = 1.0

    if direction != 0:
        entry_params_fn = STRATEGY_ENTRY_PARAMS_FN[strategy]
        entry_price, stop_price, target_price, size_multiplier = entry_params_fn(df, direction, last_row, last_signal)

    valid_stop = (
        entry_price is not None
        and stop_price is not None
        and ((direction == 1 and stop_price < entry_price) or (direction == -1 and stop_price > entry_price))
    )

    if not valid_stop:
        if not dry_run:
            state.set_last_processed_date(symbol, strategy, signal_date)
        return SymbolResult(
            symbol=symbol, strategy=strategy, market=market, action="no_signal",
            signal_date=signal_date, last_close=last_close,
        )

    return EntryCandidate(
        symbol=symbol, strategy=strategy, market=market, direction=direction,
        entry_price=entry_price, stop_price=stop_price, target_price=target_price,
        signal_date=signal_date, df=df, size_multiplier=size_multiplier,
    )


def allocate_and_open_candidates(
    candidates: list[EntryCandidate],
    state: PaperTradingState,
    trade_logger: PaperTradingLogger,
    mark_prices: dict[str, float],
    dry_run: bool,
    historical_price_data: dict[str, pd.DataFrame] | None = None,
) -> list[SymbolResult]:
    """Gunun tum yeni giris adaylarina, portfoy-geneli risk butcesini
    kullanarak pozisyon acar (M3 - PORTFOY TAHSISI, bkz. modul docstring'i).

    Adimlar:
        1. Mevcut acik pozisyonlarin (TUM stratejiler) tukettigi brut
           maruziyeti hesapla, kalan butceyi bul.
        2. Adaylarin VE mevcut acik pozisyonlarin (birlikte) getiri
           korelasyonundan kume haritasi cikar (risk/correlation_clusters.py) -
           M7 CAPRAZ-GUN kume takibi: bir kume dunku/onceki gunlerde acilan
           pozisyonlarla ZATEN doluysa, bugunku YENI adaylar o kumede
           KALAN butceyle sinirlanir (M3'un birakti	gi acik nokta - onceki
           surumde yalnizca AYNI GUNUN adaylari birbirleriyle kumeleniyordu,
           dun acilmis bir pozisyonun kume-maruziyeti hic hesaba
           katilmiyordu).
        3. GECICI esit-agirlik skorla (bkz. modul docstring'i "GECICI
           SKOR") risk.portfolio.optimize_portfolio'yu cagirip hedef
           agirliklari bul.
        4. Her aday icin, ATR-stop/%1-risk bazli hisse sayisi ile
           optimizer'in agirlik-bazli hisse sayisinin KUCUK OLANINI kullan
           (hem islem-basi risk hem portfoy-geneli maruziyet sinirlanir).

    Args:
        candidates: evaluate_symbol_strategy'den gelen yeni giris adaylari.
        state: Kalici state (dry_run=True ise DEGISTIRILMEZ).
        trade_logger: Trade logger (dry_run=True ise YAZILMAZ).
        mark_prices: {sembol: bu calistirmadaki son kapanis} - mevcut acik
            pozisyonlarin guncel dolar maruziyetini olcmek icin.
        dry_run: True ise hicbir state/log degisikligi yapilmaz.
        historical_price_data: {sembol: OHLCV df} - bu calistirmada
            TARANMIS TUM sembollerin (yalniz adaylarin degil) gecmis
            barlari; acik pozisyonlarin kume uyeligini belirlemek icin
            kullanilir. None/eksikse (orn. o sembol bugun fetch
            basarisiz oldu) o pozisyon kume hesabina KATILMAZ - brut
            butceye zaten dahil oldugundan tamamen gozden kacmaz, sadece
            o gune ozel kume sinirlamasi o pozisyon icin uygulanamaz.

    Returns:
        Her aday icin bir SymbolResult (action: entry_long/entry_short/
        skip_risk_budget).
    """
    results: list[SymbolResult] = []
    if not candidates:
        return results

    historical_price_data = historical_price_data or {}
    equity = state.get_equity()

    existing_positions = state.list_open_positions()
    existing_gross_exposure = 0.0
    existing_position_exposure: dict[str, float] = {}  # sembol -> |maruziyet|/equity, kume hesabi icin
    if equity > 0:
        for pos in existing_positions:
            mark = mark_prices.get(pos.symbol, pos.entry_price)
            exposure = abs(pos.size * mark) / equity
            existing_gross_exposure += exposure
            existing_position_exposure[pos.symbol] = existing_position_exposure.get(pos.symbol, 0.0) + exposure

    remaining_budget = max(0.0, RISK_MAX_GROSS_LEVERAGE - existing_gross_exposure)

    candidate_keys: dict[str, EntryCandidate] = {f"{c.symbol}::{c.strategy}": c for c in candidates}

    if remaining_budget <= 0:
        weights: dict[str, float] = {key: 0.0 for key in candidate_keys}
    else:
        # Kume haritasi ADAYLAR + ACIK POZISYON sembolleri BIRLIKTE cikarilir
        # (M7) - boylece bir aday, dun acilmis korelasyonlu bir pozisyonla
        # AYNI kumeye duserse bu tespit edilebilir.
        combined_price_data: dict[str, pd.DataFrame] = {key: c.df for key, c in candidate_keys.items()}
        existing_symbols = {pos.symbol for pos in existing_positions}
        for symbol in existing_symbols:
            df = historical_price_data.get(symbol)
            if df is not None:
                combined_price_data[f"__existing__::{symbol}"] = df

        returns_df = compute_return_matrix(combined_price_data, lookback_days=RISK_CORRELATION_CLUSTER_LOOKBACK_DAYS)
        all_clusters = (
            build_correlation_clusters(returns_df, threshold=RISK_CORRELATION_CLUSTER_THRESHOLD)
            if not returns_df.empty
            else {}
        )

        candidate_clusters = {key: all_clusters[key] for key in candidate_keys if key in all_clusters}
        existing_cluster_exposure_by_key = {
            f"__existing__::{symbol}": exposure for symbol, exposure in existing_position_exposure.items()
        }
        existing_cluster_exposure = correlation_clusters.compute_cluster_exposure(
            all_clusters, existing_cluster_exposure_by_key
        )

        # Her kume icin KALAN butce = toplam sinir - o kumede acik
        # pozisyonlardan zaten tuketilmis pay (M7). Adaylarin kumesinde
        # olmayan hicbir kume icin girdi TUTULMAZ (optimize_portfolio
        # eksik anahtari 0.0 kabul eder - ama buradaki dongu candidate_clusters
        # UZERINDEN gittigi icin her aday kumesi mutlaka bir girdiye sahip olur).
        sector_caps: dict[str, float] = {}
        for cluster_id in set(candidate_clusters.values()):
            consumed = existing_cluster_exposure.get(cluster_id, 0.0)
            sector_caps[cluster_id] = max(0.0, RISK_MAX_SECTOR_EXPOSURE - consumed)

        # GECICI skor (M6'dan once) - yon isaretiyle esit agirlik, bkz. modul docstring'i.
        scores = {key: float(c.direction) for key, c in candidate_keys.items()}
        weights = risk_portfolio.optimize_portfolio(
            scores,
            max_gross_leverage=remaining_budget,
            max_position_size=RISK_MAX_POSITION_SIZE,
            sector_map=candidate_clusters if candidate_clusters else None,
            max_sector_exposure=sector_caps if sector_caps else RISK_MAX_SECTOR_EXPOSURE,
        )

    for key, candidate in candidate_keys.items():
        weight = weights.get(key, 0.0)
        risk_based_size = compute_position_size(equity, RISK_PER_TRADE, candidate.entry_price, candidate.stop_price)
        weight_based_size = (abs(weight) * equity) / candidate.entry_price if candidate.entry_price > 0 else 0.0
        # size_multiplier: Kart 1 "oy sayisina orantili buyukluk" (bkz.
        # EntryCandidate.size_multiplier docstring'i); diger stratejilerde 1.0.
        size = min(risk_based_size, weight_based_size) * candidate.size_multiplier
        last_close = float(candidate.df["Close"].iloc[-1])

        if abs(weight) < 1e-6 or size <= 0:
            if not dry_run:
                state.set_last_processed_date(candidate.symbol, candidate.strategy, candidate.signal_date)
            results.append(
                SymbolResult(
                    symbol=candidate.symbol, strategy=candidate.strategy, market=candidate.market,
                    action="skip_risk_budget", signal_date=candidate.signal_date, last_close=last_close,
                )
            )
            continue

        action = "entry_long" if candidate.direction == 1 else "entry_short"
        if not dry_run:
            commission = COMMISSION_PCT * candidate.entry_price * size
            new_equity = state.adjust_equity(-commission)
            state.open_position(
                candidate.symbol, candidate.strategy, candidate.direction, candidate.signal_date,
                candidate.entry_price, candidate.stop_price, size, candidate.target_price,
            )
            state.set_last_processed_date(candidate.symbol, candidate.strategy, candidate.signal_date)
            trade_logger.log_trade(
                {
                    "event_type": "entry",
                    "date": candidate.signal_date.isoformat(),
                    "symbol": candidate.symbol,
                    "strategy": candidate.strategy,
                    "direction": candidate.direction,
                    "price": candidate.entry_price,
                    "stop_price": candidate.stop_price,
                    "target_price": candidate.target_price,
                    "size": size,
                    "equity_after": new_equity,
                }
            )
            send_telegram_message(
                _format_entry_telegram_message(
                    candidate.symbol, candidate.strategy, candidate.direction,
                    candidate.entry_price, candidate.stop_price, candidate.signal_date,
                )
            )
        results.append(
            SymbolResult(
                symbol=candidate.symbol, strategy=candidate.strategy, market=candidate.market,
                action=action, signal_date=candidate.signal_date, last_close=last_close,
            )
        )

    return results


def _print_result(result: SymbolResult, dry_run: bool) -> None:
    prefix = "[DRY-RUN] " if dry_run else ""
    suffix = f" [{result.detail}]" if result.detail else ""
    print(f"{prefix}{result.symbol:>12} ({result.market:>6}/{result.strategy:<12}): {result.action}{suffix}")


def run_once(
    strategies: list[str] | None = None,
    run_date: dt.date | None = None,
    dry_run: bool = False,
    state: PaperTradingState | None = None,
    trade_logger: PaperTradingLogger | None = None,
    fetch_fn: FetchFn = fetch_ohlcv,
    markets: dict[str, list[str]] | None = None,
    verbose: bool = True,
    fetch_max_attempts: int = FETCH_MAX_ATTEMPTS,
    fetch_base_delay: float = FETCH_RETRY_BASE_DELAY_SECONDS,
    fetch_sleep_fn: Callable[[float], None] = time.sleep,
) -> dict:
    """Tum evren (bist + crypto) x tum aktif stratejiler icin bir paper-trading calistirmasi yapar.

    Args:
        strategies: Aktif stratejiler listesi (orn. ["donchian"] veya
            ["donchian", "ma_voting"]). None ise [PAPER_TRADING_DEFAULT_STRATEGY].
        run_date: Bu calistirmanin "bugun" kabul ettigi tarih (None ise
            dt.date.today()).
        dry_run: True ise hicbir state/log degisikligi yapilmaz; state None
            ise ve state.db henuz diskte yoksa, dosya HIC OLUSTURULMAZ
            (bellek-ici gecici state kullanilir - bkz. PaperTradingState).
        state: Enjekte edilebilir PaperTradingState (testler icin; None ise
            varsayilan yol/sermaye ile yeni bir tane acilir ve fonksiyon
            sonunda kapatilir). dry_run=True oldugunda read_only=True ile
            acilir.
        trade_logger: Enjekte edilebilir PaperTradingLogger (testler icin).
        fetch_fn: Veri cekme fonksiyonu (testler icin sentetik bir stub
            verilebilir; varsayilan data.fetch.fetch_ohlcv).
        markets: {"bist": [...], "crypto": [...]} (testler icin kucuk bir
            alt kume verilebilir; None ise _default_markets() - Gozcu'nun
            canli BIST evreni + sabit kripto evreni).
        verbose: True ise her (sembol, strateji) icin bir satir ve sonunda
            equity ozeti yazdirir.

    Returns:
        {"run_date", "results" (SymbolResult listesi), "equity_snapshot"}
        anahtarlarina sahip bir sozluk.
    """
    run_date = run_date or dt.date.today()
    strategies = strategies if strategies is not None else [PAPER_TRADING_DEFAULT_STRATEGY]
    markets = markets if markets is not None else _default_markets()
    owns_state = state is None
    if state is None:
        state = PaperTradingState(read_only=dry_run)
    if trade_logger is None:
        trade_logger = PaperTradingLogger()

    try:
        if not dry_run:
            # Bu calistirma state'i degistirmeden ONCE zaman damgali bir
            # yedek al (basit kopya; eski yedekleri otomatik temizleme yok).
            state.backup()

        results: list[SymbolResult] = []
        candidates: list[EntryCandidate] = []
        mark_prices: dict[str, float] = {}
        price_data: dict[str, pd.DataFrame] = {}  # M7 - capraz-gun kume takibi icin (bkz. allocate_and_open_candidates)

        for market, tickers in markets.items():
            for symbol in tickers:
                df, skip_reason = fetch_symbol_bars(
                    symbol, market, run_date, fetch_fn,
                    fetch_max_attempts=fetch_max_attempts, fetch_base_delay=fetch_base_delay, fetch_sleep_fn=fetch_sleep_fn,
                )
                if df is None:
                    for strategy in strategies:
                        result = SymbolResult(symbol=symbol, strategy=strategy, market=market, action=skip_reason or "skip_fetch_error")
                        results.append(result)
                        if verbose:
                            _print_result(result, dry_run)
                    continue

                mark_prices[symbol] = float(df["Close"].iloc[-1])
                price_data[symbol] = df

                for strategy in strategies:
                    outcome = evaluate_symbol_strategy(
                        symbol, market, strategy, df, state, trade_logger, run_date, dry_run
                    )
                    if isinstance(outcome, EntryCandidate):
                        candidates.append(outcome)
                    else:
                        results.append(outcome)
                        if verbose:
                            _print_result(outcome, dry_run)

        allocation_results = allocate_and_open_candidates(
            candidates, state, trade_logger, mark_prices, dry_run, historical_price_data=price_data
        )
        results.extend(allocation_results)
        if verbose:
            for result in allocation_results:
                _print_result(result, dry_run)

        open_positions = state.list_open_positions()
        realized_equity = state.get_equity()
        unrealized = 0.0
        for pos in open_positions:
            mark = mark_prices.get(pos.symbol)
            if mark is not None:
                unrealized += (mark - pos.entry_price) * pos.direction * pos.size
        total_equity = realized_equity + unrealized

        snapshot = {
            "date": run_date.isoformat(),
            "realized_equity": realized_equity,
            "unrealized_pnl": unrealized,
            "total_equity": total_equity,
            "open_positions": len(open_positions),
        }

        if not dry_run:
            trade_logger.log_equity_snapshot(snapshot)
            trades_df = trade_logger.read_trades()
            trades_last_7_days = 0
            if not trades_df.empty:
                cutoff = pd.Timestamp(run_date) - pd.Timedelta(days=7)
                exits = trades_df[trades_df["event_type"] == "exit"]
                trades_last_7_days = int((exits["date"] >= cutoff).sum())
            trade_logger.update_summary(
                {
                    "last_updated": run_date.isoformat(),
                    "strategy": ", ".join(strategies),
                    "total_equity": total_equity,
                    "realized_equity": realized_equity,
                    "open_positions": len(open_positions),
                    "trades_last_7_days": trades_last_7_days,
                }
            )

        if verbose:
            print("-" * 80)
            print(
                f"Toplam equity: {total_equity:.2f} "
                f"(realized={realized_equity:.2f}, unrealized={unrealized:.2f}) | "
                f"Acik pozisyon: {len(open_positions)}"
            )

        return {"run_date": run_date, "results": results, "equity_snapshot": snapshot}
    finally:
        if owns_state:
            state.close()


def main(argv: list[str] | None = None) -> None:
    """CLI giris noktasi."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Paper trading gunluk calistirici")
    parser.add_argument(
        "--strategies", nargs="+", choices=sorted(STRATEGY_SIGNAL_FN), default=[PAPER_TRADING_DEFAULT_STRATEGY],
        help="Aktif stratejiler (bosluklarla ayirip birden fazla verilebilir)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Hicbir state/log degisikligi yapmadan ne yapilacagini yazdirir")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD (opsiyonel; gecmis bir tarih icin simulasyon)")
    args = parser.parse_args(argv)

    run_date = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    print(f"Paper trading | stratejiler={args.strategies} | tarih={run_date} | dry_run={args.dry_run}")
    print("-" * 80)
    run_once(strategies=args.strategies, run_date=run_date, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
