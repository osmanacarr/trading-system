import { fetchRemoteJson } from "@/lib/remote-readers";
import type { OpportunitiesData } from "@/lib/types";

export const dynamic = "force-dynamic";

const OPPORTUNITIES_JSON_REL_PATH = "paper_trading/logs/opportunities.json";
const CACHE_TTL_MS = 15_000;

export async function GET() {
  const opportunities = await fetchRemoteJson<OpportunitiesData>(OPPORTUNITIES_JSON_REL_PATH, CACHE_TTL_MS);
  return Response.json({ opportunities });
}
