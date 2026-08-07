"use client";

import { useDashboard } from "@/lib/dashboard-context";
import { formatPercent } from "@/lib/format";
import { Panel } from "../ui/Panel";
import { EmptyState } from "../ui/EmptyState";

const MIN_TRADES = 10;

export function RiskBudgetPanel() {
  const { data } = useDashboard();
  const budget = data?.riskBudget;

  return (
    <Panel title="risk butcesi">
      {!budget || budget.nTrades < MIN_TRADES || budget.kellyQuarterPct === null ? (
        <EmptyState
          title="yetersiz veri"
          hint={`kelly tahmini icin en az ${MIN_TRADES} kapanan islem gerekli (su an ${budget?.nTrades ?? 0})`}
        />
      ) : (
        <div className="flex items-center justify-around px-3 py-4 text-center">
          <div>
            <p className="label-xs text-[9px]">kullanilan</p>
            <p className="mono-tabular text-lg font-semibold text-term-cyan">{formatPercent(budget.usedRiskPct, 1)}</p>
            <p className="text-[9px] text-term-text-faint">sabit fraksiyonel</p>
          </div>
          <span className="text-term-text-faint">|</span>
          <div>
            <p className="label-xs text-[9px]">hesaplanan kelly/4</p>
            <p
              className={
                "mono-tabular text-lg font-semibold " +
                (budget.kellyQuarterPct >= budget.usedRiskPct ? "text-term-green" : "text-term-amber")
              }
            >
              {formatPercent(budget.kellyQuarterPct, 1)}
            </p>
            <p className="text-[9px] text-term-text-faint">tam kelly f*={budget.kellyFraction?.toFixed(3)}</p>
          </div>
        </div>
      )}
    </Panel>
  );
}
