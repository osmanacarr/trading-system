import { readJson } from "@/lib/readers";
import { SUMMARY_JSON_PATH } from "@/lib/paths";
import type { Summary } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function GET() {
  const summary = readJson<Summary>(SUMMARY_JSON_PATH);
  return Response.json({ summary });
}
