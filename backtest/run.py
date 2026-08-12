"""CLI giris noktasi: bir stratejiyi bir evren uzerinde ceker, backtest eder,
metrikleri ve istatistiksel anlamlilik ozetini yazdirir.

Kullanim:
    python -m backtest.run --strategy donchian --universe bist
    python -m backtest.run --strategy donchian --universe crypto
    python -m backtest.run --strategy price_action --universe bist \
        --start 2018-01-01 --end 2025-01-01
"""

from __future__ import annotations

import argparse
from typing import Callable

import pandas as pd

from backtest.engine import run_backtest
from backtest.metrics import summarize
from config import BIST_TICKERS, CRYPTO_TICKERS, INITIAL_CAPITAL, MIN_BARS_REQUIRED
from data.adjust import adjust_jumps
from data.fetch import fetch_ohlcv
from signals import bollinger_fade, donchian, ma_voting, price_action
from validation.significance import (
    is_significant_multi_test,
    multi_test_t_threshold,
    sharpe_confidence_interval,
    t_statistic,
)

STRATEGY_SIGNAL_FN: dict[str, Callable[[pd.DataFrame], pd.DataFrame]] = {
    "donchian": donchian.generate_signals,
    "price_action": price_action.generate_signals,
    "ma_voting": ma_voting.generate_signals,
    "bollinger_fade": bollinger_fade.generate_signals,
}

UNIVERSES: dict[str, list[str]] = {
    "bist": BIST_TICKERS,
    "crypto": CRYPTO_TICKERS,
}


def run_for_ticker(
    ticker: str,
    strategy: str,
    start: str,
    end: str | None,
    apply_jump_adjustment: bool,
) -> tuple[pd.DataFrame, pd.Series, dict[str, float]] | None:
    """Tek bir sembol icin veri cek -> sinyal uret -> backtest et -> ozetle.

    Args:
        ticker: yfinance sembolu.
        strategy: "donchian" veya "price_action".
        start: Baslangic tarihi "YYYY-MM-DD".
        end: Bitis tarihi "YYYY-MM-DD" veya None.
        apply_jump_adjustment: True ise data.adjust.adjust_jumps uygulanir
            (BIST icin onerilir).

    Returns:
        (trades, equity_curve, metrics) veya yetersiz veri varsa None.
    """
    df = fetch_ohlcv(ticker, start=start, end=end, interval="1d")
    if len(df) < MIN_BARS_REQUIRED:
        return None

    if apply_jump_adjustment:
        df = adjust_jumps(df)

    signal_fn = STRATEGY_SIGNAL_FN[strategy]
    signals = signal_fn(df)
    trades, equity_curve = run_backtest(df, signals, strategy=strategy, initial_capital=INITIAL_CAPITAL)
    metrics = summarize(trades, equity_curve)
    return trades, equity_curve, metrics


def main(argv: list[str] | None = None) -> None:
    """CLI giris noktasi."""
    parser = argparse.ArgumentParser(description="Donchian / Price Action backtest calistiricisi")
    parser.add_argument("--strategy", choices=sorted(STRATEGY_SIGNAL_FN), required=True)
    parser.add_argument("--universe", choices=sorted(UNIVERSES), required=True)
    parser.add_argument("--start", default="2018-01-01")
    parser.add_argument("--end", default=None)
    args = parser.parse_args(argv)

    tickers = UNIVERSES[args.universe]
    apply_jump_adjustment = args.universe == "bist"

    print(f"Strateji: {args.strategy} | Evren: {args.universe} ({len(tickers)} sembol) | {args.start} -> {args.end or 'bugun'}")
    print("-" * 100)

    all_trades: list[pd.DataFrame] = []
    rows: list[dict] = []

    for ticker in tickers:
        result = run_for_ticker(ticker, args.strategy, args.start, args.end, apply_jump_adjustment)
        if result is None:
            print(f"{ticker:>12}: yetersiz veri, atlandi")
            continue
        trades, _equity_curve, metrics = result
        all_trades.append(trades)
        rows.append({"ticker": ticker, **metrics})
        print(
            f"{ticker:>12}: n={metrics['n_trades']:>3} "
            f"win_rate={metrics['win_rate']:.2%} "
            f"E[R]={metrics['expectancy_r']:+.2f} "
            f"medyan_R={metrics['median_r']:+.2f} "
            f"maxDD={metrics['max_drawdown']:.2%} "
            f"Sharpe={metrics['sharpe']:.2f}"
        )

    if not rows:
        print("Hicbir sembol icin yeterli veri/islem uretilemedi.")
        return

    print("-" * 100)
    summary_df = pd.DataFrame(rows)
    print(
        f"Ortalama: win_rate={summary_df['win_rate'].mean():.2%} "
        f"E[R]={summary_df['expectancy_r'].mean():+.2f} "
        f"Sharpe={summary_df['sharpe'].mean():.2f} "
        f"(toplam islem={int(summary_df['n_trades'].sum())})"
    )

    pooled_trades = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    if not pooled_trades.empty and len(pooled_trades) >= 2:
        r_values = pooled_trades["r_multiple"]
        t = t_statistic(r_values)
        # Coklu-test duzeltmesi (Harvey & Liu 2014, bkz. validation/significance.py):
        # esik, STRATEGY_SIGNAL_FN havuzundaki TOPLAM strateji sayisina gore
        # kademeli sertlesir - yeni bir strateji eklendikce (donchian+price_action=2
        # -> +ma_voting=3) esik otomatik 2.0'dan 3.0'a cikar.
        n_strategies = len(STRATEGY_SIGNAL_FN)
        threshold = multi_test_t_threshold(n_strategies)
        sig = is_significant_multi_test(r_values, n_strategies_tested=n_strategies)
        avg_sharpe = summary_df["sharpe"].mean()
        ci_low, ci_high = sharpe_confidence_interval(avg_sharpe, n_periods=len(pooled_trades))
        print(
            f"Havuzlanmis istatistik: n={len(pooled_trades)} t-stat={t:.2f} "
            f"(anlamli @ t>={threshold} [coklu-test, havuzda {n_strategies} strateji]: {sig}) | "
            f"Sharpe %95 GA ~= [{ci_low:.2f}, {ci_high:.2f}]"
        )


if __name__ == "__main__":
    main()
