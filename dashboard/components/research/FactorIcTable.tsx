"use client";

import { useMemo, useState } from "react";
import clsx from "clsx";
import { useResearch } from "@/lib/research-context";
import { formatNumber } from "@/lib/format";
import { Panel } from "../ui/Panel";
import { Badge } from "../ui/Badge";
import { EmptyState } from "../ui/EmptyState";
import type { FactorIcRow } from "@/lib/researchTypes";

type SortKey = "factor_name" | "mean_ic" | "n_dates";

function icColor(v: number | null): string {
  if (v === null) return "text-term-text-faint";
  return v >= 0 ? "text-term-green" : "text-term-red";
}

export function FactorIcTable() {
  const { summary } = useResearch();
  const rows = useMemo(() => summary?.factor_ic ?? [], [summary]);
  const [sortKey, setSortKey] = useState<SortKey>("mean_ic");
  const [sortDir, setSortDir] = useState<1 | -1>(-1);

  const sorted = useMemo(() => {
    const copy = [...rows];
    copy.sort((a: FactorIcRow, b: FactorIcRow) => {
      let cmp: number;
      if (sortKey === "factor_name") {
        cmp = a.factor_name.localeCompare(b.factor_name);
      } else {
        const av = a[sortKey] ?? -Infinity;
        const bv = b[sortKey] ?? -Infinity;
        cmp = av - bv;
      }
      return cmp * sortDir;
    });
    return copy;
  }, [rows, sortKey, sortDir]);

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
      title="faktor IC tablosu — hangi faktor gercekten ongorucu"
      right={<span className="label-xs text-[9px]">{rows.length} faktor</span>}
    >
      {rows.length === 0 ? (
        <EmptyState title="henuz veri yok" hint="research/publish_summary.py ilk kez calistirilmadi" />
      ) : (
        <div className="overflow-x-auto scroll-thin">
          <table className="w-full min-w-[480px] text-[11px]">
            <thead>
              <tr className="border-b border-term-border-soft">
                {(
                  [
                    { key: "factor_name" as const, label: "faktor" },
                    { key: "mean_ic" as const, label: "ortalama IC" },
                    { key: "n_dates" as const, label: "tarih sayisi" },
                  ]
                ).map((col) => (
                  <th
                    key={col.key}
                    onClick={() => toggleSort(col.key)}
                    className="cursor-pointer select-none px-3 py-1.5 text-left label-xs text-[9px] hover:text-term-cyan"
                  >
                    {col.label}
                    {sortKey === col.key && <span className="ml-1 text-term-cyan">{sortDir === 1 ? "↑" : "↓"}</span>}
                  </th>
                ))}
                <th className="px-3 py-1.5 text-left label-xs text-[9px]">decay</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((row) => (
                <tr
                  key={row.factor_name}
                  className="border-b border-term-border-soft/60 transition-colors hover:bg-white/[0.02]"
                >
                  <td className="px-3 py-1.5 font-medium text-term-text mono-tabular">{row.factor_name}</td>
                  <td className={clsx("px-3 py-1.5 mono-tabular", icColor(row.mean_ic))}>
                    {row.mean_ic !== null ? formatNumber(row.mean_ic, 3) : "—"}
                  </td>
                  <td className="px-3 py-1.5 mono-tabular text-term-text-dim">{row.n_dates}</td>
                  <td className="px-3 py-1.5">
                    {row.decayed ? <Badge tone="amber">decay</Badge> : <Badge tone="neutral">stabil</Badge>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {rows.every((r) => r.mean_ic === null) && (
            <p className="px-3 py-2 text-[9px] text-term-text-faint">
              IC henuz hesaplanamiyor — research/factor_history.py gunluk biriktirme her gun bir satir ekler,
              anlamli bir kesitsel IC icin birkac gunluk veri birikmesi gerekir
            </p>
          )}
        </div>
      )}
    </Panel>
  );
}
