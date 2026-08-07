"use client";

import { useDashboard } from "@/lib/dashboard-context";
import { Panel } from "../ui/Panel";
import { EmptyState } from "../ui/EmptyState";
import { formatPercent } from "@/lib/format";

export function DataIntegrityPanel() {
  const { data } = useDashboard();
  const integrity = data?.integrity;

  return (
    <Panel title="veri butunlugu">
      {!integrity || integrity.status === "insufficient_data" || integrity.corrections.length === 0 ? (
        <EmptyState title="duzeltme kaydi yok" hint={integrity?.reason ?? "veri bekleniyor"} />
      ) : (
        <div>
          {integrity.corrections.map((c, i) => (
            <div key={i} className="flex items-center justify-between border-b border-term-border-soft px-3 py-1.5 text-[11px] last:border-b-0">
              <span className="mono-tabular text-term-text">{c.symbol}</span>
              <span className="mono-tabular text-term-text-faint">{c.date}</span>
              <span className="mono-tabular text-term-amber">{formatPercent(c.ratio - 1, 1)}</span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
