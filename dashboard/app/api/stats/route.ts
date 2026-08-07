import { readJsonl } from "@/lib/readers";
import { TRADES_JSONL_PATH } from "@/lib/paths";
import type { TradeRecord } from "@/lib/types";
import { computeRiskBudget, computeStrategyStats } from "@/lib/derive";
import { sharpeConfidenceInterval } from "@/lib/stats";
import { BACKTEST_BASELINE } from "@/lib/backtestBaseline";

export const dynamic = "force-dynamic";

// Sharpe orani icin gunluk equity getirisi degil, R-katlari uzerinden basit
// bir yaklasim kullanilir (equity.jsonl calistirma-basina bir nokta oldugundan
// gunluk getiri serisi olarak yorumlanamaz - runner.py gunde bir kez calisir
// ama bu her zaman takvim gunu anlamina gelmez, orn. hafta sonu atlanir).
// Bu yuzden Sharpe CI burada R-katlari serisinin ortalama/std'sinden turetilir.
function sharpeFromRValues(rValues: number[]): number {
  if (rValues.length < 2) return 0;
  const mean = rValues.reduce((a, b) => a + b, 0) / rValues.length;
  const variance = rValues.reduce((acc, v) => acc + (v - mean) ** 2, 0) / (rValues.length - 1);
  const std = Math.sqrt(variance);
  return std === 0 ? 0 : mean / std;
}

export async function GET() {
  const trades = readJsonl<TradeRecord>(TRADES_JSONL_PATH);
  const stats = computeStrategyStats(trades);
  const riskBudget = computeRiskBudget(trades);

  const rValues = trades
    .filter((t) => t.event_type === "exit" && t.r_multiple !== null)
    .map((t) => t.r_multiple as number);
  const sharpe = sharpeFromRValues(rValues);
  const sharpeCi = sharpeConfidenceInterval(sharpe, rValues.length);

  return Response.json({
    stats,
    riskBudget,
    sharpe: { value: sharpe, ci: sharpeCi, nTrades: rValues.length },
    backtestBaseline: BACKTEST_BASELINE,
  });
}
