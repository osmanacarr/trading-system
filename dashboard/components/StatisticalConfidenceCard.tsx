"use client";

import clsx from "clsx";
import { useDashboard } from "@/lib/dashboard-context";
import { formatNumber } from "@/lib/format";
import { Panel } from "./ui/Panel";
import { EmptyState } from "./ui/EmptyState";
import { Badge } from "./ui/Badge";

const T_THRESHOLD = 2.0;
const MIN_TRADES_FOR_ESTIMATE = 5;

export function StatisticalConfidenceCard() {
  const { data } = useDashboard();
  const stats = data?.stats;
  const sharpe = data?.sharpe;

  if (!stats || stats.nTrades < MIN_TRADES_FOR_ESTIMATE) {
    return (
      <Panel title="istatistiksel guven">
        <EmptyState
          title="yetersiz veri"
          hint={`en az ${MIN_TRADES_FOR_ESTIMATE} kapanan islem gerekli (su an ${stats?.nTrades ?? 0})`}
        />
      </Panel>
    );
  }

  return (
    <Panel title="istatistiksel guven">
      <div className="space-y-3 px-3 py-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="label-xs text-[9px]">t-istatistigi</p>
            <p className={clsx("mono-tabular text-xl font-semibold", stats.significant ? "text-term-green" : "text-term-amber")}>
              {formatNumber(stats.tStat, 2)}
            </p>
          </div>
          <Badge tone={stats.significant ? "green" : "amber"}>{stats.significant ? "anlamli (t≥2)" : "henuz anlamli degil"}</Badge>
        </div>
        <div>
          <p className="label-xs text-[9px]">sharpe (R-bazli, %95 GA)</p>
          <p className="mono-tabular text-sm text-term-text">
            {formatNumber(sharpe?.value ?? 0, 2)}
            <span className="text-term-text-faint">
              {" "}[{formatNumber(sharpe?.ci[0] ?? 0, 2)}, {formatNumber(sharpe?.ci[1] ?? 0, 2)}]
            </span>
          </p>
        </div>
        <p className="text-[10px] leading-relaxed text-term-text-faint">
          n={stats.nTrades} kapanan islem. t = R̄·√n/σ_R (faz3.5 §4.1). Esik t=2, ~%95 guven.
        </p>
      </div>
    </Panel>
  );
}
