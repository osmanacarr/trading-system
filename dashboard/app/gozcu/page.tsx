import Link from "next/link";
import { GozcuProvider } from "@/lib/gozcu-context";
import { GozcuWarningBanner } from "@/components/gozcu/GozcuWarningBanner";
import { MarketTabs } from "@/components/gozcu/MarketTabs";
import { AttentionTable } from "@/components/gozcu/AttentionTable";
import { PsychologyGauge } from "@/components/gozcu/PsychologyGauge";
import { CorrelationSummaryPanel } from "@/components/gozcu/CorrelationSummaryPanel";
import { SystemHealthPanel } from "@/components/gozcu/SystemHealthPanel";
import { SymbolDrilldown } from "@/components/gozcu/SymbolDrilldown";

export default function GozcuPage() {
  return (
    <GozcuProvider>
      <div className="flex min-h-screen flex-col">
        <GozcuWarningBanner />

        <div className="flex h-12 shrink-0 items-center justify-between border-b border-term-border bg-term-panel-head px-3">
          <div className="flex items-center gap-3">
            <span className="label-xs text-[10px]">GÖZCÜ — canlı izleme</span>
            <MarketTabs />
          </div>
          <Link href="/" className="label-xs text-[9px] text-term-text-faint hover:text-term-cyan">
            ← paper trading paneline dön
          </Link>
        </div>

        <main className="flex-1 space-y-3 px-2 py-3">
          <div className="grid grid-cols-12 gap-2">
            <div className="col-span-12 lg:col-span-8">
              <AttentionTable />
            </div>
            <div className="col-span-12 flex flex-col gap-2 lg:col-span-4">
              <PsychologyGauge />
              <CorrelationSummaryPanel />
              <SystemHealthPanel />
            </div>
          </div>
          <SymbolDrilldown />
        </main>
      </div>
    </GozcuProvider>
  );
}
