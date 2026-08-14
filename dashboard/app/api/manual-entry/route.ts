import { appendManualEntry } from "@/lib/readers";
import { fetchRemoteJsonl } from "@/lib/remote-readers";
import type { ManualEntryRecord } from "@/lib/types";

export const dynamic = "force-dynamic";

// GET: Secenek 2 (runtime-fetch) - GitHub'daki manual_trades.jsonl'i okur.
// POST (asagida) DEGISMEDI: appendManualEntry hala YEREL dosya sistemine
// yazmaya calisir ve Vercel'de (salt-okunur fs) beklendigi gibi basarisiz
// olur (bkz. lib/readers.ts appendManualEntry yorumu) - bu route'un yazma
// tarafi zaten GitHub'a degil yerel dosyaya yazacak sekilde tasarlanmisti,
// runtime-fetch migrasyonu SADECE okuma tarafini ilgilendiriyor.
const MANUAL_LOG_REL_PATH = "paper_trading/logs/manual_trades.jsonl";
const CACHE_TTL_MS = 15_000;

export async function GET() {
  const entries = await fetchRemoteJsonl<ManualEntryRecord>(MANUAL_LOG_REL_PATH, CACHE_TTL_MS);
  return Response.json({ entries });
}

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return Response.json({ ok: false, error: "gecersiz JSON govdesi", entry: null }, { status: 400 });
  }

  const { symbol, signal_date, system_entry_price, user_entry_price, user_size, note } =
    (body ?? {}) as Record<string, unknown>;

  if (typeof symbol !== "string" || symbol.trim() === "") {
    return Response.json({ ok: false, error: "symbol zorunlu", entry: null }, { status: 400 });
  }
  if (typeof signal_date !== "string" || signal_date.trim() === "") {
    return Response.json({ ok: false, error: "signal_date zorunlu", entry: null }, { status: 400 });
  }
  if (typeof user_entry_price !== "number" || !Number.isFinite(user_entry_price)) {
    return Response.json({ ok: false, error: "user_entry_price sayi olmali", entry: null }, { status: 400 });
  }
  if (typeof user_size !== "number" || !Number.isFinite(user_size)) {
    return Response.json({ ok: false, error: "user_size sayi olmali", entry: null }, { status: 400 });
  }

  const result = appendManualEntry({
    symbol,
    signal_date,
    system_entry_price: typeof system_entry_price === "number" ? system_entry_price : null,
    user_entry_price,
    user_size,
    note: typeof note === "string" ? note : "",
  });

  if (!result.ok) {
    return Response.json(
      {
        ok: false,
        entry: null,
        error:
          "Kalici kayit basarisiz oldu. Bu, salt-okunur bir dosya sisteminde " +
          "(orn. Vercel serverless production) calisirken BEKLENEN bir durumdur - " +
          "kalici yazma icin yerel `npm run dev` veya kendi sunucunuzu kullanin. " +
          `Teknik detay: ${result.error}`,
      },
      { status: 500 }
    );
  }

  return Response.json({ ok: true, error: null, entry: result.entry });
}
