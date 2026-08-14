import { fetchRemoteJsonl } from "@/lib/remote-readers";
import type { EquitySnapshot } from "@/lib/types";

export const dynamic = "force-dynamic";

const EQUITY_JSONL_REL_PATH = "paper_trading/logs/equity.jsonl";
const CACHE_TTL_MS = 15_000;

export async function GET() {
  const equity = await fetchRemoteJsonl<EquitySnapshot>(EQUITY_JSONL_REL_PATH, CACHE_TTL_MS);
  return Response.json({ equity });
}
