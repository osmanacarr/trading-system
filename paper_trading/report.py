"""paper_trading/report.py - haftalik ozet raporu (markdown).

Ekip toplantisinda kullanilmak uzere: bu hafta acilan/kapanan islemler,
tum-zamanlar win-rate/expectancy (backtest.metrics ile AYNI fonksiyonlar,
kod tekrari yok), acik pozisyonlar listesi ve baslangica gore equity
degisimi.

Kullanim:
    python -m paper_trading.report
    python -m paper_trading.report --out paper_trading/logs/weekly_report.md
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import pandas as pd

from backtest.metrics import expectancy_r, median_r, win_rate
from config import PAPER_TRADING_INITIAL_CAPITAL
from paper_trading.logger import PaperTradingLogger
from paper_trading.state import PaperTradingState


def generate_weekly_report(
    state: PaperTradingState,
    trade_logger: PaperTradingLogger,
    as_of: dt.date | None = None,
    initial_capital: float = PAPER_TRADING_INITIAL_CAPITAL,
) -> str:
    """Haftalik durum ozetini markdown metni olarak uretir.

    Args:
        state: Guncel acik pozisyonlari okumak icin kullanilan state.
        trade_logger: Trade/equity kayitlarini okumak icin kullanilan logger.
        as_of: Raporun "bugun" kabul ettigi tarih (None ise dt.date.today()).
        initial_capital: Baslangic sanal sermayesi (karsilastirma icin).

    Returns:
        Markdown formatinda rapor metni.
    """
    as_of = as_of or dt.date.today()
    window_start = as_of - dt.timedelta(days=7)

    trades = trade_logger.read_trades()
    equity_log = trade_logger.read_equity()

    if trades.empty:
        entries, exits = trades, trades
    else:
        entries = trades[trades["event_type"] == "entry"]
        exits = trades[trades["event_type"] == "exit"]

    entries_week = _in_window(entries, window_start, as_of)
    exits_week = _in_window(exits, window_start, as_of)

    open_positions = state.list_open_positions()

    if not equity_log.empty:
        latest_equity = float(equity_log["total_equity"].iloc[-1])
    else:
        latest_equity = state.get_equity()
    equity_change = latest_equity - initial_capital
    equity_change_pct = (equity_change / initial_capital) if initial_capital else 0.0

    lines: list[str] = []
    lines.append(f"# Paper Trading Haftalik Ozet — {as_of.isoformat()}")
    lines.append("")
    lines.append(f"## Bu hafta ({window_start.isoformat()} → {as_of.isoformat()})")
    lines.append(f"- Acilan islem: **{len(entries_week)}**")
    lines.append(f"- Kapanan islem: **{len(exits_week)}**")
    lines.append("")
    lines.append(f"## Genel performans (tum zamanlar, {len(exits)} kapanan islem)")
    if exits.empty:
        lines.append("- Henuz kapanan islem yok.")
    else:
        lines.append(f"- Win rate: **{win_rate(exits):.1%}**")
        lines.append(f"- Expectancy (E[R]): **{expectancy_r(exits):+.2f}**")
        lines.append(f"- Medyan R: **{median_r(exits):+.2f}**")
    lines.append("")
    lines.append(f"## Acik pozisyonlar ({len(open_positions)})")
    if not open_positions:
        lines.append("- Acik pozisyon yok.")
    else:
        lines.append("| Sembol | Strateji | Yon | Giris Tarihi | Giris Fiyati | Stop | Boyut |")
        lines.append("|---|---|---|---|---|---|---|")
        for pos in open_positions:
            yon = "LONG" if pos.direction == 1 else "SHORT"
            lines.append(
                f"| {pos.symbol} | {pos.strategy} | {yon} | {pos.entry_date.isoformat()} | "
                f"{pos.entry_price:.4f} | {pos.stop_price:.4f} | {pos.size:.4f} |"
            )
    lines.append("")
    lines.append("## Equity")
    lines.append(f"- Baslangic sermayesi: **{initial_capital:,.2f}**")
    lines.append(f"- Guncel toplam equity: **{latest_equity:,.2f}**")
    lines.append(f"- Degisim: **{equity_change:+,.2f} ({equity_change_pct:+.2%})**")
    lines.append("")

    return "\n".join(lines)


def _in_window(df: pd.DataFrame, start: dt.date, end: dt.date) -> pd.DataFrame:
    if df.empty:
        return df
    dates = df["date"].dt.date
    return df[(dates >= start) & (dates <= end)]


def main(argv: list[str] | None = None) -> None:
    """CLI giris noktasi: raporu stdout'a yazdirir, --out verilirse dosyaya da yazar."""
    parser = argparse.ArgumentParser(description="Paper trading haftalik ozet raporu")
    parser.add_argument("--out", default=None, help="Raporun ayrica yazilacagi dosya yolu (opsiyonel)")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD (opsiyonel; rapor bu tarihe gore uretilir)")
    args = parser.parse_args(argv)

    as_of = dt.date.fromisoformat(args.date) if args.date else None

    with PaperTradingState() as state:
        trade_logger = PaperTradingLogger()
        report = generate_weekly_report(state, trade_logger, as_of=as_of)

    print(report)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
