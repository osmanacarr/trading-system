import { fetchRemoteJson } from "@/lib/remote-readers";
import type { GozcuSnapshot } from "@/lib/gozcuTypes";

export const dynamic = "force-dynamic";

// PILOT (Secenek 2 / runtime-fetch): gozcu/data/snapshot.json artik build-time'da
// pakete gomulu yerel dosyadan degil, GitHub'daki GUNCEL icerikten okunuyor -
// bkz. lib/remote-readers.ts. Hicbir yfinance/ag cagrisi YAPMAZ (bkz.
// gozcu/scanner.py modul docstring'i, "Bolum 0" mimari karari) - tek kaynak
// GitHub Actions'ta periyodik calisan scanner'dir, bu route sadece onun
// yazdigi son snapshot'i GitHub'dan okur (30sn TTL cache ile).
const GOZCU_SNAPSHOT_REL_PATH = "gozcu/data/snapshot.json";
const CACHE_TTL_MS = 30_000;

export async function GET() {
  const snapshot = await fetchRemoteJson<GozcuSnapshot>(GOZCU_SNAPSHOT_REL_PATH, CACHE_TTL_MS);
  return Response.json({
    snapshot,
    fetchedAt: new Date().toISOString(),
  });
}
