"use client";

import clsx from "clsx";
import { useGozcu } from "@/lib/gozcu-context";
import { GOZCU_MARKET_LABELS, type GozcuMarketKey } from "@/lib/gozcuTypes";

const MARKETS: GozcuMarketKey[] = ["bist", "nasdaq"];

export function MarketTabs() {
  const { activeMarket, setActiveMarket, snapshot } = useGozcu();

  return (
    <div className="flex gap-1">
      {MARKETS.map((market) => {
        const open = snapshot?.markets?.[market]?.market_open ?? false;
        return (
          <button
            key={market}
            onClick={() => setActiveMarket(market)}
            className={clsx(
              "flex items-center gap-1.5 rounded-sm border px-2.5 py-1 text-[11px] font-medium tracking-wide transition-colors",
              activeMarket === market
                ? "border-term-cyan/40 bg-term-cyan-dim text-term-cyan"
                : "border-term-border text-term-text-dim hover:text-term-text"
            )}
          >
            {GOZCU_MARKET_LABELS[market]}
            <span
              className={clsx("h-1.5 w-1.5 rounded-full", open ? "bg-term-green" : "bg-term-text-faint")}
              title={open ? "piyasa açık" : "piyasa kapalı"}
            />
          </button>
        );
      })}
    </div>
  );
}
