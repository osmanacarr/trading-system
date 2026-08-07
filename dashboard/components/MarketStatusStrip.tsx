"use client";

import { useEffect, useState } from "react";
import { isBistOpen, isCryptoOpen, istanbulTimeString } from "@/lib/market";
import { PulseDot } from "./ui/PulseDot";

export function MarketStatusStrip() {
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    setNow(new Date());
    const id = setInterval(() => setNow(new Date()), 30_000);
    return () => clearInterval(id);
  }, []);

  const tick = now ?? new Date(0);
  const bistOpen = now ? isBistOpen(tick) : false;
  const utcTime = now
    ? new Intl.DateTimeFormat("tr-TR", { timeZone: "UTC", hour: "2-digit", minute: "2-digit", hour12: false }).format(tick)
    : "--:--";

  return (
    <div className="flex items-center gap-4 border-t border-term-border-soft px-3 py-1.5 text-[10px]" suppressHydrationWarning>
      <span className="label-xs text-[9px]">piyasa durumu</span>
      <span className="flex items-center gap-1.5">
        <PulseDot tone={bistOpen ? "green" : "neutral"} live={bistOpen} />
        <span className="text-term-text-dim">BIST</span>
        <span className="mono-tabular text-term-text-faint">{bistOpen ? "acik" : "kapali"} · {now ? istanbulTimeString(tick) : "--:--:--"} TRT</span>
      </span>
      <span className="flex items-center gap-1.5">
        <PulseDot tone={isCryptoOpen() ? "green" : "neutral"} live />
        <span className="text-term-text-dim">BTC-USD</span>
        <span className="mono-tabular text-term-text-faint">7/24 · {utcTime} UTC</span>
      </span>
    </div>
  );
}
