import { readJson, readJsonl, readOpenPositions } from "@/lib/readers";
import { EQUITY_JSONL_PATH, SUMMARY_JSON_PATH, TRADES_JSONL_PATH } from "@/lib/paths";
import type { EquitySnapshot, Summary, TradeRecord } from "@/lib/types";
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
  const { positions, error: positionsError } = readOpenPositions();

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
    stats,
    riskBudget,
    correlation,
    sharpe: { value: sharpe, ci: sharpeCi, nTrades: rValues.length },
    backtestBaseline: BACKTEST_BASELINE,
    integrity: DATA_INTEGRITY_STATUS,
  });
}
