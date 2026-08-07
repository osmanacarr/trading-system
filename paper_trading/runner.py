"""paper_trading/runner.py - gunluk paper trading calistiricisi.

Her sembol icin akis:
    en guncel veriyi cek (3 deneme + exponential backoff) ->
    sinyalleri uret (backtest ile AYNI signals.* fonksiyonlari) ->
    acik pozisyon VARSA: stop/trailing kontrolu (tetiklenirse kapat) ->
    acik pozisyon YOKSA: giris sinyali varsa ac (backtest.engine ile AYNI
    ATR-stop / pozisyon-buyuklugu formulleri) ->
    state'i guncelle (idempotency icin sembolun son islenen bar tarihi)

IDEMPOTENCY: Her sembol icin islenen son bar'in tarihi state'e yazilir
(PaperTradingState.set_last_processed_date). Runner ayni gun icinde tekrar
calistirilirsa, veri kaynagindaki en guncel bar hala ayni oldugundan
(signal_date degismez), sembol "zaten islendi" olarak atlanir - ayni sinyal
iki kere isleme alinmaz.

DAYANIKLILIK: Bir sembolde veri cekme kalici olarak basarisiz olursa
(3 deneme sonrasi) o sembol atlanir ve loglanir; calisma DURMAZ, digerlerine
devam edilir.

Kullanim:
    python -m paper_trading.runner --strategy donchian
    python -m paper_trading.runner --strategy donchian --dry-run
    python -m paper_trading.runner --strategy donchian --date 2026-08-05
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
    BIST_TICKERS,
    COMMISSION_PCT,
    CRYPTO_TICKERS,
    DONCHIAN_ATR_PERIOD,
    DONCHIAN_ATR_STOP_MULT,
    FETCH_MAX_ATTEMPTS,
    FETCH_RETRY_BASE_DELAY_SECONDS,
    MIN_BARS_REQUIRED,
    PAPER_TRADING_DEFAULT_STRATEGY,
    PAPER_TRADING_LOOKBACK_DAYS,
    RISK_PER_TRADE,
    SLIPPAGE_PCT,
)
from data.adjust import adjust_jumps
from data.fetch import fetch_ohlcv
from notifications.telegram import send_telegram_message
from paper_trading.logger import PaperTradingLogger
from paper_trading.state import PaperTradingState, PositionRecord
from signals import donchian, price_action

log = logging.getLogger("paper_trading.runner")

STRATEGY_SIGNAL_FN: dict[str, Callable[[pd.DataFrame], pd.DataFrame]] = {
    "donchian": donchian.generate_signals,
    "price_action": price_action.generate_signals,
}

MARKETS: dict[str, list[str]] = {
    "bist": BIST_TICKERS,
    "crypto": CRYPTO_TICKERS,
}

FetchFn = Callable[..., pd.DataFrame]


def _format_entry_telegram_message(
    symbol: str, direction: int, entry_price: float, stop_price: float, signal_date: dt.date
) -> str:
    """GIRIS bildirimi metnini olusturur (orn. "🔴 GIRIS: EREGL.IS SHORT @ 38.66
    | Stop: 41.72 (+7.9%) | 2026-08-07"). Emoji yon renginde: LONG=yesil,
    SHORT=kirmizi (dashboard'daki ayni renk disipliniyle tutarli)."""
    emoji = "🟢" if direction == 1 else "🔴"
    yon = "LONG" if direction == 1 else "SHORT"
    stop_pct = abs(stop_price - entry_price) / entry_price * 100
    return (
        f"{emoji} GIRIS: {symbol} {yon} @ {entry_price:.2f} | "
        f"Stop: {stop_price:.2f} ({stop_pct:+.1f}%) | {signal_date.isoformat()}"
    )


def _format_exit_telegram_message(
    symbol: str, direction: int, exit_price: float, r_multiple: float, exit_reason: str, signal_date: dt.date
) -> str:
    """CIKIS bildirimi metnini olusturur. Emoji kar/zarar renginde: R>=0 yesil,
    R<0 kirmizi (yon degil, sonuc onemli)."""
    emoji = "🟢" if r_multiple >= 0 else "🔴"
    yon = "LONG" if direction == 1 else "SHORT"
    return (
        f"{emoji} CIKIS: {symbol} {yon} @ {exit_price:.2f} | "
        f"R: {r_multiple:+.2f} ({exit_reason}) | {signal_date.isoformat()}"
    )


@dataclass
class SymbolResult:
    """Bir sembol icin bu calistirmada alinan aksiyonun ozeti."""

    symbol: str
    market: str
    action: str
    # action degerleri:
    #   skip_weekend, skip_fetch_error, skip_insufficient_data,
    #   skip_already_processed, hold, no_signal, entry_long, entry_short, exit
    detail: str = ""
    signal_date: dt.date | None = None
    last_close: float | None = None


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


def process_symbol(
    symbol: str,
    market: str,
    strategy: str,
    state: PaperTradingState,
    trade_logger: PaperTradingLogger,
    run_date: dt.date,
    dry_run: bool,
    fetch_fn: FetchFn,
    fetch_max_attempts: int = FETCH_MAX_ATTEMPTS,
    fetch_base_delay: float = FETCH_RETRY_BASE_DELAY_SECONDS,
    fetch_sleep_fn: Callable[[float], None] = time.sleep,
) -> SymbolResult:
    """Tek bir sembol icin bir gunluk paper-trading adimini isler.

    Args:
        symbol: yfinance sembolu.
        market: "bist" veya "crypto" (piyasa takvimi kontrolu icin).
        strategy: "donchian" veya "price_action".
        state: Kalici state (dry_run=True ise DEGISTIRILMEZ).
        trade_logger: Trade/equity logger (dry_run=True ise YAZILMAZ).
        run_date: Bu calistirmanin "bugun" kabul ettigi tarih (--date ile
            gecmis bir tarih verilebilir).
        dry_run: True ise hicbir state/log degisikligi yapilmaz, yalnizca
            ne yapilacagi hesaplanir.
        fetch_fn: Veri cekme fonksiyonu (retry sarmalayicisina aktarilir).
        fetch_max_attempts, fetch_base_delay, fetch_sleep_fn: fetch_with_retry'e
            aktarilir (testlerde bekleme suresini sifirlamak icin kullanilir).

    Returns:
        SymbolResult: bu sembol icin alinan/alinacak aksiyonun ozeti.
    """
    if market == "bist" and not is_bist_trading_day(run_date):
        return SymbolResult(symbol=symbol, market=market, action="skip_weekend")

    start = (run_date - dt.timedelta(days=PAPER_TRADING_LOOKBACK_DAYS)).isoformat()
    end = (run_date + dt.timedelta(days=1)).isoformat()
    df = fetch_with_retry(
        fetch_fn, symbol, start, end,
        max_attempts=fetch_max_attempts, base_delay=fetch_base_delay, sleep_fn=fetch_sleep_fn,
    )
    if df is None:
        return SymbolResult(symbol=symbol, market=market, action="skip_fetch_error")

    df = df[df.index.date <= run_date]
    if market == "bist":
        df = adjust_jumps(df)

    if len(df) < MIN_BARS_REQUIRED:
        return SymbolResult(symbol=symbol, market=market, action="skip_insufficient_data")

    signal_date = df.index[-1].date()
    last_close = float(df["Close"].iloc[-1])

    last_processed = state.get_last_processed_date(symbol)
    if last_processed is not None and last_processed >= signal_date:
        return SymbolResult(
            symbol=symbol, market=market, action="skip_already_processed",
            signal_date=signal_date, last_close=last_close,
        )

    signal_fn = STRATEGY_SIGNAL_FN[strategy]
    signals = signal_fn(df)
    last_row = df.iloc[-1]
    last_signal = signals.iloc[-1]

    position: PositionRecord | None = state.get_position(symbol)
    action = "no_signal"
    detail = ""

    if position is not None:
        direction = position.direction
        if strategy == "donchian":
            trailing_level = last_signal["exit_long_level"] if direction == 1 else last_signal["exit_short_level"]
            exit_result = check_donchian_exit(
                direction, last_row["Open"], last_row["High"], last_row["Low"], last_row["Close"],
                position.stop_price, trailing_level,
            )
        else:
            exit_result = resolve_intrabar_exit(
                direction, last_row["Open"], last_row["High"], last_row["Low"],
                position.stop_price, position.target_price,
            )

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
                state.close_position(symbol)
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
                        symbol, direction, trade["exit_price"], trade["r_multiple"], reason, signal_date
                    )
                )
        else:
            action = "hold"
    else:
        direction = 1 if bool(last_signal["entry_long"]) else (-1 if bool(last_signal["entry_short"]) else 0)
        entry_price: float | None = None
        stop_price: float | None = None
        target_price: float | None = None

        if direction != 0:
            if strategy == "donchian":
                atr_series = compute_atr(df, period=DONCHIAN_ATR_PERIOD)
                current_atr = atr_series.iloc[-1]
                if pd.notna(current_atr) and current_atr > 0:
                    entry_price, stop_price = plan_donchian_entry(
                        last_row["Close"], direction, current_atr, DONCHIAN_ATR_STOP_MULT, SLIPPAGE_PCT
                    )
            else:
                entry_price = apply_slippage(last_row["Close"], direction, is_entry=True, slippage_pct=SLIPPAGE_PCT)
                stop_price = last_signal["stop_long"] if direction == 1 else last_signal["stop_short"]
                target_price = last_signal["target_long"] if direction == 1 else last_signal["target_short"]

        if entry_price is not None and stop_price is not None:
            size = compute_position_size(state.get_equity(), RISK_PER_TRADE, entry_price, stop_price)
            valid_stop = (direction == 1 and stop_price < entry_price) or (direction == -1 and stop_price > entry_price)
            if size > 0 and valid_stop:
                action = "entry_long" if direction == 1 else "entry_short"
                if not dry_run:
                    commission = COMMISSION_PCT * entry_price * size
                    new_equity = state.adjust_equity(-commission)
                    state.open_position(
                        symbol, strategy, direction, signal_date, entry_price, stop_price, size, target_price
                    )
                    trade_logger.log_trade(
                        {
                            "event_type": "entry",
                            "date": signal_date.isoformat(),
                            "symbol": symbol,
                            "strategy": strategy,
                            "direction": direction,
                            "price": entry_price,
                            "stop_price": stop_price,
                            "target_price": target_price,
                            "size": size,
                            "equity_after": new_equity,
                        }
                    )
                    send_telegram_message(
                        _format_entry_telegram_message(symbol, direction, entry_price, stop_price, signal_date)
                    )

    if not dry_run:
        state.set_last_processed_date(symbol, signal_date)

    return SymbolResult(symbol=symbol, market=market, action=action, detail=detail, signal_date=signal_date, last_close=last_close)


def _print_result(result: SymbolResult, dry_run: bool) -> None:
    prefix = "[DRY-RUN] " if dry_run else ""
    suffix = f" [{result.detail}]" if result.detail else ""
    print(f"{prefix}{result.symbol:>12} ({result.market:>6}): {result.action}{suffix}")


def run_once(
    strategy: str = PAPER_TRADING_DEFAULT_STRATEGY,
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
    """Tum evren (bist + crypto) icin bir paper-trading calistirmasi yapar.

    Args:
        strategy: "donchian" veya "price_action".
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
            alt kume verilebilir; varsayilan config evrenlerinin tamami).
        verbose: True ise her sembol icin bir satir ve sonunda equity ozeti
            yazdirir.

    Returns:
        {"run_date", "results" (SymbolResult listesi), "equity_snapshot"}
        anahtarlarina sahip bir sozluk.
    """
    run_date = run_date or dt.date.today()
    markets = markets if markets is not None else MARKETS
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
        for market, tickers in markets.items():
            for symbol in tickers:
                result = process_symbol(
                    symbol, market, strategy, state, trade_logger, run_date, dry_run, fetch_fn,
                    fetch_max_attempts=fetch_max_attempts, fetch_base_delay=fetch_base_delay, fetch_sleep_fn=fetch_sleep_fn,
                )
                results.append(result)
                if verbose:
                    _print_result(result, dry_run)

        open_positions = state.list_open_positions()
        realized_equity = state.get_equity()
        mark_prices = {r.symbol: r.last_close for r in results if r.last_close is not None}
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
                    "strategy": strategy,
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
    parser.add_argument("--strategy", choices=sorted(STRATEGY_SIGNAL_FN), default=PAPER_TRADING_DEFAULT_STRATEGY)
    parser.add_argument("--dry-run", action="store_true", help="Hicbir state/log degisikligi yapmadan ne yapilacagini yazdirir")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD (opsiyonel; gecmis bir tarih icin simulasyon)")
    args = parser.parse_args(argv)

    run_date = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    print(f"Paper trading | strateji={args.strategy} | tarih={run_date} | dry_run={args.dry_run}")
    print("-" * 80)
    run_once(strategy=args.strategy, run_date=run_date, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
