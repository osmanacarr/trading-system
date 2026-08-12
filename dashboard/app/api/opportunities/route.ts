import { readJson } from "@/lib/readers";
import { OPPORTUNITIES_JSON_PATH } from "@/lib/paths";
import type { OpportunitiesData } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function GET() {
  const opportunities = readJson<OpportunitiesData>(OPPORTUNITIES_JSON_PATH);
  return Response.json({ opportunities });
}
