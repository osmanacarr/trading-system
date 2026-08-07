import type { OpenPosition, TradeRecord } from "./types";
import { classifyMarket } from "./market";
import {
  expectancyR,
  generalizedKellyFraction,
  medianR,
  rHistogram,
  tStatistic,
  tStatOverTime,
  winRate,
  type HistogramBin,
  type ConfidencePoint,
} from "./stats";

export function exitTrades(trades: TradeRecord[]): TradeRecord[] {
  return trades.filter((t) => t.event_type === "exit");
}

export function closedRValues(trades: TradeRecord[]): number[] {
  return exitTrades(trades)
    .map((t) => t.r_multiple)
    .filter((r): r is number => r !== null && Number.isFinite(r));
}

export interface StrategyStats {
  nTrades: number;
  winRate: number;
  expectancyR: number;
  medianR: number;
  tStat: number;
  significant: boolean;
  histogram: HistogramBin[];
  confidenceOverTime: ConfidencePoint[];
}

const T_THRESHOLD = 2.0; // config.py SIGNIFICANCE_T_THRESHOLD

export function computeStrategyStats(trades: TradeRecord[]): StrategyStats {
  const exits = exitTrades(trades);
  const rValues = closedRValues(trades);
  const t = tStatistic(rValues);
  return {
    nTrades: exits.length,
    winRate: winRate(exits),
    expectancyR: expectancyR(rValues),
    medianR: medianR(rValues),
    tStat: t,
    significant: Math.abs(t) >= T_THRESHOLD,
    histogram: rHistogram(rValues),
    confidenceOverTime: tStatOverTime(rValues),
  };
}

export interface CorrelationWarning {
  triggered: boolean;
  market: "bist" | "crypto" | null;
  direction: 1 | -1 | null;
  count: number;
}

const CORRELATION_THRESHOLD = 3; // "N'den fazla" - ayni yon+piyasada N pozisyon esiginde uyar

export function computeCorrelationWarning(positions: OpenPosition[]): CorrelationWarning {
  const groups = new Map<string, number>();
  for (const pos of positions) {
    const market = classifyMarket(pos.symbol);
    const key = `${market}:${pos.direction}`;
    groups.set(key, (groups.get(key) ?? 0) + 1);
  }
  let worst: { market: "bist" | "crypto"; direction: 1 | -1; count: number } | null = null;
  for (const [key, count] of groups) {
    if (!worst || count > worst.count) {
      const [market, dir] = key.split(":");
      worst = { market: market as "bist" | "crypto", direction: Number(dir) as 1 | -1, count };
    }
  }
  if (!worst || worst.count < CORRELATION_THRESHOLD) {
    return { triggered: false, market: null, direction: null, count: worst?.count ?? 0 };
  }
  return { triggered: true, market: worst.market, direction: worst.direction, count: worst.count };
}

export interface RiskBudget {
  usedRiskPct: number; // config.py RISK_PER_TRADE
  kellyFraction: number | null; // tam Kelly
  kellyQuarterPct: number | null; // fractional-Kelly/4, yuzde olarak
  nTrades: number;
}

const RISK_PER_TRADE = 0.01; // config.py

export function computeRiskBudget(trades: TradeRecord[]): RiskBudget {
  const rValues = closedRValues(trades);
  const kelly = generalizedKellyFraction(rValues);
  return {
    usedRiskPct: RISK_PER_TRADE,
    kellyFraction: kelly,
    kellyQuarterPct: kelly !== null ? (kelly / 4) : null,
    nTrades: rValues.length,
  };
}
