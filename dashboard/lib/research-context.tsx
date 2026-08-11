"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import type { ResearchSummary } from "./researchTypes";

// research_summary.json, GOZCU'nun aksine ~5 dakikada bir DEGIL, tipik
// olarak GUNDE BIR (research/factor_history.py toplama + research/
// publish_summary.py yayinlama dongusuyle esgudumlu) guncellenir - bu
// yuzden GOZCU_CONTEXT'teki 45sn'lik siki polling yerine cok daha uzun
// bir aralik yeterli (sunucuya gereksiz yuk bindirmemek icin).
const POLL_MS = 5 * 60_000;

interface ResearchContextValue {
  summary: ResearchSummary | null;
  loading: boolean;
  error: string | null;
  lastFetchedAt: Date | null;
  refetch: () => Promise<void>;
}

const ResearchContext = createContext<ResearchContextValue | null>(null);

export function ResearchProvider({ children }: { children: ReactNode }) {
  const [summary, setSummary] = useState<ResearchSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastFetchedAt, setLastFetchedAt] = useState<Date | null>(null);

  const fetchSummary = useCallback(async () => {
    try {
      const res = await fetch("/api/research", { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = (await res.json()) as { summary: ResearchSummary | null };
      setSummary(json.summary);
      setError(null);
      setLastFetchedAt(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : "bilinmeyen hata");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSummary();
    const id = setInterval(() => {
      if (document.visibilityState === "hidden") return;
      fetchSummary();
    }, POLL_MS);
    return () => clearInterval(id);
  }, [fetchSummary]);

  return (
    <ResearchContext.Provider value={{ summary, loading, error, lastFetchedAt, refetch: fetchSummary }}>
      {children}
    </ResearchContext.Provider>
  );
}

export function useResearch(): ResearchContextValue {
  const ctx = useContext(ResearchContext);
  if (!ctx) throw new Error("useResearch must be used within ResearchProvider");
  return ctx;
}
