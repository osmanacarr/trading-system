import { readJson } from "@/lib/readers";
import { GOZCU_SNAPSHOT_PATH } from "@/lib/paths";
import type { GozcuSnapshot } from "@/lib/gozcuTypes";

export const dynamic = "force-dynamic";

// SADECE gozcu/data/snapshot.json'i okur - hicbir yfinance/ag cagrisi
// YAPMAZ (bkz. gozcu/scanner.py modul docstring'i, "Bolum 0" mimari
// kararu). Kac kullanici sekmesi bu route'u pollersa pollesin, tek
// kaynak (GitHub Actions'ta periyodik calisan scanner) taranir.
export async function GET() {
  const snapshot = readJson<GozcuSnapshot>(GOZCU_SNAPSHOT_PATH);
  return Response.json({
    snapshot,
    fetchedAt: new Date().toISOString(),
  });
}
