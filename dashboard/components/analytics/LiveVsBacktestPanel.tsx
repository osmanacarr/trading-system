"use client";

import { useMemo } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useDashboard } from "@/lib/dashboard-context";
import { closedRValues } from "@/lib/derive";
import { formatNumber, formatPercent } from "@/lib/format";
import { Panel } from "../ui/Panel";
import { EmptyState } from "../ui/EmptyState";

const MIN_TRADES_FOR_COMPARISON = 5;

function ComparisonRow({ label, live, backtest, isPercent }: { label: string; live: number; backtest: number; isPercent?: boolean }) {
  const fmt = (v: number) => (isPercent ? formatPercent(v, 0) : formatNumber(v, 2));
  const diverging = Math.sign(live) !== Math.sign(backtest) || Math.abs(live - backtest) / (Math.abs(backtest) || 1) > 0.5;
  return (
    <div className="flex items-center justify-between border-b border-term-border-soft px-3 py-2 last:border-b-0">
      <span className="label-xs text-[9px]">{label}</span>
      <div className="flex items-center gap-3 mono-tabular text-[12px]">
        <span className="text-term-cyan">canli {fmt(live)}</span>
        <span className="text-term-text-faint">vs</span>
        <span className="text-term-text-dim">backtest {fmt(backtest)}</span>
        {diverging && <span className="text-term-amber" title="canli, backtest referansindan belirgin sapiyor">⚠</span>}
      </div>
    </div>
  );
}

export function LiveVsBacktestPanel() {
  const { data } = useDashboard();
  const stats = data?.stats;
  const baseline = data?.backtestBaseline;

  const hasEnoughLiveData = (stats?.nTrades ?? 0) >= MIN_TRADES_FOR_COMPARISON;
  const expectancyBaseline = baseline?.expectancyRPerTrade ?? null;

  const deviationSeries = useMemo(() => {
    if (expectancyBaseline === null) return [];
    const rValues = closedRValues(data?.trades ?? []);
    let cumLive = 0;
    return rValues.map((r, i) => {
      cumLive += r;
      return {
        n: i + 1,
        canli_kumulatif_R: Number(cumLive.toFixed(3)),
        backtest_beklenen_R: Number(((i + 1) * expectancyBaseline).toFixed(3)),
      };
    });
  }, [expectancyBaseline, data?.trades]);

  return (
    <Panel title="canli vs backtest sapma">
      {!hasEnoughLiveData ? (
        <EmptyState
          title="canli veri birikiyor"
          hint={`karsilastirma icin en az ${MIN_TRADES_FOR_COMPARISON} kapanan islem gerekli (su an ${stats?.nTrades ?? 0})`}
        />
      ) : (
        <div>
          <ComparisonRow label="win rate" live={stats!.winRate} backtest={baseline?.winRate ?? 0} isPercent />
          <ComparisonRow label="sharpe (yaklasik)" live={data!.sharpe.value} backtest={baseline?.sharpe ?? 0} />
          {expectancyBaseline === null ? (
            <div className="px-3 py-2">
              <p className="text-[10px] leading-relaxed text-term-text-faint">
                Equity-sapma egrisi icin referans backtest expectancy_R degeri repoda makine-okunur
                olarak commit&apos;lenmemis (bkz. lib/backtestBaseline.ts) - yapi hazir, deger eklenince
                otomatik dolar.
              </p>
            </div>
          ) : (
            <div className="h-40 w-full px-2 pb-2 pt-1">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={deviationSeries} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                  <CartesianGrid stroke="var(--color-term-border-soft)" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="n" tick={{ fontSize: 9, fill: "var(--color-term-text-faint)" }} axisLine={{ stroke: "var(--color-term-border)" }} tickLine={false} />
                  <YAxis tick={{ fontSize: 9, fill: "var(--color-term-text-faint)" }} axisLine={false} tickLine={false} width={30} />
                  <Tooltip />
                  <Legend wrapperStyle={{ fontSize: 9 }} />
                  <Line type="monotone" dataKey="canli_kumulatif_R" stroke="var(--color-term-cyan)" strokeWidth={1.5} dot={false} name="canli" />
                  <Line type="monotone" dataKey="backtest_beklenen_R" stroke="var(--color-term-text-faint)" strokeDasharray="4 4" dot={false} name="backtest beklenen" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}
