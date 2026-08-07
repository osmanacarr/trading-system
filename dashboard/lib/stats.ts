// validation/significance.py + backtest/metrics.py'nin TypeScript portu.
// Formuller Python tarafiyla BIREBIR ayni tutulmustur (bkz. faz3.5_matematiksel_formalizasyon.md SS4);
// tek kaynak (single source of truth) Python tarafidir, burada sadece
// dashboard'un sunucusuz (Vercel) ortamda Python calistirmadan ayni
// sonuclari uretebilmesi icin yeniden yazildi.

function mean(values: number[]): number {
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function sampleStd(values: number[]): number {
  const n = values.length;
  if (n < 2) return 0;
  const m = mean(values);
  const variance = values.reduce((acc, v) => acc + (v - m) ** 2, 0) / (n - 1);
  return Math.sqrt(variance);
}

/** SE(R_bar) = sigma_R / sqrt(n). n < 2 ise 0 doner. */
export function standardErrorR(values: number[]): number {
  const clean = values.filter((v) => Number.isFinite(v));
  const n = clean.length;
  if (n < 2) return 0;
  return sampleStd(clean) / Math.sqrt(n);
}

/** t = R_bar * sqrt(n) / sigma_R. n < 2 veya sigma_R == 0 ise 0 doner. */
export function tStatistic(values: number[]): number {
  const clean = values.filter((v) => Number.isFinite(v));
  const n = clean.length;
  if (n < 2) return 0;
  const se = standardErrorR(clean);
  if (se === 0) return 0;
  return mean(clean) / se;
}

export function isSignificant(values: number[], threshold = 2.0): boolean {
  return Math.abs(tStatistic(values)) >= threshold;
}

/** SE(Sharpe) ~= sqrt((1 + 0.5*Sharpe^2) / n) (Lo, 2002) */
export function sharpeStandardError(sharpe: number, nPeriods: number): number {
  if (nPeriods < 2) return 0;
  return Math.sqrt((1 + 0.5 * sharpe ** 2) / nPeriods);
}

// Standart normal dagilimin ters kumulatif fonksiyonu (Acklam yaklasimi) -
// scipy.stats.norm.ppf'nin bagimliliksiz karsiligi. |hata| < 1.15e-9.
function normInv(p: number): number {
  if (p <= 0 || p >= 1) return NaN;
  const a = [-3.969683028665376e1, 2.209460984245205e2, -2.759285104469687e2, 1.383577518672690e2, -3.066479806614716e1, 2.506628277459239e0];
  const b = [-5.447609879822406e1, 1.615858368580409e2, -1.556989798598866e2, 6.680131188771972e1, -1.328068155288572e1];
  const c = [-7.784894002430293e-3, -3.223964580411365e-1, -2.400758277161838e0, -2.549732539343734e0, 4.374664141464968e0, 2.938163982698783e0];
  const d = [7.784695709041462e-3, 3.224671290700398e-1, 2.445134137142996e0, 3.754408661907416e0];
  const pLow = 0.02425;
  let q: number, r: number;
  if (p < pLow) {
    q = Math.sqrt(-2 * Math.log(p));
    return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  } else if (p <= 1 - pLow) {
    q = p - 0.5;
    r = q * q;
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
  } else {
    q = Math.sqrt(-2 * Math.log(1 - p));
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  }
}

/** (alt_sinir, ust_sinir). n_periods < 2 ise (sharpe, sharpe) doner. */
export function sharpeConfidenceInterval(sharpe: number, nPeriods: number, confidence = 0.95): [number, number] {
  const se = sharpeStandardError(sharpe, nPeriods);
  if (se === 0) return [sharpe, sharpe];
  const z = normInv(1 - (1 - confidence) / 2);
  return [sharpe - z * se, sharpe + z * se];
}

export function winRate(exitTrades: { pnl: number | null }[]): number {
  if (exitTrades.length === 0) return 0;
  const wins = exitTrades.filter((t) => (t.pnl ?? 0) > 0).length;
  return wins / exitTrades.length;
}

export function expectancyR(rValues: number[]): number {
  if (rValues.length === 0) return 0;
  return mean(rValues);
}

export function medianR(rValues: number[]): number {
  if (rValues.length === 0) return 0;
  const sorted = [...rValues].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
}

export interface HistogramBin {
  x0: number;
  x1: number;
  count: number;
}

/** R-katsayisi dagilim histogrami: sabit genislikli binler, [min,max] araligini kapsar. */
export function rHistogram(rValues: number[], binCount = 12): HistogramBin[] {
  if (rValues.length === 0) return [];
  const min = Math.min(...rValues, -1);
  const max = Math.max(...rValues, 1);
  const width = (max - min) / binCount || 1;
  const bins: HistogramBin[] = Array.from({ length: binCount }, (_, i) => ({
    x0: min + i * width,
    x1: min + (i + 1) * width,
    count: 0,
  }));
  for (const r of rValues) {
    let idx = Math.floor((r - min) / width);
    if (idx >= binCount) idx = binCount - 1;
    if (idx < 0) idx = 0;
    bins[idx].count += 1;
  }
  return bins;
}

export interface ConfidencePoint {
  n: number;
  t: number;
}

/** Islem sayisi arttikca t-istatistiginin kumulatif seyri (kronolojik sirada). */
export function tStatOverTime(rValuesChronological: number[]): ConfidencePoint[] {
  const points: ConfidencePoint[] = [];
  for (let n = 2; n <= rValuesChronological.length; n++) {
    points.push({ n, t: tStatistic(rValuesChronological.slice(0, n)) });
  }
  return points;
}

/** Islem sayisi arttikca kumulatif win-rate serisi (StrategySummaryCard sparkline'i icin). */
export function cumulativeWinRate(pnlValues: (number | null)[]): number[] {
  const series: number[] = [];
  let wins = 0;
  pnlValues.forEach((pnl, i) => {
    if ((pnl ?? 0) > 0) wins += 1;
    series.push(wins / (i + 1));
  });
  return series;
}

/** Islem sayisi arttikca kumulatif expectancy_R (ortalama R) serisi. */
export function cumulativeExpectancyR(rValues: number[]): number[] {
  const series: number[] = [];
  let sum = 0;
  rValues.forEach((r, i) => {
    sum += r;
    series.push(sum / (i + 1));
  });
  return series;
}

/** Islem sayisi arttikca kumulatif medyan R serisi. */
export function cumulativeMedianR(rValues: number[]): number[] {
  const series: number[] = [];
  const seen: number[] = [];
  for (const r of rValues) {
    seen.push(r);
    series.push(medianR(seen));
  }
  return series;
}

/**
 * Genellenmis Kelly fraksiyonu, sabit olmayan R-kati dagilimlari icin
 * (bkz. faz3.5_matematiksel_formalizasyon.md SS5: "Kelly'nin genel
 * beklenen-log-getiri versiyonu"). Kucuk-bahis yaklasimi:
 *   f* ~= E[R] / E[R^2]
 * (klasik f* = W/a - L/b sabit-oranli formulunun, R'nin surekli bir
 * rastgele degisken oldugu duruma genellemesi). Guvenilir bir tahmin icin
 * en az 10 kapanan islem gerekir; aksi halde null doner.
 */
export function generalizedKellyFraction(rValues: number[]): number | null {
  const clean = rValues.filter((v) => Number.isFinite(v));
  if (clean.length < 10) return null;
  const eR = mean(clean);
  const eR2 = mean(clean.map((r) => r * r));
  if (eR2 === 0) return null;
  return eR / eR2;
}
