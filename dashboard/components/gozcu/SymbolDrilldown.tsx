"use client";

import { CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useGozcu } from "@/lib/gozcu-context";
import { formatNumber, formatPercent } from "@/lib/format";
import { Panel } from "../ui/Panel";
import { EmptyState } from "../ui/EmptyState";
import { Badge } from "../ui/Badge";

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-term-border-soft/60 px-3 py-1">
      <span className="label-xs text-[9px]">{label}</span>
      <span className="mono-tabular text-[11px] text-term-text">{value}</span>
    </div>
  );
}

function pct(v: number | null): string {
  return v === null ? "—" : formatPercent(v);
}

function num(v: number | null, decimals = 2): string {
  return v === null ? "—" : formatNumber(v, decimals);
}

export function SymbolDrilldown() {
  const { snapshot, activeMarket, selectedSymbol, setSelectedSymbol } = useGozcu();
  const market = snapshot?.markets?.[activeMarket];
  const entry = market?.attention_list.find((row) => row.symbol === selectedSymbol) ?? null;

  if (!selectedSymbol || !entry) return null;

  const chartData = entry.intraday.times.map((t, i) => ({
    time: new Date(t).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" }),
    price: entry.intraday.price[i],
    vwap: entry.intraday.vwap[i],
  }));

  return (
    <Panel
      title={`sembol detayı — ${entry.symbol}`}
      right={
        <button
          onClick={() => setSelectedSymbol(null)}
          className="label-xs text-[9px] text-term-text-faint hover:text-term-cyan"
        >
          kapat ✕
        </button>
      }
    >
      <div className="flex flex-col gap-2 px-2 py-2">
        {chartData.length < 2 ? (
          <EmptyState title="gün içi veri yok" hint="piyasa kapalıyken veya ilk barlarda mini-grafik boş kalabilir" />
        ) : (
          <div className="h-40 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                <CartesianGrid stroke="var(--color-term-border-soft)" strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="time"
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
                <Tooltip
                  contentStyle={{
                    background: "var(--color-term-panel-head)",
                    border: "1px solid var(--color-term-border)",
                    fontSize: 11,
                  }}
                />
                <Line type="monotone" dataKey="price" stroke="var(--color-term-cyan)" strokeWidth={1.5} dot={false} name="fiyat" />
                <Line
                  type="monotone"
                  dataKey="vwap"
                  stroke="var(--color-term-amber)"
                  strokeWidth={1.5}
                  dot={false}
                  strokeDasharray="4 2"
                  name="VWAP"
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
        <div className="flex flex-wrap gap-1 px-1">
          {entry.momentum_candle && <Badge tone="amber">momentum mumu</Badge>}
          <Badge tone="cyan">skor {num(entry.score, 1)}</Badge>
        </div>
        <div
          className={
            entry.lateness_warning?.includes("GEC KALINMIS")
              ? "rounded-sm border border-term-red/30 bg-term-red-dim px-2 py-1.5"
              : "rounded-sm border border-term-border-soft bg-term-bg-1/40 px-2 py-1.5"
          }
        >
          <p
            className={
              entry.lateness_warning?.includes("GEC KALINMIS")
                ? "text-[10px] leading-relaxed text-term-red"
                : "text-[10px] leading-relaxed text-term-text-dim"
            }
          >
            <span className="font-semibold">⏱ GEÇ KALMA KONTROLÜ:</span>{" "}
            {entry.lateness_warning ?? "henüz hesaplanmadı (bu sembol için tarama bekleniyor)"}
          </p>
        </div>
        <div className="rounded-sm border border-term-border-soft">
          <MetricRow label="son fiyat" value={num(entry.last_price, 4)} />
          <MetricRow label="günlük % değişim" value={pct(entry.daily_change_pct)} />
          <MetricRow label="haftalık % değişim" value={pct(entry.weekly_change_pct)} />
          <MetricRow label="RVOL" value={entry.rvol !== null ? `${num(entry.rvol, 2)}x` : "—"} />
          <MetricRow label="hacim z-skoru" value={num(entry.volume_zscore, 2)} />
          <MetricRow label="VWAP" value={num(entry.vwap, 4)} />
          <MetricRow label="VWAP'a göre konum" value={pct(entry.vwap_position_pct)} />
          <MetricRow label="VWAP eğimi" value={num(entry.vwap_slope, 4)} />
          <MetricRow label="52 hafta zirveye uzaklık" value={pct(entry.distance_from_52w_high)} />
          <MetricRow label="52 hafta dibe uzaklık" value={pct(entry.distance_from_52w_low)} />
          <MetricRow label="ATR yüzdelik dilimi" value={entry.atr_percentile !== null ? `%${num(entry.atr_percentile, 0)}` : "—"} />
        </div>
      </div>
    </Panel>
  );
}
