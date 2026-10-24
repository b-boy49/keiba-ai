import { getAiStatus } from "@/lib/ai/published-store";
export const dynamic = "force-dynamic";
export async function GET() { return Response.json(await getAiStatus()); }
