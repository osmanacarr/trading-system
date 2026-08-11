"use client";

import { useResearch } from "@/lib/research-context";
import { formatPercent } from "@/lib/format";
import { Panel } from "../ui/Panel";
import { EmptyState } from "../ui/EmptyState";

// research/attribution.py - kapanmis islemlerin getirisini "common"
// (piyasa/beta) ve "specific" (gercek secim becerisi) olarak ayirir.
export function AttributionSummaryPanel() {
  const { summary } = useResearch();
  const attribution = summary?.attribution;
  const hasData = attribution && (attribution.total_common_return !== 0 || attribution.total_specific_return !== 0);

  return (
    <Panel title="attribution — ne kadari beceri, ne kadari piyasa">
      {!hasData ? (
        <EmptyState title="henuz veri yok" hint="kapanan islem/attribution verisi bekleniyor" />
      ) : (
        <div className="px-3 py-3">
          <div className="flex h-3 w-full overflow-hidden rounded-sm border border-term-border">
            <div
              className="bg-term-cyan/70"
              style={{ width: `${Math.min(100, Math.max(0, attribution!.pct_specific * 100))}%` }}
              title="specific (beceri)"
            />
            <div className="flex-1 bg-term-text-faint/30" title="common (piyasa)" />
          </div>
          <div className="mt-2 flex items-center justify-between text-[10px]">
            <span className="text-term-cyan">specific (beceri) {formatPercent(attribution!.pct_specific, 0)}</span>
            <span className="text-term-text-faint">common (piyasa) {formatPercent(1 - attribution!.pct_specific, 0)}</span>
          </div>
        </div>
      )}
    </Panel>
  );
}
