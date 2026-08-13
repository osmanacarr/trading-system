import Link from "next/link";
import { MarketHeatmap } from "./gozcu/MarketHeatmap";
import { PsychologyGauge } from "./gozcu/PsychologyGauge";
import { RegimeIndicatorPanel } from "./research/RegimeIndicatorPanel";

// "Günlük aktif trader" akışının 4. katmanı: "piyasada ne oluyor" - Gözcü
// (dikkat/heatmap + psikoloji) ve Araştırma (rejim) özetlerini TEK kompakt
// bölümde birleştirir. Sayfalar BİRLEŞTİRİLMEDİ (ayrı /gozcu ve /research
// hâlâ var, detay için oraya linklenir) - burada sadece bir özet var.
export function MarketPulseSection() {
  return (
    <div>
      <div className="flex items-center justify-between px-1 pb-1.5">
        <p className="label-xs text-[10px]">piyasa nabzı</p>
        <div className="flex gap-3 text-[9px]">
          <Link href="/gozcu" className="text-term-cyan hover:underline">
            Gözcü&apos;de detay →
          </Link>
          <Link href="/research" className="text-term-cyan hover:underline">
            Araştırma&apos;da detay →
          </Link>
        </div>
      </div>
      <div className="grid grid-cols-12 gap-2">
        <div className="col-span-12 lg:col-span-8">
          <MarketHeatmap />
        </div>
        <div className="col-span-12 flex flex-col gap-2 lg:col-span-4">
          <PsychologyGauge />
          <RegimeIndicatorPanel />
        </div>
      </div>
    </div>
  );
}
