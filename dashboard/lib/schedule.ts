// "Ne zaman ne haber gelecek" paneli icin saf fonksiyonlar. Veri dosyasi
// gerektirmez - sabit cron/piyasa-saati tanimlarindan (bkz. .github/workflows/
// paper_trading.yml, gozcu_scan.yml, config.py GOZCU_*_OPEN_TIME) turetilir.
// Intl.DateTimeFormat + explicit timeZone kullanilir (Europe/Istanbul'da DST
// YOK, America/New_York'ta VAR) - IANA tz veritabani DST'yi kendiliginden
// dogru hesaplar, gozcu/market_hours.py'nin Python zoneinfo yaklasimiyla AYNI
// felsefe, burada manuel UTC-offset matematigi YAPILMAZ.

export type JobStatus = "otomatik" | "deneysel-manuel";

export interface ScheduledJob {
  id: string;
  label: string;
  status: JobStatus;
  detail: string;
}

function partsInZone(date: Date, timeZone: string): { weekday: number; hour: number; minute: number } {
  const fmt = new Intl.DateTimeFormat("en-US", {
    timeZone,
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  const parts = fmt.formatToParts(date);
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
  const weekdayMap: Record<string, number> = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
  return {
    weekday: weekdayMap[get("weekday")] ?? 0,
    hour: Number(get("hour")),
    minute: Number(get("minute")),
  };
}

function isWeekdayOpen(date: Date, timeZone: string, openH: number, openM: number, closeH: number, closeM: number): boolean {
  const { weekday, hour, minute } = partsInZone(date, timeZone);
  if (weekday === 0 || weekday === 6) return false;
  const mins = hour * 60 + minute;
  return mins >= openH * 60 + openM && mins <= closeH * 60 + closeM;
}

/** Hafta ici, verilen saat:dakikada bir sonraki olusumu hesaplar (verilen saat GECTIYSE ertesi is gunu). */
function nextWeekdayOccurrence(now: Date, timeZone: string, hour: number, minute: number): Date {
  const candidate = new Date(now);
  for (let i = 0; i < 8; i++) {
    const test = new Date(candidate.getTime() + i * 86_400_000);
    const { weekday, hour: h, minute: m } = partsInZone(test, timeZone);
    if (weekday === 0 || weekday === 6) continue;
    const testMinutes = h * 60 + m;
    const targetMinutes = hour * 60 + minute;
    if (i === 0 && testMinutes >= targetMinutes) continue; // bugun saat gecti, sonrakine bak
    // Bu "gun" (yerel takvimde) icin hedef saate denk gelen UTC anini bul -
    // basit yaklasim: mevcut farktan hareketle dakika bazinda hizala.
    const diffMinutes = targetMinutes - testMinutes;
    return new Date(test.getTime() + diffMinutes * 60_000);
  }
  return candidate;
}

function formatCountdown(now: Date, target: Date): string {
  const ms = target.getTime() - now.getTime();
  if (ms <= 0) return "şimdi";
  const totalMinutes = Math.round(ms / 60_000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours === 0) return `~${minutes} dk sonra`;
  return `~${hours} sa ${minutes} dk sonra`;
}

export function computeScheduledJobs(now: Date = new Date()): ScheduledJob[] {
  const jobs: ScheduledJob[] = [];

  // BIST + kripto paper trading: cron "0 16 * * 1-5" UTC (paper_trading.yml)
  {
    const nextBist = nextWeekdayOccurrence(now, "UTC", 16, 0);
    jobs.push({
      id: "bist-scan",
      label: "BIST taraması (Donchian)",
      status: "otomatik",
      detail: `hafta içi ~19:00 TRT (BIST kapanışından sonra) — sıradaki: ${formatCountdown(now, nextBist)}`,
    });
  }
  {
    // "0 0 * * *" UTC her gun - hafta sonu dahil
    const target = new Date(now);
    target.setUTCHours(24, 0, 0, 0); // bir sonraki UTC gece yarisi
    if (target.getTime() <= now.getTime()) target.setUTCDate(target.getUTCDate() + 1);
    jobs.push({
      id: "crypto-scan",
      label: "Kripto (BTC-USD) taraması",
      status: "otomatik",
      detail: `her gün UTC 00:00 (~03:00 TRT) — sıradaki: ${formatCountdown(now, target)}`,
    });
  }

  // Gozcu: hafta ici, BIST veya NASDAQ aciksa ~2 dk'da bir (harici cron-job.org
  // tetikleyicisi + gozcu_scan.yml debounce - bkz. config.py market saatleri)
  {
    const bistOpen = isWeekdayOpen(now, "Europe/Istanbul", 10, 0, 18, 10);
    const nasdaqOpen = isWeekdayOpen(now, "America/New_York", 9, 30, 16, 0);
    const active = bistOpen || nasdaqOpen;
    jobs.push({
      id: "gozcu-scan",
      label: "Gözcü taraması",
      status: "otomatik",
      detail: active
        ? `şu an AKTİF (${bistOpen ? "BIST" : ""}${bistOpen && nasdaqOpen ? " + " : ""}${nasdaqOpen ? "NASDAQ" : ""} açık) — ~2 dk'da bir tazeleniyor`
        : "şu an PASİF (her iki piyasa da kapalı) — piyasa açıldığında otomatik başlar",
    });
  }

  jobs.push({
    id: "rsi2-scan",
    label: "NASDAQ RSI2 mean-reversion",
    status: "deneysel-manuel",
    detail: "DENEYSEL — otomatik çalışmıyor, sadece --strategies mean_reversion ile manuel/isteğe bağlı çalıştırılır",
  });

  jobs.push({
    id: "dashboard-freshness",
    label: "Bu panelin veri tazeliği",
    status: "otomatik",
    detail: "Gözcü verisi ~15-30 dk'da bir güncellenir (Vercel deploy-kotası nedeniyle debounce'lı); pozisyon/işlem verisi her gerçek paper-trading çalıştırmasında (yukarıdaki BIST/kripto saatleri) güncellenir",
  });

  return jobs;
}
