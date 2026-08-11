import Link from "next/link";
import { ResearchProvider } from "@/lib/research-context";
import { RuleBurdenBanner } from "@/components/research/RuleBurdenBanner";
import { FactorIcTable } from "@/components/research/FactorIcTable";
import { RegimeIndicatorPanel } from "@/components/research/RegimeIndicatorPanel";
import { EnsembleWeightsPanel } from "@/components/research/EnsembleWeightsPanel";
import { AttributionSummaryPanel } from "@/components/research/AttributionSummaryPanel";

export default function ResearchPage() {
  return (
    <ResearchProvider>
      <div className="flex min-h-screen flex-col">
        <div className="flex h-12 shrink-0 items-center justify-between border-b border-term-border bg-term-panel-head px-3">
          <span className="label-xs text-[10px]">ARAŞTIRMA — faktör kütüphanesi, alpha doğrulama, rejim/ensemble</span>
          <Link href="/" className="label-xs text-[9px] text-term-text-faint hover:text-term-cyan">
            ← paper trading paneline dön
          </Link>
        </div>

        <main className="flex-1 space-y-3 px-2 py-3">
          <RuleBurdenBanner />

          <div className="grid grid-cols-12 gap-2">
            <div className="col-span-12 lg:col-span-8">
              <FactorIcTable />
            </div>
            <div className="col-span-12 flex flex-col gap-2 lg:col-span-4">
              <RegimeIndicatorPanel />
              <AttributionSummaryPanel />
            </div>
          </div>

          <EnsembleWeightsPanel />
        </main>
      </div>
    </ResearchProvider>
  );
}
