import { readJsonl } from "@/lib/readers";
import { TRADES_JSONL_PATH } from "@/lib/paths";
import type { TradeRecord } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function GET() {
  const trades = readJsonl<TradeRecord>(TRADES_JSONL_PATH);
  return Response.json({ trades });
}
