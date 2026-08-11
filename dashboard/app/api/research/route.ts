import { readJson } from "@/lib/readers";
import { RESEARCH_SUMMARY_PATH } from "@/lib/paths";
import type { ResearchSummary } from "@/lib/researchTypes";

export const dynamic = "force-dynamic";

// SADECE research/data/research_summary.json'i okur - hicbir Python
// hesaplamasi burada TEKRARLANMAZ (bkz. research/publish_summary.py
// modul docstring'i, gozcu/scanner.py ile AYNI "tek kaynak" mimarisi).
export async function GET() {
  const summary = readJson<ResearchSummary>(RESEARCH_SUMMARY_PATH);
  return Response.json({
    summary,
    fetchedAt: new Date().toISOString(),
  });
}
