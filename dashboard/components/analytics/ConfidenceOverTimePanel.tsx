"use client";

import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useDashboard } from "@/lib/dashboard-context";
import { Panel } from "../ui/Panel";
import { EmptyState } from "../ui/EmptyState";
import type { ConfidencePoint } from "@/lib/stats";

const MIN_TRADES = 5;
const T_THRESHOLD = 2.0;

function TooltipContent({ active, payload }: { active?: boolean; payload?: { payload: ConfidencePoint }[] }) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="rounded-sm border border-term-border bg-term-panel-head px-2.5 py-1.5 text-[11px]">
      <p className="mono-tabular text-term-text-dim">n={point.n}</p>
      <p className="mono-tabular text-term-cyan">t={point.t.toFixed(2)}</p>
    </div>
  );
}

export function ConfidenceOverTimePanel() {
  const { data } = useDashboard();
  const stats = data?.stats;

  return (
    <Panel title="istatistiksel guven (zaman icinde)">
      {!stats || stats.nTrades < MIN_TRADES ? (
        <EmptyState title="yetersiz veri" hint={`en az ${MIN_TRADES} kapanan islem gerekli (su an ${stats?.nTrades ?? 0})`} />
      ) : (
        <div className="h-48 w-full px-2 pb-2 pt-1">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={stats.confidenceOverTime} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid stroke="var(--color-term-border-soft)" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="n"
                tick={{ fill: "var(--color-term-text-faint)", fontSize: 9, fontFamily: "var(--font-mono)" }}
                axisLine={{ stroke: "var(--color-term-border)" }}
                tickLine={false}
                label={{ value: "islem sayisi (n)", position: "insideBottom", offset: -2, fontSize: 9, fill: "var(--color-term-text-faint)" }}
              />
              <YAxis
                tick={{ fill: "var(--color-term-text-faint)", fontSize: 9, fontFamily: "var(--font-mono)" }}
                axisLine={false}
                tickLine={false}
                width={30}
              />
              <ReferenceLine y={T_THRESHOLD} stroke="var(--color-term-amber)" strokeDasharray="4 4" label={{ value: "t=2 esik", fontSize: 9, fill: "var(--color-term-amber)", position: "insideTopRight" }} />
              <ReferenceLine y={-T_THRESHOLD} stroke="var(--color-term-amber)" strokeDasharray="4 4" />
              <Tooltip content={<TooltipContent />} />
              <Line type="monotone" dataKey="t" stroke="var(--color-term-cyan)" strokeWidth={1.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </Panel>
  );
}
