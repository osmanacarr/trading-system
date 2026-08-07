// paper_trading hesabi karisik para birimli (BIST=TL, kripto=USD)
// fiyatlari FX donusumu YAPMADAN tek bir sanal equity havuzunda birlestirir
// (runner.py data.fx'i hic cagirmiyor - bilincli basitlestirme, bkz. README).
// Bu yuzden equity gercek bir para birimini temsil etmez; dashboard bunu
// acikca "sanal birim" olarak etiketler, TL/USD sembolu KULLANMAZ.

export function formatNumber(value: number, decimals = 2): string {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function formatSigned(value: number, decimals = 2): string {
  const formatted = formatNumber(Math.abs(value), decimals);
  return value >= 0 ? `+${formatted}` : `-${formatted}`;
}

export function formatPercent(value: number, decimals = 1): string {
  return `${formatSigned(value * 100, decimals)}%`;
}

export function formatR(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return `${formatSigned(value, 2)}R`;
}

export function formatDaysSince(isoDate: string, now: Date = new Date()): string {
  const then = new Date(`${isoDate}T00:00:00Z`).getTime();
  const days = Math.max(0, Math.round((now.getTime() - then) / 86_400_000));
  if (days === 0) return "bugün";
  if (days === 1) return "1 gün";
  return `${days} gün`;
}
