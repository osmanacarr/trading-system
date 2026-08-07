"use client";

import { useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { useDashboard } from "@/lib/dashboard-context";
import { formatR } from "@/lib/format";
import { Panel } from "./ui/Panel";
import { EmptyState } from "./ui/EmptyState";
import type { TradeRecord } from "@/lib/types";

function tradeKey(t: TradeRecord, i: number): string {
  return `${t.date}-${t.symbol}-${t.event_type}-${i}`;
}

function LogLine({ trade, isNew }: { trade: TradeRecord; isNew: boolean }) {
  const dir = trade.direction === 1 ? "LONG" : "SHORT";
  const isEntry = trade.event_type === "entry";
  return (
    <div
      className={clsx(
        "flex items-center justify-between gap-2 border-b border-term-border-soft px-3 py-1.5 text-[11px] last:border-b-0",
        isNew && "animate-slide-in"
      )}
    >
      <div className="flex items-center gap-1.5 min-w-0">
        <span className="mono-tabular text-term-text-faint">{trade.date}</span>
        <span className={clsx("font-semibold", isEntry ? "text-term-cyan" : "text-term-text-dim")}>
          {isEntry ? "GIRIS" : "CIKIS"}
        </span>
        <span className="truncate text-term-text">{trade.symbol}</span>
        <span className={clsx(dir === "LONG" ? "text-term-green" : "text-term-red", "text-[10px]")}>{dir}</span>
        {!isEntry && trade.exit_reason && (
          <span className="text-[10px] text-term-text-faint">({trade.exit_reason})</span>
        )}
      </div>
      {!isEntry && (
        <span className={clsx("mono-tabular shrink-0", (trade.r_multiple ?? 0) >= 0 ? "text-term-green" : "text-term-red")}>
          {formatR(trade.r_multiple)}
        </span>
      )}
    </div>
  );
}

export function SystemLog() {
  const { data } = useDashboard();
  const trades = data?.trades ?? [];
  const prevCountRef = useRef(0);
  const [newKeys, setNewKeys] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (trades.length > prevCountRef.current) {
      const added = trades.slice(prevCountRef.current);
      setNewKeys(new Set(added.map((t, i) => tradeKey(t, prevCountRef.current + i))));
      const timeout = setTimeout(() => setNewKeys(new Set()), 1000);
      prevCountRef.current = trades.length;
      return () => clearTimeout(timeout);
    }
    prevCountRef.current = trades.length;
  }, [trades]);

  const reversed = [...trades].map((t, i) => ({ trade: t, key: tradeKey(t, i) })).reverse();

  return (
    <Panel title="sistem gunlugu" className="flex-1 min-h-0" bodyClassName="h-full overflow-y-auto scroll-thin">
      {reversed.length === 0 ? (
        <EmptyState title="olay yok" hint="ilk sinyal olustugunda burada gorunecek" />
      ) : (
        <div>
          {reversed.map(({ trade, key }) => (
            <LogLine key={key} trade={trade} isNew={newKeys.has(key)} />
          ))}
        </div>
      )}
    </Panel>
  );
}
