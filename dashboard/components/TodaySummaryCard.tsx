"use client";

import clsx from "clsx";
import { useDashboard } from "@/lib/dashboard-context";
import { Panel } from "./ui/Panel";

// "Günlük aktif trader" akışının 1. katmanı: "bugün ne oldu, ne değişti" -
// tek satırda, en üstte. Yeni bir veri kaynağı gerektirmez, mevcut
// equity.jsonl (son iki snapshot farkı) + actionSheet.entries (is_new_today/
// is_near_stop sayaçları) üzerinden TÜRETİLİR.
export function TodaySummaryCard() {
  const { data } = useDashboard();
  const equity = data?.equity ?? [];
  const entries = data?.actionSheet?.entries ?? [];

  const last = equity[equity.length - 1];
  const prev = equity[equity.length - 2];
  const equityDelta = last && prev && prev.total_equity !== 0 ? ((last.total_equity - prev.total_equity) / prev.total_equity) * 100 : null;

  const newSignals = entries.filter((e) => e.is_new_today).length;
  const nearStop = entries.filter((e) => e.is_near_stop).length;
  const openCount = data?.positions.length ?? 0;

  return (
    <Panel title="bugünün özeti">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 px-3 py-2 text-[12px]">
        <div className="flex items-baseline gap-1.5">
          <span className="label-xs text-[9px] text-term-text-faint">equity (son çalıştırma)</span>
          {equityDelta === null ? (
            <span className="mono-tabular text-term-text-faint">—</span>
          ) : (
            <span className={clsx("mono-tabular font-semibold", equityDelta >= 0 ? "text-term-green" : "text-term-red")}>
              {equityDelta >= 0 ? "+" : ""}
              {equityDelta.toFixed(2)}%
            </span>
          )}
        </div>
        <div className="flex items-baseline gap-1.5">
          <span className="label-xs text-[9px] text-term-text-faint">yeni sinyal</span>
          <span className={clsx("mono-tabular font-semibold", newSignals > 0 ? "text-term-green" : "text-term-text-dim")}>
            {newSignals}
          </span>
        </div>
        <div className="flex items-baseline gap-1.5">
          <span className="label-xs text-[9px] text-term-text-faint">stop&apos;a yaklaşan</span>
          <span className={clsx("mono-tabular font-semibold", nearStop > 0 ? "text-term-amber" : "text-term-text-dim")}>
            {nearStop}
          </span>
        </div>
        <div className="flex items-baseline gap-1.5">
          <span className="label-xs text-[9px] text-term-text-faint">açık pozisyon</span>
          <span className="mono-tabular font-semibold text-term-text">{openCount}</span>
        </div>
      </div>
    </Panel>
  );
}
