export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex h-full min-h-[80px] flex-col items-center justify-center gap-1 px-4 py-6 text-center">
      <p className="label-xs text-[10px] text-term-text-faint">{title}</p>
      {hint && <p className="mono-tabular text-[11px] text-term-text-faint/80">{hint}</p>}
    </div>
  );
}
