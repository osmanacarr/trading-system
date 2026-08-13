"use client";

import { useMemo, useState } from "react";
import clsx from "clsx";
import { useGozcu } from "@/lib/gozcu-context";
import { formatNumber, formatPercent } from "@/lib/format";
import { Panel } from "../ui/Panel";
import { Badge } from "../ui/Badge";
import { EmptyState } from "../ui/EmptyState";

type SortKey = "symbol" | "daily_change_pct" | "rvol" | "volume_zscore" | "score";

const COLUMNS: { key: SortKey; label: string }[] = [
  { key: "symbol", label: "sembol" },
  { key: "daily_change_pct", label: "günlük %" },
  { key: "rvol", label: "rvol" },
  { key: "volume_zscore", label: "hacim z" },
  { key: "score", label: "dikkat skoru" },
];

// bkz. gozcu/metrics.py::compute_lateness_warning - metnin kendisi zaten
// esigi uyguluyor, burada TEKRAR bir esik sayisi TUTULMAZ (tek kaynak Python
// tarafi) - sadece "GEC KALINMIS" ifadesi geçiyor mu diye bakilir.
function isLate(entry: { lateness_warning?: string }): boolean {
  return entry.lateness_warning?.includes("GEC KALINMIS") ?? false;
}

function pctColor(v: number | null): string {
  if (v === null) return "text-term-text-faint";
  return v >= 0 ? "text-term-green" : "text-term-red";
}

export function AttentionTable() {
  const { snapshot, activeMarket, selectedSymbol, setSelectedSymbol } = useGozcu();
  const market = snapshot?.markets?.[activeMarket];
  const list = useMemo(() => market?.attention_list ?? [], [market]);
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [sortDir, setSortDir] = useState<1 | -1>(-1);

  const sorted = useMemo(() => {
    const copy = [...list];
    copy.sort((a, b) => {
      let cmp: number;
      if (sortKey === "symbol") {
        cmp = a.symbol.localeCompare(b.symbol);
      } else {
        const av = a[sortKey] ?? -Infinity;
        const bv = b[sortKey] ?? -Infinity;
        cmp = av - bv;
      }
      return cmp * sortDir;
    });
    return copy;
  }, [list, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === 1 ? -1 : 1));
    } else {
      setSortKey(key);
      setSortDir(-1);
    }
  }

  return (
    <Panel
      title="dikkat listesi — en çok hareket eden semboller (tavsiye değil, sıralama)"
      right={<span className="label-xs text-[9px]">{list.length} sembol</span>}
    >
      {!market ? (
        <EmptyState title="henüz veri yok" hint="ilk GÖZCÜ taraması bekleniyor" />
      ) : list.length === 0 ? (
        <EmptyState title={market.market_open ? "dikkat çeken hareket yok" : "piyasa kapalı"} />
      ) : (
        <div className="overflow-x-auto scroll-thin">
          <table className="w-full min-w-[560px] text-[11px]">
            <thead>
              <tr className="border-b border-term-border-soft">
                {COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    onClick={() => toggleSort(col.key)}
                    className="cursor-pointer select-none px-3 py-1.5 text-left label-xs text-[9px] hover:text-term-cyan"
                  >
                    {col.label}
                    {sortKey === col.key && <span className="ml-1 text-term-cyan">{sortDir === 1 ? "↑" : "↓"}</span>}
                  </th>
                ))}
                <th className="px-3 py-1.5 text-left label-xs text-[9px]">momentum</th>
                <th className="px-3 py-1.5 text-left label-xs text-[9px]">geç kalma</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((row) => {
                const isSelected = selectedSymbol === row.symbol;
                return (
                  <tr
                    key={row.symbol}
                    onClick={() => setSelectedSymbol(isSelected ? null : row.symbol)}
                    className={clsx(
                      "cursor-pointer border-b border-term-border-soft/60 transition-colors hover:bg-white/[0.02]",
                      isSelected && "bg-term-cyan-dim"
                    )}
                  >
                    <td className="px-3 py-1.5 font-medium text-term-text mono-tabular">{row.symbol}</td>
                    <td className={clsx("px-3 py-1.5 mono-tabular", pctColor(row.daily_change_pct))}>
                      {row.daily_change_pct !== null ? formatPercent(row.daily_change_pct) : "—"}
                    </td>
                    <td className="px-3 py-1.5 mono-tabular text-term-text-dim">
                      {row.rvol !== null ? `${formatNumber(row.rvol, 1)}x` : "—"}
                    </td>
                    <td className="px-3 py-1.5 mono-tabular text-term-text-dim">
                      {row.volume_zscore !== null ? formatNumber(row.volume_zscore, 1) : "—"}
                    </td>
                    <td className="px-3 py-1.5 mono-tabular font-semibold text-term-cyan">
                      {row.score !== null ? formatNumber(row.score, 1) : "—"}
                    </td>
                    <td className="px-3 py-1.5">{row.momentum_candle && <Badge tone="amber">momentum</Badge>}</td>
                    <td className="px-3 py-1.5" title={row.lateness_warning}>
                      {isLate(row) && <Badge tone="red">⚠ GEÇ</Badge>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}
