import { fetchRemoteJsonl } from "@/lib/remote-readers";
import type { TradeRecord } from "@/lib/types";

export const dynamic = "force-dynamic";

const TRADES_JSONL_REL_PATH = "paper_trading/logs/trades.jsonl";
const CACHE_TTL_MS = 15_000;

export async function GET() {
  const trades = await fetchRemoteJsonl<TradeRecord>(TRADES_JSONL_REL_PATH, CACHE_TTL_MS);
  return Response.json({ trades });
}
