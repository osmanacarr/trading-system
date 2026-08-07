import { readOpenPositions } from "@/lib/readers";
import { computeCorrelationWarning } from "@/lib/derive";

export const dynamic = "force-dynamic";

export async function GET() {
  const positions = readOpenPositions();
  const warning = computeCorrelationWarning(positions);
  return Response.json({ warning });
}
