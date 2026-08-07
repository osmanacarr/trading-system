"use client";

import { useDashboard } from "@/lib/dashboard-context";
import { exitTrades, closedRValues } from "@/lib/derive";
import { cumulativeExpectancyR, cumulativeMedianR, cumulativeWinRate } from "@/lib/stats";
import { formatPercent, formatR } from "@/lib/format";
import { Panel } from "./ui/Panel";
import { EmptyState } from "./ui/EmptyState";
import { Sparkline } from "./ui/Sparkline";
import clsx from "clsx";

function Metric({
  label,
  value,
  series,
  tone,
}: {
  label: string;
  value: string;
  series: number[];
  tone: "green" | "red" | "neutral";
}) {
  return (
    <div className="flex items-center justify-between gap-2 border-b border-term-border-soft px-3 py-2.5 last:border-b-0">
      <div>
        <p className="label-xs text-[9px]">{label}</p>
        <p
          className={clsx(
            "mono-tabular text-xl font-semibold",
            tone === "green" && "text-term-green",
            tone === "red" && "text-term-red",
            tone === "neutral" && "text-term-text"
          )}
        >
          {value}
        </p>
      </div>
      <Sparkline values={series} />
    </div>
  );
}

export function StrategySummaryCard() {
  const { data } = useDashboard();
  const trades = data?.trades ?? [];
  const exits = exitTrades(trades);
  const rValues = closedRValues(trades);

  return (
    <Panel title="strateji ozeti">
      {exits.length === 0 ? (
        <EmptyState title="henuz kapanan islem yok" hint="sistem sinyal bekliyor" />
      ) : (
        <div>
          <Metric
            label="win rate"
            value={formatPercent(exits.filter((t) => (t.pnl ?? 0) > 0).length / exits.length, 0)}
            series={cumulativeWinRate(exits.map((t) => t.pnl))}
            tone="neutral"
          />
          <Metric
            label="expectancy (E[R])"
            value={formatR(rValues.reduce((a, b) => a + b, 0) / rValues.length)}
            series={cumulativeExpectancyR(rValues)}
            tone={rValues.reduce((a, b) => a + b, 0) >= 0 ? "green" : "red"}
          />
          <Metric
            label="medyan R"
            value={formatR([...rValues].sort((a, b) => a - b)[Math.floor(rValues.length / 2)])}
            series={cumulativeMedianR(rValues)}
            tone="neutral"
          />
        </div>
      )}
    </Panel>
  );
}
