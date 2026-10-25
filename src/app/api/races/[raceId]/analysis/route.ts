import { getAiPrediction } from "@/lib/ai/published-store";
import { privateJson } from "@/lib/security/cache-control";
export const dynamic = "force-dynamic";
export async function GET(_: Request, { params }: { params: Promise<{ raceId: string }> }) {
  const prediction = await getAiPrediction((await params).raceId);
  if (prediction.status !== "READY") return privateJson(prediction);
  return privateJson({ ...prediction, analysis_notice: "reference_win_score は校正状況を明記した参考スコアです。的中・収益を保証するものではありません。" });
}
