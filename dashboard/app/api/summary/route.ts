import { fetchRemoteJson } from "@/lib/remote-readers";
import type { Summary } from "@/lib/types";

export const dynamic = "force-dynamic";

const SUMMARY_JSON_REL_PATH = "paper_trading/logs/summary.json";
const CACHE_TTL_MS = 15_000;

export async function GET() {
  const summary = await fetchRemoteJson<Summary>(SUMMARY_JSON_REL_PATH, CACHE_TTL_MS);
  return Response.json({ summary });
}
