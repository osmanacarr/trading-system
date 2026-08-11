"use client";

import clsx from "clsx";
import { useResearch } from "@/lib/research-context";
import { Panel } from "../ui/Panel";
import { EmptyState } from "../ui/EmptyState";
import type { RegimeLabel } from "@/lib/researchTypes";

const REGIME_TONE: Record<RegimeLabel, string> = {
  low: "text-term-green",
  normal: "text-term-cyan",
  high: "text-term-amber",
};

const REGIME_TR: Record<RegimeLabel, string> = {
  low: "dusuk",
  normal: "normal",
  high: "yuksek",
};

// research/regime.py - ATR yuzdelik dilimine gore dusuk/normal/yuksek
// volatilite rejimi. Bu panel sadece GOZLEMLER - hicbir parametreyi
// otomatik degistirmez (bkz. modul docstring'i, quant.md "testable
// hypothesis" uyarisi).
export function RegimeIndicatorPanel() {
  const { summary } = useResearch();
  const regime = summary?.regime;

  return (
    <Panel title="volatilite rejimi — evren geneli">
      {!regime || regime.n_symbols === 0 ? (
        <EmptyState title="henuz veri yok" />
      ) : (
        <div className="flex flex-col items-center justify-center gap-2 px-4 py-5 text-center">
          {regime.majority_label ? (
            <p className={clsx("mono-tabular text-lg font-semibold", REGIME_TONE[regime.majority_label])}>
              {REGIME_TR[regime.majority_label]}
            </p>
          ) : (
            <p className="text-term-text-faint">—</p>
          )}
          <div className="flex gap-3 text-[10px] text-term-text-faint">
            <span>
              dusuk <span className="mono-tabular text-term-green">{regime.counts.low}</span>
            </span>
            <span>
              normal <span className="mono-tabular text-term-cyan">{regime.counts.normal}</span>
            </span>
            <span>
              yuksek <span className="mono-tabular text-term-amber">{regime.counts.high}</span>
            </span>
          </div>
          <p className="text-[9px] text-term-text-faint">{regime.n_symbols} sembol uzerinden (son bar)</p>
        </div>
      )}
    </Panel>
  );
}
