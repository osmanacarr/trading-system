import { fetchRemoteJson } from "@/lib/remote-readers";
import type { ResearchSummary } from "@/lib/researchTypes";

export const dynamic = "force-dynamic";

// Secenek 2 (runtime-fetch, bkz. lib/remote-readers.ts): artik build-time'da
// pakete gomulu yerel dosya yerine GitHub'daki GUNCEL icerikten okunuyor.
// SADECE research/data/research_summary.json'i okur - hicbir Python
// hesaplamasi burada TEKRARLANMAZ (bkz. research/publish_summary.py
// modul docstring'i, gozcu/scanner.py ile AYNI "tek kaynak" mimarisi).
const RESEARCH_SUMMARY_REL_PATH = "research/data/research_summary.json";
const CACHE_TTL_MS = 120_000;

export async function GET() {
  const summary = await fetchRemoteJson<ResearchSummary>(RESEARCH_SUMMARY_REL_PATH, CACHE_TTL_MS);
  return Response.json({
    summary,
    fetchedAt: new Date().toISOString(),
  });
}
