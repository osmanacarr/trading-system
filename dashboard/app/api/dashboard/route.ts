import { readJson, readJsonl, readOpenPositions } from "@/lib/readers";
import {
  ACTION_SHEET_JSON_PATH,
  EQUITY_JSONL_PATH,
  MANUAL_LOG_PATH,
  OPPORTUNITIES_JSON_PATH,
  SUMMARY_JSON_PATH,
  TRADES_JSONL_PATH,
} from "@/lib/paths";
import type {
  ActionSheetData,
  EquitySnapshot,
  ManualEntryRecord,
  OpportunitiesData,
  PricedOpenPosition,
  Summary,
  TradeRecord,
} from "@/lib/types";
import { computeCorrelationWarning, computeRiskBudget, computeStrategyStats } from "@/lib/derive";
import { sharpeConfidenceInterval } from "@/lib/stats";
import { BACKTEST_BASELINE } from "@/lib/backtestBaseline";
import { DATA_INTEGRITY_STATUS } from "@/lib/integrity";

export const dynamic = "force-dynamic";

// Sayfanin ihtiyac duydugu her seyi TEK istekte doner (client'in her poll'da
// 6 ayri route'a paralel istek atmasi yerine) - bkz. app/page.tsx polling.
// Tekil kaynaklara (/api/trades, /api/positions, ...) yine de dogrudan
// erisim korunuyor: hem test/debug icin hem de tek bir veri kaynaginin
// dashboard disinda tuketilmesi icin.
export async function GET() {
  const summary = readJson<Summary>(SUMMARY_JSON_PATH);
  const trades = readJsonl<TradeRecord>(TRADES_JSONL_PATH);
  const equity = readJsonl<EquitySnapshot>(EQUITY_JSONL_PATH);
  const { positions: rawPositions, error: positionsError } = readOpenPositions();
  const manualEntries = readJsonl<ManualEntryRecord>(MANUAL_LOG_PATH);
  const actionSheet = readJson<ActionSheetData>(ACTION_SHEET_JSON_PATH);
  const opportunities = readJson<OpportunitiesData>(OPPORTUNITIES_JSON_PATH);

  // 2026-08-13: state.db'nin acik pozisyon listesi (rawPositions) fiyatsizdir
  // (bkz. lib/types.ts OpenPosition yorumu); action_sheet.json ise AYNI
  // sembolleri (symbol,strategy) icin CANLI fiyatla tasir (Python tarafinda
  // refresh_live_prices() ile ~2 dk'da bir tazelenir). Iki ayri panel iki
  // ayri kaynaktan besleninceye kadar tutarsiz gorunuyordu (ActionSheetPanel
  // fiyatli, ana tablo "n/a") - burada TEK SEFERDE join edilip TUM cagiran
  // bilesenlere (PositionsTable dahil) ayni, fiyatli obje verilir.
  const priceBySymbolStrategy = new Map(
    (actionSheet?.entries ?? []).map((e) => [`${e.symbol}::${e.strategy}`, e])
  );
  const positions: PricedOpenPosition[] = rawPositions.map((pos) => {
    const priced = priceBySymbolStrategy.get(`${pos.symbol}::${pos.strategy}`);
    return {
      ...pos,
      current_price: priced?.current_price ?? null,
      unrealized_pnl_pct: priced?.unrealized_pnl_pct ?? null,
      stop_distance_pct: priced?.stop_distance_pct ?? null,
      is_near_stop: priced?.is_near_stop ?? false,
    };
  });

  const stats = computeStrategyStats(trades);
  const riskBudget = computeRiskBudget(trades);
  const correlation = computeCorrelationWarning(positions);

  const rValues = trades
    .filter((t) => t.event_type === "exit" && t.r_multiple !== null)
    .map((t) => t.r_multiple as number);
  const mean = rValues.length ? rValues.reduce((a, b) => a + b, 0) / rValues.length : 0;
  const std =
    rValues.length > 1
      ? Math.sqrt(rValues.reduce((acc, v) => acc + (v - mean) ** 2, 0) / (rValues.length - 1))
      : 0;
  const sharpe = std === 0 ? 0 : mean / std;
  const sharpeCi = sharpeConfidenceInterval(sharpe, rValues.length);

  return Response.json({
    generatedAt: new Date().toISOString(),
    summary,
    trades,
    equity,
    positions,
    positionsError,
    manualEntries,
    actionSheet,
    opportunities,
    stats,
    riskBudget,
    correlation,
    sharpe: { value: sharpe, ci: sharpeCi, nTrades: rValues.length },
    backtestBaseline: BACKTEST_BASELINE,
    integrity: DATA_INTEGRITY_STATUS,
  });
}
