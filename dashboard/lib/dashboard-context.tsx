"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import type {
  ActionSheetData,
  EquitySnapshot,
  ManualEntryRecord,
  OpenPosition,
  OpportunitiesData,
  Summary,
  TradeRecord,
} from "./types";
import type { CorrelationWarning, RiskBudget, StrategyStats } from "./derive";
import type { BACKTEST_BASELINE } from "./backtestBaseline";
import type { DataIntegrityStatus } from "./integrity";

export interface DashboardData {
  generatedAt: string;
  summary: Summary | null;
  trades: TradeRecord[];
  equity: EquitySnapshot[];
  positions: OpenPosition[];
  positionsError: string | null;
  manualEntries: ManualEntryRecord[];
  actionSheet: ActionSheetData | null;
  opportunities: OpportunitiesData | null;
  stats: StrategyStats;
  riskBudget: RiskBudget;
  correlation: CorrelationWarning;
  sharpe: { value: number; ci: [number, number]; nTrades: number };
  backtestBaseline: typeof BACKTEST_BASELINE;
  integrity: DataIntegrityStatus;
}

interface DashboardContextValue {
  data: DashboardData | null;
  loading: boolean;
  error: string | null;
  lastFetchedAt: Date | null;
  refetch: () => Promise<void>;
  selectedSymbol: string | null;
  setSelectedSymbol: (symbol: string | null) => void;
  commandPaletteOpen: boolean;
  setCommandPaletteOpen: (open: boolean) => void;
  /** "Bu sinyali aldim" formunun acik oldugu trade (bkz. SystemLog + ManualEntryModal). */
  markingTrade: TradeRecord | null;
  setMarkingTrade: (trade: TradeRecord | null) => void;
}

const DashboardContext = createContext<DashboardContextValue | null>(null);

const POLL_MS = 10_000;

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastFetchedAt, setLastFetchedAt] = useState<Date | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [markingTrade, setMarkingTrade] = useState<TradeRecord | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch("/api/dashboard", { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = (await res.json()) as DashboardData;
      setData(json);
      setError(null);
      setLastFetchedAt(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : "bilinmeyen hata");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, POLL_MS);
    return () => clearInterval(id);
  }, [fetchData]);

  useEffect(() => {
    function onKeydown(e: KeyboardEvent) {
      if (e.key === "/") {
        const target = e.target as HTMLElement | null;
        const isTyping =
          target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable);
        if (!isTyping) {
          e.preventDefault();
          setCommandPaletteOpen(true);
        }
      } else if (e.key === "Escape") {
        setCommandPaletteOpen(false);
      }
    }
    window.addEventListener("keydown", onKeydown);
    return () => window.removeEventListener("keydown", onKeydown);
  }, []);

  return (
    <DashboardContext.Provider
      value={{
        data,
        loading,
        error,
        lastFetchedAt,
        refetch: fetchData,
        selectedSymbol,
        setSelectedSymbol,
        commandPaletteOpen,
        setCommandPaletteOpen,
        markingTrade,
        setMarkingTrade,
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard(): DashboardContextValue {
  const ctx = useContext(DashboardContext);
  if (!ctx) throw new Error("useDashboard must be used within DashboardProvider");
  return ctx;
}
