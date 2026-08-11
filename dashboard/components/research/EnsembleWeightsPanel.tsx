"use client";

import clsx from "clsx";
import { useResearch } from "@/lib/research-context";
import { formatNumber } from "@/lib/format";
import { Panel } from "../ui/Panel";
import { Badge } from "../ui/Badge";
import { EmptyState } from "../ui/EmptyState";

export function EnsembleWeightsPanel() {
  const { summary } = useResearch();
  const ensemble = summary?.ensemble;
  const weights = ensemble?.weights ?? [];
  const redundantPairs = ensemble?.redundant_pairs ?? [];

  // Agirliklar IC gerektirir (faktor gecmisi birikmesi gerekir - bkz.
  // FactorIcTable notu), ama korelasyon/redundancy TEK bir gunluk kesitten
  // bile hesaplanabilir (bkz. research/ensemble.py::factor_correlation_matrix) -
  // bu yuzden ikisi BAGIMSIZ olarak gosterilir, biri bos diye digeri
  // gizlenmez.
  const hasWeights = weights.length > 0;
  const hasRedundantPairs = redundantPairs.length > 0;

  return (
    <Panel
      title="ensemble agirliklari — IC-agirlikli kompozit"
      right={hasRedundantPairs ? <Badge tone="amber">{redundantPairs.length} redundant çift</Badge> : undefined}
    >
      {!hasWeights && !hasRedundantPairs ? (
        <EmptyState title="henuz veri yok" />
      ) : (
        <div className="space-y-2 px-3 py-2">
          {hasWeights ? (
            <ul className="space-y-1">
              {weights.map((w) => (
                <li key={w.factor_name} className="flex items-center justify-between text-[11px]">
                  <span className="mono-tabular text-term-text">{w.factor_name}</span>
                  <span
                    className={clsx(
                      "mono-tabular",
                      w.weight === null ? "text-term-text-faint" : w.weight >= 0 ? "text-term-green" : "text-term-red"
                    )}
                  >
                    {w.weight !== null ? formatNumber(w.weight, 3) : "—"}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-[10px] text-term-text-faint">
              agirliklar henuz yok — IC hesaplamak icin faktor gecmisinin birikmesi gerekiyor
            </p>
          )}
          {hasRedundantPairs && (
            <div className="border-t border-term-border-soft pt-2">
              <p className="label-xs text-[9px] text-term-text-faint">yuksek korele ciftler (cesitlendirme saglamaz)</p>
              <ul className="mt-1 space-y-0.5">
                {redundantPairs.map((p) => (
                  <li key={`${p.factor_a}-${p.factor_b}`} className="text-[10px] text-term-text-faint">
                    {p.factor_a} ↔ {p.factor_b} ({p.correlation !== null ? formatNumber(p.correlation, 2) : "—"})
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}
