"use client";

import clsx from "clsx";
import { useDashboard } from "@/lib/dashboard-context";
import { PAPER_TRADING_INITIAL_CAPITAL } from "@/lib/constants";
import { formatNumber, formatPercent } from "@/lib/format";
import { Badge } from "./ui/Badge";
import { PulseDot } from "./ui/PulseDot";
import { FlashNumber } from "./ui/FlashNumber";
import { LiveClock } from "./LiveClock";
import type { BadgeTone } from "./ui/Badge";
import type { Summary } from "@/lib/types";

function daysSince(iso: string): number {
  const then = new Date(`${iso}T00:00:00Z`).getTime();
  return Math.floor((Date.now() - then) / 86_400_000);
}

function RunStatusDot({ label, summary }: { label: string; summary: Summary | null }) {
  let tone: BadgeTone = "neutral";
  let title = "Henuz hic calisma yapilmadi";
  if (summary) {
    const age = daysSince(summary.last_updated);
    if (summary.error) {
      tone = "amber";
      title = `Son calistirmada hata: ${summary.error}`;
    } else if (age <= 2) {
      tone = "green";
      title = `Son calisma: ${summary.last_updated} (${age === 0 ? "bugun" : `${age} gun once`})`;
    } else {
      tone = "amber";
      title = `Son calisma ${age} gun once - workflow durmus olabilir`;
    }
  }
  return (
    <span className="flex items-center gap-1.5" title={title}>
      <PulseDot tone={tone} live={tone === "green"} />
      <span className="label-xs text-[9px]">{label}</span>
    </span>
  );
}

export function StatusBar() {
  const { data, setCommandPaletteOpen } = useDashboard();
  const summary = data?.summary ?? null;
  const equity = data?.equity ?? [];

  const latest = equity[equity.length - 1];
  const previous = equity[equity.length - 2];
  const totalEquity = latest?.total_equity ?? summary?.total_equity ?? PAPER_TRADING_INITIAL_CAPITAL;
  const totalChangePct = (totalEquity - PAPER_TRADING_INITIAL_CAPITAL) / PAPER_TRADING_INITIAL_CAPITAL;
  const dailyChangePct = previous && previous.total_equity !== 0 ? (totalEquity - previous.total_equity) / previous.total_equity : null;

  return (
    <div className="flex h-12 shrink-0 items-center justify-between border-b border-term-border bg-term-panel-head px-3">
      <div className="flex items-center gap-3">
        <LiveClock />
        <span className="label-xs text-[10px] hidden sm:inline">paper trading</span>
        <Badge tone="cyan">{summary?.strategy ?? "donchian"}</Badge>
        {summary?.error && <Badge tone="amber">⚠ anomali</Badge>}
        {data?.positionsError && <Badge tone="amber">⚠ pozisyon verisi okunamadi</Badge>}
      </div>

      <div className="flex items-baseline gap-2.5">
        <span className="label-xs text-[9px] hidden md:inline">toplam equity</span>
        <FlashNumber
          value={totalEquity}
          format={(v) => formatNumber(v)}
          pulse
          className="text-lg font-semibold text-term-text"
        />
        <span className={clsx("mono-tabular text-[11px]", totalChangePct >= 0 ? "text-term-green" : "text-term-red")}>
          {totalChangePct >= 0 ? "▲" : "▼"} {formatPercent(totalChangePct)}
        </span>
        {dailyChangePct !== null && (
          <span className={clsx("mono-tabular text-[10px] hidden lg:inline", dailyChangePct >= 0 ? "text-term-green" : "text-term-red")}>
            (gunluk {formatPercent(dailyChangePct)})
          </span>
        )}
      </div>

      <div className="flex items-center gap-4">
        <RunStatusDot label="BIST" summary={summary} />
        <RunStatusDot label="KRIPTO" summary={summary} />
        <span className="label-xs text-[9px] hidden md:inline">
          {summary ? `son calisma ${summary.last_updated}` : "henuz calismadi"}
        </span>
        <button
          onClick={() => setCommandPaletteOpen(true)}
          className="flex items-center gap-1 rounded-sm border border-term-border px-1.5 py-0.5 text-term-text-faint transition-colors hover:border-term-cyan/40 hover:text-term-cyan"
          title="Komut paleti (sembol ara / panele git)"
        >
          <span className="mono-tabular text-[10px]">/</span>
          <span className="label-xs text-[9px] hidden xl:inline">ara</span>
        </button>
      </div>
    </div>
  );
}
