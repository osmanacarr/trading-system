import { readJsonl } from "@/lib/readers";
import { EQUITY_JSONL_PATH } from "@/lib/paths";
import type { EquitySnapshot } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function GET() {
  const equity = readJsonl<EquitySnapshot>(EQUITY_JSONL_PATH);
  return Response.json({ equity });
}
