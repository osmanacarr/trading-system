"use client";

import { useGozcu } from "@/lib/gozcu-context";
import { Panel } from "../ui/Panel";
import { Badge, type BadgeTone } from "../ui/Badge";
import { EmptyState } from "../ui/EmptyState";

const REGIME_TONE: Record<string, BadgeTone> = {
  normal: "cyan",
  yuksek: "amber",
  asiri: "red",
  bilinmiyor: "neutral",
};

function gaugeColor(pct: number): string {
  if (pct >= 60) return "var(--color-term-green)";
  if (pct <= 40) return "var(--color-term-red)";
  return "var(--color-term-amber)";
}

export function PsychologyGauge() {
  const { snapshot, activeMarket } = useGozcu();
  const market = snapshot?.markets?.[activeMarket];
  const breadth = market?.psychology.breadth_pct ?? null;
  const regime = market?.psychology.volatility_regime ?? "bilinmiyor";

  return (
    <Panel title="piyasa psikolojisi">
      {breadth === null ? (
        <EmptyState title="veri yok" />
      ) : (
        <div className="flex flex-col gap-3 px-3 py-3">
          <div className="flex items-center justify-between">
            <span className="label-xs text-[9px]">pozitif kapanan (breadth)</span>
            <span className="mono-tabular text-lg font-semibold" style={{ color: gaugeColor(breadth) }}>
              {breadth.toFixed(0)}
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-term-border-soft">
            <div
              className="h-full rounded-full transition-all"
              style={{ width: `${Math.max(0, Math.min(100, breadth))}%`, backgroundColor: gaugeColor(breadth) }}
            />
          </div>
          <div className="flex items-center justify-between">
            <span className="label-xs text-[9px]">oynaklık rejimi</span>
            <Badge tone={REGIME_TONE[regime] ?? "neutral"}>{regime}</Badge>
          </div>
          <p className="label-xs text-[8px] leading-relaxed text-term-text-faint">
            bu bir ZAMANLAMA ARACI DEĞİLDİR. korku/coşku dönemleri tarihte uzun sürebilir, tek başına karar vermek için
            kullanılmamalıdır.
          </p>
        </div>
      )}
    </Panel>
  );
}
