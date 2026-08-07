import { DashboardProvider } from "@/lib/dashboard-context";
import { StatusBar } from "@/components/StatusBar";
import { StrategySummaryCard } from "@/components/StrategySummaryCard";
import { SystemLog } from "@/components/SystemLog";
import { EquityChart } from "@/components/EquityChart";
import { PositionsTable } from "@/components/PositionsTable";
import { TradeHistoryPanel } from "@/components/TradeHistoryPanel";
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

export default function Home() {
  return (
    <DashboardProvider>
      <div className="flex min-h-screen flex-col">
        <StatusBar />

        <main className="flex-1 space-y-3 px-2 py-3">
          {/* Ana 12-kolon grid: sol (strateji ozeti + gunluk) / orta (equity + pozisyonlar) / sag (islem gecmisi + guven) */}
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
              <div id="panel-positions">
                <PositionsTable />
              </div>
            </div>

            <div className="col-span-12 flex flex-col gap-2 lg:col-span-3">
              <div id="panel-trade-history" className="flex min-h-[280px] flex-1 flex-col">
                <TradeHistoryPanel />
              </div>
              <div id="panel-confidence">
                <StatisticalConfidenceCard />
              </div>
            </div>
          </div>

          {/* Manuel islem takibi: sistemin onerisi vs kullanicinin gercekte actigi islem */}
          <div id="panel-system-vs-real">
            <SystemVsRealPanel />
          </div>

          {/* Ozgun arastirma panelleri - ana panellerle esit oncelikte (bkz. gorev tanimi) */}
          <div>
            <p className="label-xs px-1 pb-1.5 text-[10px]">arastirma panelleri — canli/backtest karsilastirma ve risk analitigi</p>
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
    </DashboardProvider>
  );
}
