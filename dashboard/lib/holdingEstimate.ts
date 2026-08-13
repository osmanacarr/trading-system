// Donchian (config.BIST_TICKERS, 2018-2026, 675 kapanmis islem) gercek
// tutma-suresi (takvim gunu) dagilimi - "Asama D" analizinden birebir
// mirror'lanir (bkz. ilgili konusma: EREGL/TUPRS gibi acik pozisyonlarin
// "neden hala kapanmadi" sorusuna DURUST, sayisal bir cevap). KESIN bir
// tahmin/garanti DEGILDIR - sadece "backtest'teki normal aralik neresi"
// sorusuna kaba bir referans noktasi verir.
export const DONCHIAN_HOLDING_DAYS: Record<
  1 | -1,
  { median: number; p75: number }
> = {
  1: { median: 22.5, p75: 49 }, // LONG (n=438)
  "-1": { median: 18, p75: 33 }, // SHORT (n=237)
};

export function daysSince(isoDate: string, now: Date = new Date()): number {
  const then = new Date(`${isoDate}T00:00:00Z`).getTime();
  return Math.max(0, Math.round((now.getTime() - then) / 86_400_000));
}

/**
 * Acik bir pozisyonun ne kadar suredir acik oldugunu, backtest'teki
 * medyan/p75 tutma suresiyle kiyaslayip KABA bir beklenti metni uretir.
 * Sadece Donchian icin anlamlidir (mean_reversion'in MAX_HOLD_DAYS=10 ile
 * SABIT bir ustsiniri var, farkli bir mekanizma - bkz. config.py) - bu
 * yuzden strategy!=="donchian" ise null doner (yanlis stratejiye yanlis
 * referansla tahmin uretilmemeli).
 */
export function estimateRemainingHold(
  strategy: string,
  direction: 1 | -1,
  entryDate: string,
  now: Date = new Date()
): string | null {
  if (strategy !== "donchian") return null;
  const open = daysSince(entryDate, now);
  const { median, p75 } = DONCHIAN_HOLDING_DAYS[direction];

  if (open < median) {
    return `muhtemelen ~${Math.round(median - open)} gün daha (medyan ${median}g bazlı)`;
  }
  if (open < p75) {
    return `medyanı (${median}g) geçti, olağan üst sınıra (p75 ${p75}g) kadar ~${Math.round(p75 - open)} gün daha sürebilir`;
  }
  return `olağan aralığın (p75 ${p75}g) dışında — ama trailing-stop'lu bir stratejide bu normal, sabit bir çıkış tarihi yok`;
}
