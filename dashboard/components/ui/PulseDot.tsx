import clsx from "clsx";
import type { BadgeTone } from "./Badge";

const DOT_CLASSES: Record<BadgeTone, string> = {
  green: "bg-term-green shadow-[0_0_6px_var(--color-term-green)]",
  red: "bg-term-red shadow-[0_0_6px_var(--color-term-red)]",
  amber: "bg-term-amber shadow-[0_0_6px_var(--color-term-amber)]",
  cyan: "bg-term-cyan shadow-[0_0_6px_var(--color-term-cyan)]",
  neutral: "bg-term-text-faint",
};

export function PulseDot({ tone, live = false }: { tone: BadgeTone; live?: boolean }) {
  return (
    <span
      className={clsx(
        "inline-block h-1.5 w-1.5 rounded-full",
        DOT_CLASSES[tone],
        live && "animate-blink-dot"
      )}
    />
  );
}
