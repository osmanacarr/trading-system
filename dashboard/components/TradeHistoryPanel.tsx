"use client";

import { useMemo, useState } from "react";
import clsx from "clsx";
import { useDashboard } from "@/lib/dashboard-context";
import { exitTrades } from "@/lib/derive";
import { classifyMarket } from "@/lib/market";
import { formatR } from "@/lib/format";
import { Panel } from "./ui/Panel";
import { EmptyState } from "./ui/EmptyState";
import type { Market } from "@/lib/types";

type FilterKey = "all" | Market;
const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "tumu" },
  { key: "bist", label: "bist" },
  { key: "crypto", label: "kripto" },
];

export function TradeHistoryPanel() {
  const { data, selectedSymbol, setSelectedSymbol } = useDashboard();
  const [filter, setFilter] = useState<FilterKey>("all");
  const exits = exitTrades(data?.trades ?? []);

  const filtered = useMemo(() => {
    let rows = [...exits].reverse();
    if (filter !== "all") rows = rows.filter((t) => classifyMarket(t.symbol) === filter);
    if (selectedSymbol) rows = rows.filter((t) => t.symbol === selectedSymbol);
    return rows;
  }, [exits, filter, selectedSymbol]);

  return (
    <Panel
      title="islem gecmisi"
      className="flex-1 min-h-0"
      bodyClassName="flex h-full min-h-0 flex-col"
      right={
        <div className="flex gap-0.5">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={clsx(
                "rounded-sm px-1.5 py-0.5 text-[9px] tracking-wide",
                filter === f.key ? "bg-term-cyan-dim text-term-cyan" : "text-term-text-faint hover:text-term-text-dim"
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
      }
    >
      {selectedSymbol && (
        <button
          onClick={() => setSelectedSymbol(null)}
          className="flex w-full items-center justify-between border-b border-term-border-soft bg-term-cyan-dim px-3 py-1 text-[10px] text-term-cyan"
        >
          <span>sembol: {selectedSymbol}</span>
          <span>✕ temizle</span>
        </button>
      )}
      {filtered.length === 0 ? (
        <EmptyState title="kapanan islem yok" hint={selectedSymbol ? `${selectedSymbol} icin kayit yok` : undefined} />
      ) : (
        <div className="flex-1 min-h-0 overflow-y-auto scroll-thin">
          {filtered.map((t, i) => (
            <div key={`${t.date}-${t.symbol}-${i}`} className="flex items-center justify-between gap-2 border-b border-term-border-soft px-3 py-1.5 text-[11px]">
              <div className="min-w-0">
                <p className="truncate font-medium text-term-text mono-tabular">
                  {t.symbol} <span className={t.direction === 1 ? "text-term-green" : "text-term-red"}>{t.direction === 1 ? "L" : "S"}</span>
                </p>
                <p className="text-[9px] text-term-text-faint">{t.date}</p>
              </div>
              <span className={clsx("mono-tabular text-sm font-semibold shrink-0", (t.r_multiple ?? 0) >= 0 ? "text-term-green" : "text-term-red")}>
                {formatR(t.r_multiple)}
              </span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
