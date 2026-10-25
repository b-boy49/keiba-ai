import { getAiPrediction } from "@/lib/ai/published-store";
import { privateJson } from "@/lib/security/cache-control";
export const dynamic = "force-dynamic";
export async function GET(_: Request, { params }: { params: Promise<{ raceId: string }> }) { return privateJson(await getAiPrediction((await params).raceId)); }
