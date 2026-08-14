import { fetchRemoteJson } from "@/lib/remote-readers";
import type { ActionSheetData } from "@/lib/types";

export const dynamic = "force-dynamic";

const ACTION_SHEET_JSON_REL_PATH = "paper_trading/logs/action_sheet.json";
const CACHE_TTL_MS = 15_000;

export async function GET() {
  const actionSheet = await fetchRemoteJson<ActionSheetData>(ACTION_SHEET_JSON_REL_PATH, CACHE_TTL_MS);
  return Response.json({ actionSheet });
}
