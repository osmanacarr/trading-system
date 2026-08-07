"use client";

import { useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import clsx from "clsx";
import { useDashboard } from "@/lib/dashboard-context";
import { formatNumber } from "@/lib/format";
import { Panel } from "./ui/Panel";
import { EmptyState } from "./ui/EmptyState";
import { MarketStatusStrip } from "./MarketStatusStrip";
import type { EquitySnapshot } from "@/lib/types";

type RangeKey = "1G" | "1H" | "1A" | "YTD" | "TUMU";
const RANGES: RangeKey[] = ["1G", "1H", "1A", "YTD", "TUMU"];

function cutoffFor(range: RangeKey): Date | null {
  const now = new Date();
  switch (range) {
    case "1G":
      return new Date(now.getTime() - 1 * 86_400_000);
    case "1H":
      return new Date(now.getTime() - 7 * 86_400_000);
    case "1A":
      return new Date(now.getTime() - 30 * 86_400_000);
    case "YTD":
      return new Date(Date.UTC(now.getUTCFullYear(), 0, 1));
    case "TUMU":
      return null;
  }
}

function TooltipContent({ active, payload }: { active?: boolean; payload?: { payload: EquitySnapshot }[] }) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="rounded-sm border border-term-border bg-term-panel-head px-2.5 py-1.5 text-[11px] shadow-lg">
      <p className="label-xs text-[9px]">{point.date}</p>
      <p className="mono-tabular text-term-cyan">{formatNumber(point.total_equity)}</p>
      <p className="mono-tabular text-[10px] text-term-text-dim">acik pozisyon: {point.open_positions}</p>
    </div>
  );
}

export function EquityChart() {
  const { data } = useDashboard();
  const equity = data?.equity ?? [];
  const [range, setRange] = useState<RangeKey>("TUMU");

  const filtered = useMemo(() => {
    const cutoff = cutoffFor(range);
    if (!cutoff) return equity;
    return equity.filter((e) => new Date(`${e.date}T00:00:00Z`) >= cutoff);
  }, [equity, range]);

  const trendUp = filtered.length >= 2 ? filtered[filtered.length - 1].total_equity >= filtered[0].total_equity : true;
  const strokeColor = trendUp ? "var(--color-term-green)" : "var(--color-term-red)";

  return (
    <Panel
      title="equity egrisi"
      right={
        <div className="flex gap-0.5">
          {RANGES.map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={clsx(
                "rounded-sm px-1.5 py-0.5 text-[9px] font-medium tracking-wide transition-colors",
                range === r ? "bg-term-cyan-dim text-term-cyan" : "text-term-text-faint hover:text-term-text-dim"
              )}
            >
              {r}
            </button>
          ))}
        </div>
      }
    >
      {filtered.length < 2 ? (
        <EmptyState
          title="yetersiz veri"
          hint={equity.length === 0 ? "ilk paper trading calistirmasi bekleniyor" : "secili aralikta yeterli nokta yok"}
        />
      ) : (
        <div className="h-56 w-full px-2 pb-2 pt-1">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={filtered} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
              <defs>
                <linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={strokeColor} stopOpacity={0.28} />
                  <stop offset="100%" stopColor={strokeColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="var(--color-term-border-soft)" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="date"
                tick={{ fill: "var(--color-term-text-faint)", fontSize: 9, fontFamily: "var(--font-mono)" }}
                axisLine={{ stroke: "var(--color-term-border)" }}
                tickLine={false}
                minTickGap={40}
              />
              <YAxis
                tick={{ fill: "var(--color-term-text-faint)", fontSize: 9, fontFamily: "var(--font-mono)" }}
                axisLine={false}
                tickLine={false}
                domain={["auto", "auto"]}
                width={52}
              />
              <Tooltip content={<TooltipContent />} />
              <Area type="monotone" dataKey="total_equity" stroke={strokeColor} strokeWidth={1.5} fill="url(#equityFill)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
      <MarketStatusStrip />
    </Panel>
  );
}
