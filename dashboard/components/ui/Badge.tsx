import clsx from "clsx";

export type BadgeTone = "green" | "red" | "amber" | "cyan" | "neutral";

const TONE_CLASSES: Record<BadgeTone, string> = {
  green: "text-term-green border-term-green/40 bg-term-green-dim",
  red: "text-term-red border-term-red/40 bg-term-red-dim",
  amber: "text-term-amber border-term-amber/40 bg-term-amber-dim",
  cyan: "text-term-cyan border-term-cyan/40 bg-term-cyan-dim",
  neutral: "text-term-text-dim border-term-border bg-transparent",
};

export function Badge({ tone, children }: { tone: BadgeTone; children: React.ReactNode }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-sm border px-1.5 py-0.5 text-[10px] font-medium tracking-wide mono-tabular",
        TONE_CLASSES[tone]
      )}
    >
      {children}
    </span>
  );
}
