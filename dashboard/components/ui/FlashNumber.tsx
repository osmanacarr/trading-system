"use client";

import { useEffect, useRef, useState } from "react";
import clsx from "clsx";

/**
 * Deger degistiginde kisa bir yesil/kirmizi flash (700ms) + istege bagli
 * pulse efekti gosteren sayi. "Canli hissi" mikro-animasyonlarindan biri
 * (bkz. dashboard gorsel kimlik gereksinimleri).
 */
export function FlashNumber({
  value,
  format,
  className,
  colorByValue = false,
  pulse = false,
}: {
  value: number;
  format: (v: number) => string;
  className?: string;
  colorByValue?: boolean;
  pulse?: boolean;
}) {
  const prevRef = useRef<number | null>(null);
  const [flash, setFlash] = useState<"up" | "down" | null>(null);

  useEffect(() => {
    if (prevRef.current !== null && prevRef.current !== value) {
      setFlash(value > prevRef.current ? "up" : "down");
      const t = setTimeout(() => setFlash(null), 700);
      prevRef.current = value;
      return () => clearTimeout(t);
    }
    prevRef.current = value;
  }, [value]);

  return (
    <span
      className={clsx(
        "mono-tabular inline-block rounded-sm px-0.5",
        flash === "up" && "animate-flash-green",
        flash === "down" && "animate-flash-red",
        flash && pulse && "animate-pulse-value",
        colorByValue && value > 0 && "text-term-green",
        colorByValue && value < 0 && "text-term-red",
        className
      )}
    >
      {format(value)}
    </span>
  );
}
