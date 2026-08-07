"use client";

import { useDashboard } from "@/lib/dashboard-context";
import { Panel } from "../ui/Panel";
import { EmptyState } from "../ui/EmptyState";
import { Badge } from "../ui/Badge";

export function CorrelationWarningPanel() {
  const { data } = useDashboard();
  const warning = data?.correlation;
  const positions = data?.positions ?? [];
  const positionsError = data?.positionsError ?? null;

  return (
    <Panel title="portfoy korelasyon uyarisi">
      {positionsError ? (
        <EmptyState title="degerlendirilemedi" hint="pozisyon verisi okunamadi (bkz. strateji ligi paneli)" />
      ) : positions.length === 0 ? (
        <EmptyState title="acik pozisyon yok" hint="korelasyon riski degerlendirilemez" />
      ) : !warning?.triggered ? (
        <div className="flex h-full flex-col items-center justify-center gap-1.5 px-4 py-6 text-center">
          <Badge tone="green">cesitlendirme normal</Badge>
          <p className="text-[10px] text-term-text-faint">
            {positions.length} acik pozisyon, esik altinda (max grup: {warning?.count ?? 0})
          </p>
        </div>
      ) : (
        <div className="flex h-full flex-col items-center justify-center gap-1.5 px-4 py-6 text-center">
          <Badge tone="amber">⚠ dusuk cesitlendirme</Badge>
          <p className="text-[11px] leading-relaxed text-term-text">
            {warning.count} {warning.market === "bist" ? "BIST" : "kripto"} pozisyonu ayni anda{" "}
            {warning.direction === 1 ? "long" : "short"} — cesitlendirme sinirli olabilir.
          </p>
        </div>
      )}
    </Panel>
  );
}
