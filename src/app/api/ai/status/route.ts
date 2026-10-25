import { getAiStatus } from "@/lib/ai/published-store";
import { privateJson } from "@/lib/security/cache-control";
export const dynamic = "force-dynamic";
export async function GET() { return privateJson(await getAiStatus()); }
