import { DATA_INTEGRITY_STATUS } from "@/lib/integrity";

export const dynamic = "force-dynamic";

export async function GET() {
  return Response.json(DATA_INTEGRITY_STATUS);
}
