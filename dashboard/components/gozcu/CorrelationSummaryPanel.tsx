"use client";

import { useGozcu } from "@/lib/gozcu-context";
import { formatNumber } from "@/lib/format";
import { Panel } from "../ui/Panel";
import { EmptyState } from "../ui/EmptyState";

export function CorrelationSummaryPanel() {
  const { snapshot, activeMarket } = useGozcu();
  const market = snapshot?.markets?.[activeMarket];
  const corr = market?.correlation.average_correlation ?? null;
  const ref = market?.correlation.reference_ticker ?? null;

  return (
    <Panel title="korelasyon özeti">
      {corr === null ? (
        <EmptyState title="veri yok" hint="referans endeks verisi çekilemedi" />
      ) : (
        <div className="flex flex-col gap-2 px-3 py-3">
          <div className="flex items-baseline justify-between">
            <span className="label-xs text-[9px]">referansla ({ref}) ortalama korelasyon</span>
            <span className="mono-tabular text-lg font-semibold text-term-text">{formatNumber(corr, 2)}</span>
          </div>
          {corr >= 0.7 && (
            <p className="label-xs text-[9px] leading-relaxed text-term-amber">
              ⚠ çoğu hisse aynı yönde hareket ediyor — çeşitlendirme sınırlı olabilir.
            </p>
          )}
        </div>
      )}
    </Panel>
  );
}
