"use client";

import { DashboardProvider } from "@/lib/dashboard-context";
import { GozcuProvider } from "@/lib/gozcu-context";
import { ResearchProvider } from "@/lib/research-context";
import { StatusBar } from "@/components/StatusBar";
import { TodaySummaryCard } from "@/components/TodaySummaryCard";
import { ActionRequiredPanel } from "@/components/ActionRequiredPanel";
import { PositionsTable } from "@/components/PositionsTable";
import { ActionSheetPanel } from "@/components/ActionSheetPanel";
import { OpportunitiesPanel } from "@/components/OpportunitiesPanel";
import { MarketPulseSection } from "@/components/MarketPulseSection";
import { ScanScheduleCard } from "@/components/ScanScheduleCard";
import { TradeHistoryPanel } from "@/components/TradeHistoryPanel";
import { StrategySummaryCard } from "@/components/StrategySummaryCard";
import { SystemLog } from "@/components/SystemLog";
import { EquityChart } from "@/components/EquityChart";
import { StatisticalConfidenceCard } from "@/components/StatisticalConfidenceCard";
import { TickerTape } from "@/components/TickerTape";
import { CommandPalette } from "@/components/CommandPalette";
import { ManualEntryModal } from "@/components/ManualEntryModal";
import { SystemVsRealPanel } from "@/components/SystemVsRealPanel";
import { LiveVsBacktestPanel } from "@/components/analytics/LiveVsBacktestPanel";
import { RHistogramPanel } from "@/components/analytics/RHistogramPanel";
import { ConfidenceOverTimePanel } from "@/components/analytics/ConfidenceOverTimePanel";
import { DataIntegrityPanel } from "@/components/analytics/DataIntegrityPanel";
import { CorrelationWarningPanel } from "@/components/analytics/CorrelationWarningPanel";
import { RiskBudgetPanel } from "@/components/analytics/RiskBudgetPanel";

// Sayfa duzeni "gunluk aktif trader" akisini yansitir (2026-08-13, bkz.
// ilgili konusma - kullanicinin "her gun bakan biri icin baglam" talebi):
//   1. Bugun ne oldu, ne degisti      -> TodaySummaryCard
//   2. Bugun/yarin ne yapmam gerekiyor -> ActionRequiredPanel (oncelikli)
//   3. Su an neyi izliyorum            -> PositionsTable (canli fiyat, ETA)
//      + ActionSheetPanel (tam emir talimatlari) + OpportunitiesPanel
//   4. Piyasada ne oluyor              -> MarketPulseSection (Gozcu+Arastirma ozeti)
//   5. Ne zaman yeni bilgi gelecek     -> ScanScheduleCard
// Gecmis islemler AYRI, acik pozisyonlarla KARISMAYAN bir bolumde.
// Strateji ozeti/analitik paneller ALTTA (arka plan bilgisi, gunluk akisin
// disinda ama KALDIRILMADI - hepsi hala erisilebilir).
export default function Home() {
  return (
    <DashboardProvider>
      <GozcuProvider>
        <ResearchProvider>
          <div className="flex min-h-screen flex-col">
            <StatusBar />

            <main className="flex-1 space-y-3 px-2 py-3">
              <div id="panel-today-summary">
                <TodaySummaryCard />
              </div>

              <div id="panel-action-required">
                <ActionRequiredPanel />
              </div>

              <div>
                <p className="label-xs px-1 pb-1.5 text-[10px]">açık pozisyonlarım</p>
                <div className="grid grid-cols-12 gap-2">
                  <div className="col-span-12">
                    <div id="panel-positions">
                      <PositionsTable />
                    </div>
                  </div>
                  <div className="col-span-12" id="panel-action-sheet">
                    <ActionSheetPanel />
                  </div>
                  <div className="col-span-12" id="panel-opportunities">
                    <OpportunitiesPanel />
                  </div>
                </div>
              </div>

              <div id="panel-market-pulse">
                <MarketPulseSection />
              </div>

              <div id="panel-schedule">
                <ScanScheduleCard />
              </div>

              <div>
                <p className="label-xs px-1 pb-1.5 text-[10px]">geçmiş — kapanmış işlemler</p>
                <div id="panel-trade-history" className="min-h-[280px]">
                  <TradeHistoryPanel />
                </div>
              </div>

              <div>
                <p className="label-xs px-1 pb-1.5 text-[10px]">strateji özeti ve arka plan bilgisi</p>
                <div className="grid grid-cols-12 gap-2">
                  <div className="col-span-12 flex flex-col gap-2 lg:col-span-3">
                    <div id="panel-strategy-summary">
                      <StrategySummaryCard />
                    </div>
                    <div id="panel-system-log" className="flex min-h-[280px] flex-1 flex-col">
                      <SystemLog />
                    </div>
                  </div>

                  <div className="col-span-12 flex flex-col gap-2 lg:col-span-6">
                    <div id="panel-equity-chart">
                      <EquityChart />
                    </div>
                  </div>

                  <div className="col-span-12 flex flex-col gap-2 lg:col-span-3">
                    <div id="panel-confidence">
                      <StatisticalConfidenceCard />
                    </div>
                  </div>
                </div>
              </div>

              {/* Manuel islem takibi: sistemin onerisi vs kullanicinin gercekte actigi islem */}
              <div id="panel-system-vs-real">
                <SystemVsRealPanel />
              </div>

              {/* Ozgun arastirma panelleri - ana panellerle esit oncelikte (bkz. gorev tanimi) */}
              <div>
                <p className="label-xs px-1 pb-1.5 text-[10px]">araştırma panelleri — canlı/backtest karşılaştırma ve risk analitiği</p>
                <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-3">
                  <div id="panel-live-vs-backtest">
                    <LiveVsBacktestPanel />
                  </div>
                  <div id="panel-r-histogram">
                    <RHistogramPanel />
                  </div>
                  <div id="panel-confidence-over-time">
                    <ConfidenceOverTimePanel />
                  </div>
                  <div id="panel-data-integrity">
                    <DataIntegrityPanel />
                  </div>
                  <div id="panel-correlation">
                    <CorrelationWarningPanel />
                  </div>
                  <div id="panel-risk-budget">
                    <RiskBudgetPanel />
                  </div>
                </div>
              </div>
            </main>

            <TickerTape />
            <CommandPalette />
            <ManualEntryModal />
          </div>
        </ResearchProvider>
      </GozcuProvider>
    </DashboardProvider>
  );
}
