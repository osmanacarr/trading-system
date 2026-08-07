"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import clsx from "clsx";
import { useDashboard } from "@/lib/dashboard-context";
import { ALL_TICKERS } from "@/lib/tickers";
import { fuzzyMatch } from "@/lib/fuzzy";
import { classifyMarket } from "@/lib/market";

const PANEL_TARGETS: { id: string; label: string }[] = [
  { id: "panel-strategy-summary", label: "strateji ozeti" },
  { id: "panel-system-log", label: "sistem gunlugu" },
  { id: "panel-equity-chart", label: "equity egrisi" },
  { id: "panel-positions", label: "acik pozisyonlar" },
  { id: "panel-trade-history", label: "islem gecmisi" },
  { id: "panel-confidence", label: "istatistiksel guven" },
  { id: "panel-system-vs-real", label: "sistem vs gercek" },
  { id: "panel-live-vs-backtest", label: "canli vs backtest sapma" },
  { id: "panel-r-histogram", label: "r-katsayisi dagilimi" },
  { id: "panel-confidence-over-time", label: "istatistiksel guven (zaman icinde)" },
  { id: "panel-data-integrity", label: "veri butunlugu" },
  { id: "panel-correlation", label: "portfoy korelasyon uyarisi" },
  { id: "panel-risk-budget", label: "risk butcesi" },
];

interface CommandItem {
  type: "symbol" | "panel";
  id: string;
  label: string;
  hint: string;
}

export function CommandPalette() {
  const { commandPaletteOpen, setCommandPaletteOpen, setSelectedSymbol } = useDashboard();
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (commandPaletteOpen) {
      setQuery("");
      setActiveIndex(0);
      const t = setTimeout(() => inputRef.current?.focus(), 0);
      return () => clearTimeout(t);
    }
  }, [commandPaletteOpen]);

  const items = useMemo<CommandItem[]>(() => {
    const symbolItems: CommandItem[] = ALL_TICKERS.filter((t) => fuzzyMatch(query, t)).map((t) => ({
      type: "symbol",
      id: t,
      label: t,
      hint: classifyMarket(t),
    }));
    const panelItems: CommandItem[] = PANEL_TARGETS.filter((p) => fuzzyMatch(query, p.label)).map((p) => ({
      type: "panel",
      id: p.id,
      label: p.label,
      hint: "panel",
    }));
    return [...symbolItems, ...panelItems];
  }, [query]);

  function selectItem(item: CommandItem) {
    if (item.type === "symbol") {
      setSelectedSymbol(item.id);
    } else {
      document.getElementById(item.id)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    setCommandPaletteOpen(false);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, items.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (items[activeIndex]) selectItem(items[activeIndex]);
    }
  }

  if (!commandPaletteOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 pt-[15vh]"
      onClick={() => setCommandPaletteOpen(false)}
    >
      <div
        className="w-full max-w-lg rounded-sm border border-term-border bg-term-panel-head shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 border-b border-term-border px-3 py-2">
          <span className="text-term-cyan mono-tabular">/</span>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setActiveIndex(0);
            }}
            onKeyDown={onKeyDown}
            placeholder="sembol ara veya panele git..."
            className="flex-1 bg-transparent text-sm text-term-text outline-none placeholder:text-term-text-faint mono-tabular"
          />
          <kbd className="label-xs text-[9px]">esc</kbd>
        </div>
        <div className="max-h-80 overflow-y-auto scroll-thin">
          {items.length === 0 ? (
            <p className="px-3 py-4 text-center text-[11px] text-term-text-faint">sonuc yok</p>
          ) : (
            items.map((item, i) => (
              <button
                key={`${item.type}-${item.id}`}
                onClick={() => selectItem(item)}
                onMouseEnter={() => setActiveIndex(i)}
                className={clsx(
                  "flex w-full items-center justify-between px-3 py-2 text-left text-[12px] transition-colors",
                  i === activeIndex ? "bg-term-cyan-dim text-term-cyan" : "text-term-text"
                )}
              >
                <span className="mono-tabular">{item.label}</span>
                <span className="label-xs text-[9px]">{item.hint}</span>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
