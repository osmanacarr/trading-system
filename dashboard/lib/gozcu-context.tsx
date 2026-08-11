"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import type { GozcuMarketKey, GozcuSnapshot } from "./gozcuTypes";

// Gercek veri GitHub Actions'ta ~5 dakikada bir yenileniyor (bkz.
// gozcu/scanner.py, .github/workflows/gozcu_scan.yml) - client'in daha sik
// pollemesi gereksiz, sadece sunucuya yuk bindirir. 30-60sn araliginin
// ortasi secildi; kullaniciya "son guncelleme: X dakika once" acikca
// gosterilir (bkz. SystemHealthPanel) - sahte "her saniye canli" hissi
// VERILMEZ (bkz. gorev tanimi Bolum 0).
const POLL_MS = 45_000;

interface GozcuContextValue {
  snapshot: GozcuSnapshot | null;
  loading: boolean;
  error: string | null;
  lastFetchedAt: Date | null;
  /** true = bu sekmedeki polling DURDURULDU (sadece client-side; arka plandaki GitHub Actions taramasini ETKILEMEZ). */
  killSwitchOn: boolean;
  setKillSwitchOn: (v: boolean) => void;
  activeMarket: GozcuMarketKey;
  setActiveMarket: (m: GozcuMarketKey) => void;
  selectedSymbol: string | null;
  setSelectedSymbol: (s: string | null) => void;
  refetch: () => Promise<void>;
}

const GozcuContext = createContext<GozcuContextValue | null>(null);

export function GozcuProvider({ children }: { children: ReactNode }) {
  const [snapshot, setSnapshot] = useState<GozcuSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastFetchedAt, setLastFetchedAt] = useState<Date | null>(null);
  const [killSwitchOn, setKillSwitchOn] = useState(false);
  const [activeMarket, setActiveMarket] = useState<GozcuMarketKey>("bist");
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const killSwitchRef = useRef(killSwitchOn);
  useEffect(() => {
    killSwitchRef.current = killSwitchOn;
  }, [killSwitchOn]);

  const fetchSnapshot = useCallback(async () => {
    try {
      const res = await fetch("/api/gozcu", { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = (await res.json()) as { snapshot: GozcuSnapshot | null };
      setSnapshot(json.snapshot);
      setError(null);
      setLastFetchedAt(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : "bilinmeyen hata");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSnapshot();
    const id = setInterval(() => {
      if (killSwitchRef.current) return;
      if (document.visibilityState === "hidden") return;
      fetchSnapshot();
    }, POLL_MS);

    function onVisibilityChange() {
      if (document.visibilityState === "visible" && !killSwitchRef.current) {
        fetchSnapshot();
      }
    }
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [fetchSnapshot]);

  return (
    <GozcuContext.Provider
      value={{
        snapshot,
        loading,
        error,
        lastFetchedAt,
        killSwitchOn,
        setKillSwitchOn,
        activeMarket,
        setActiveMarket,
        selectedSymbol,
        setSelectedSymbol,
        refetch: fetchSnapshot,
      }}
    >
      {children}
    </GozcuContext.Provider>
  );
}

export function useGozcu(): GozcuContextValue {
  const ctx = useContext(GozcuContext);
  if (!ctx) throw new Error("useGozcu must be used within GozcuProvider");
  return ctx;
}
