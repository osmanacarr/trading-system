"use client";

import { useEffect, useState } from "react";
import { istanbulTimeString } from "@/lib/market";

export function LiveClock() {
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    setNow(new Date());
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <span className="mono-tabular text-[11px] text-term-text-dim" suppressHydrationWarning>
      {now ? istanbulTimeString(now) : "--:--:--"} <span className="text-term-text-faint">TRT</span>
    </span>
  );
}
