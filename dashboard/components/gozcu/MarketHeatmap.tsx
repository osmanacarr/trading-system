"use client";

import { Treemap, ResponsiveContainer, Tooltip } from "recharts";
import type { TreemapNode } from "recharts/types/chart/Treemap";
import { useGozcu } from "@/lib/gozcu-context";
import { formatPercent } from "@/lib/format";
import { Panel } from "../ui/Panel";
import { EmptyState } from "../ui/EmptyState";
import { MarketTabs } from "./MarketTabs";

// Bloomberg/finviz tarzi "piyasa haritasi" (2026-08-13, kullanicinin "duz
// tablo listesinden daha hizli taranabilir gorunum" talebi) - Recharts'ta
// ZATEN kurulu Treemap kullanilir (yeni bagimlilik YOK). Boyut = dikkat
// skoru (gozcu/scoring.py::compute_attention_score - "en cok hareket eden"
// siralamasi, YATIRIM TAVSIYESI DEGIL, bkz. GozcuWarningBanner), renk =
// gunluk % degisim (yesil/kirmizi yogunlugu buyuklukle orantili).

const GREEN_RGB = "0, 214, 143"; // --color-term-green
const RED_RGB = "255, 71, 87"; // --color-term-red

function cellColor(dailyChangePct: number | null): string {
  if (dailyChangePct === null) return "rgba(148, 163, 184, 0.25)"; // notr/veri yok
  const intensity = Math.min(Math.abs(dailyChangePct) / 0.1, 1); // %10+ hareket = tam yoğunluk
  const rgb = dailyChangePct >= 0 ? GREEN_RGB : RED_RGB;
  return `rgba(${rgb}, ${(0.18 + 0.62 * intensity).toFixed(2)})`;
}

function HeatmapCell(props: TreemapNode & { onSelect: (symbol: string) => void }) {
  const { x, y, width, height, name, dailyChangePct, onSelect } = props as unknown as {
    x: number;
    y: number;
    width: number;
    height: number;
    name: string;
    dailyChangePct: number | null;
    onSelect: (symbol: string) => void;
  };
  if (width < 2 || height < 2) return null;
  const showText = width > 46 && height > 26;
  return (
    <g onClick={() => onSelect(name)} className="cursor-pointer">
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={cellColor(dailyChangePct)}
        stroke="var(--color-term-border)"
        strokeWidth={1}
      />
      {showText && (
        <>
          <text x={x + 4} y={y + 14} fontSize={10} fontFamily="var(--font-mono)" fill="var(--color-term-text)">
            {name}
          </text>
          <text x={x + 4} y={y + 26} fontSize={9} fontFamily="var(--font-mono)" fill="var(--color-term-text-dim)">
            {dailyChangePct !== null ? formatPercent(dailyChangePct) : "—"}
          </text>
        </>
      )}
    </g>
  );
}

export function MarketHeatmap() {
  const { snapshot, activeMarket, setSelectedSymbol } = useGozcu();
  const market = snapshot?.markets?.[activeMarket];
  const list = market?.attention_list ?? [];

  const data = list
    .filter((e) => e.score !== null && e.score > 0)
    .map((e) => ({
      name: e.symbol,
      size: e.score as number,
      dailyChangePct: e.daily_change_pct,
    }));

  return (
    <Panel
      title="piyasa haritası — dikkat çeken hareketler (tavsiye değil)"
      right={<MarketTabs />}
    >
      <div className="px-2 py-2">
        {!market || data.length === 0 ? (
          <EmptyState title={market?.market_open ? "dikkat çeken hareket yok" : "piyasa kapalı"} />
        ) : (
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <Treemap
                data={data}
                dataKey="size"
                aspectRatio={4 / 3}
                stroke="var(--color-term-border)"
                content={(props) => <HeatmapCell {...(props as TreemapNode)} onSelect={setSelectedSymbol} />}
                isAnimationActive={false}
              >
                <Tooltip
                  contentStyle={{
                    background: "var(--color-term-panel-head)",
                    border: "1px solid var(--color-term-border)",
                    fontSize: 11,
                  }}
                  formatter={(_value, _name, item) => {
                    const payload = item?.payload as { dailyChangePct?: number | null } | undefined;
                    return [payload?.dailyChangePct !== undefined && payload?.dailyChangePct !== null ? formatPercent(payload.dailyChangePct) : "—", "günlük"];
                  }}
                />
              </Treemap>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </Panel>
  );
}
