"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis, ReferenceLine } from "recharts";
import { useDashboard } from "@/lib/dashboard-context";
import { Panel } from "../ui/Panel";
import { EmptyState } from "../ui/EmptyState";
import type { HistogramBin } from "@/lib/stats";

const MIN_TRADES = 8;

function TooltipContent({ active, payload }: { active?: boolean; payload?: { payload: HistogramBin }[] }) {
  if (!active || !payload?.length) return null;
  const bin = payload[0].payload;
  return (
    <div className="rounded-sm border border-term-border bg-term-panel-head px-2.5 py-1.5 text-[11px]">
      <p className="mono-tabular text-term-text-dim">
        {bin.x0.toFixed(1)}R → {bin.x1.toFixed(1)}R
      </p>
      <p className="mono-tabular text-term-cyan">{bin.count} islem</p>
    </div>
  );
}

export function RHistogramPanel() {
  const { data } = useDashboard();
  const stats = data?.stats;

  return (
    <Panel title="r-katsayisi dagilimi">
      {!stats || stats.nTrades < MIN_TRADES ? (
        <EmptyState title="yetersiz veri" hint={`en az ${MIN_TRADES} kapanan islem gerekli (su an ${stats?.nTrades ?? 0})`} />
      ) : (
        <div className="h-48 w-full px-2 pb-2 pt-1">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={stats.histogram} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid stroke="var(--color-term-border-soft)" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="x0"
                tickFormatter={(v: number) => v.toFixed(1)}
                tick={{ fill: "var(--color-term-text-faint)", fontSize: 9, fontFamily: "var(--font-mono)" }}
                axisLine={{ stroke: "var(--color-term-border)" }}
                tickLine={false}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fill: "var(--color-term-text-faint)", fontSize: 9, fontFamily: "var(--font-mono)" }}
                axisLine={false}
                tickLine={false}
                width={28}
              />
              <ReferenceLine x={0} stroke="var(--color-term-text-faint)" strokeDasharray="2 2" />
              <Tooltip content={<TooltipContent />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
              <Bar dataKey="count" radius={[1, 1, 0, 0]}>
                {stats.histogram.map((bin, i) => (
                  <Cell key={i} fill={bin.x0 < 0 ? "var(--color-term-red)" : "var(--color-term-green)"} fillOpacity={0.75} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="px-1 text-[9px] text-term-text-faint">
            trend-takip imzasi: cogu -1R civari kucuk kayip, saga uzun kuyrukta birkac buyuk kazanc
          </p>
        </div>
      )}
    </Panel>
  );
}
