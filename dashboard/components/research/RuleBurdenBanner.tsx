"use client";

import { useResearch } from "@/lib/research-context";

// quant2.md - "rule burden": ardisik eklenen cok sayida filtre/kural
// overfitting riskidir. Bu SERT bir engel DEGIL, sadece gorunur bir
// uyaridir (bkz. validation/alpha_evaluation.py::check_rule_burden).
export function RuleBurdenBanner() {
  const { summary } = useResearch();
  const burden = summary?.rule_burden;
  if (!burden || !burden.overfitting_risk) return null;

  return (
    <div className="flex items-center gap-2 rounded-sm border border-term-amber/40 bg-term-amber-dim px-3 py-2 text-[11px] text-term-amber">
      <span>⚠</span>
      <span>
        rule burden uyarisi: {burden.n_filters} aktif filtre (esik={burden.max_filters}) — ardisik eklenen kurallar
        overfitting riskini artirabilir (quant2.md)
      </span>
    </div>
  );
}
