import { readOpenPositions } from "@/lib/readers";

export const dynamic = "force-dynamic";

export async function GET() {
  const positions = readOpenPositions();
  return Response.json({ positions });
}
