import type { Market } from "./types";

// config.py BIST_TICKERS hepsi ".IS" suffix'li (yfinance formati);
// CRYPTO_TICKERS tek eleman "BTC-USD". Yeni bir kripto ciftinin de
// ".IS" ile bitmemesi yeterli - evren genislerse burada degisiklik gerekmez.
export function classifyMarket(symbol: string): Market {
  return symbol.endsWith(".IS") ? "bist" : "crypto";
}

function istanbulParts(date: Date): { weekday: number; hour: number; minute: number } {
  const fmt = new Intl.DateTimeFormat("en-US", {
    timeZone: "Europe/Istanbul",
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
    hour: parseInt(get("hour"), 10),
    minute: parseInt(get("minute"), 10),
  };
}

// BIST'in gercek islem saatleri (yaklasik, resmi tatil takvimi haric -
// runner.py'nin is_bist_trading_day() ile ayni basitlestirme felsefesi:
// sadece hafta ici + saat araligi kontrolu).
export function isBistOpen(date: Date = new Date()): boolean {
  const { weekday, hour, minute } = istanbulParts(date);
  if (weekday === 0 || weekday === 6) return false;
  const minutes = hour * 60 + minute;
  return minutes >= 10 * 60 && minutes <= 18 * 60 + 10;
}

// Kripto piyasasi 7/24 acik.
export function isCryptoOpen(): boolean {
  return true;
}

export function istanbulTimeString(date: Date = new Date()): string {
  return new Intl.DateTimeFormat("tr-TR", {
    timeZone: "Europe/Istanbul",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}
