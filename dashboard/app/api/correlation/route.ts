import { readOpenPositions } from "@/lib/readers";
import { computeCorrelationWarning } from "@/lib/derive";

export const dynamic = "force-dynamic";

export async function GET() {
  const { positions, error } = readOpenPositions();
  const warning = computeCorrelationWarning(positions);
  return Response.json({ warning, positionsError: error });
}
