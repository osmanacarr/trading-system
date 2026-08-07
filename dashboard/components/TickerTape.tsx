"use client";

import clsx from "clsx";
import { useDashboard } from "@/lib/dashboard-context";
import { formatR } from "@/lib/format";
import type { TradeRecord } from "@/lib/types";

function TickerItem({ trade }: { trade: TradeRecord }) {
  const dir = trade.direction === 1 ? "LONG" : "SHORT";
  const isEntry = trade.event_type === "entry";
  return (
    <span className="mono-tabular flex items-center gap-1.5 whitespace-nowrap px-4 text-[11px]">
      <span className="text-term-text-faint">{trade.date}</span>
      <span className="font-semibold text-term-text">{trade.symbol}</span>
      <span className={dir === "LONG" ? "text-term-green" : "text-term-red"}>{dir}</span>
      <span className="text-term-text-dim">{isEntry ? "GIRIS" : "CIKIS"}</span>
      {!isEntry && (
        <span className={clsx("font-semibold", (trade.r_multiple ?? 0) >= 0 ? "text-term-green" : "text-term-red")}>
          {formatR(trade.r_multiple)}
        </span>
      )}
      <span className="text-term-border">│</span>
    </span>
  );
}

export function TickerTape() {
  const { data } = useDashboard();
  const trades = (data?.trades ?? []).slice(-24).reverse();

  if (trades.length === 0) {
    return (
      <div className="flex h-7 shrink-0 items-center border-t border-term-border bg-term-panel-head px-3">
        <span className="label-xs text-[9px]">henuz islem/sinyal yok - sistem sinyal bekliyor</span>
      </div>
    );
  }

  return (
    <div className="group flex h-7 shrink-0 items-center overflow-hidden border-t border-term-border bg-term-panel-head">
      <div className="flex animate-ticker group-hover:[animation-play-state:paused]">
        <div className="flex shrink-0">
          {trades.map((t, i) => (
            <TickerItem key={`a-${i}`} trade={t} />
          ))}
        </div>
        <div className="flex shrink-0" aria-hidden>
          {trades.map((t, i) => (
            <TickerItem key={`b-${i}`} trade={t} />
          ))}
        </div>
      </div>
    </div>
  );
}
