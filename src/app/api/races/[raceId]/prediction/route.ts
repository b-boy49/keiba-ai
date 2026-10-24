import { getAiPrediction } from "@/lib/ai/published-store";
export const dynamic = "force-dynamic";
export async function GET(_: Request, { params }: { params: Promise<{ raceId: string }> }) { return Response.json(await getAiPrediction((await params).raceId)); }
