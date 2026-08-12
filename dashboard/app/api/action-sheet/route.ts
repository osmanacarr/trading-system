import { readJson } from "@/lib/readers";
import { ACTION_SHEET_JSON_PATH } from "@/lib/paths";
import type { ActionSheetData } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function GET() {
  const actionSheet = readJson<ActionSheetData>(ACTION_SHEET_JSON_PATH);
  return Response.json({ actionSheet });
}
