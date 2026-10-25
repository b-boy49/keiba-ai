// Web Crypto and fetch work both in Next middleware (Edge) and Node routes.
const encoder = new TextEncoder();

async function keyFor(id: string) {
  const hash = new Uint8Array(await crypto.subtle.digest("SHA-256", encoder.encode(id)));
  return `keiba-ai:session:v2:${Array.from(hash, byte => byte.toString(16).padStart(2, "0")).join("")}`;
}

async function command(args: (string | number)[]): Promise<unknown> {
  const url = process.env.UPSTASH_REDIS_REST_URL, token = process.env.UPSTASH_REDIS_REST_TOKEN;
  if (!url || !token) throw new Error("SESSION_STORE_UNAVAILABLE");
  let parsed: URL;
  try { parsed = new URL(url); } catch { throw new Error("SESSION_STORE_UNAVAILABLE"); }
  if (process.env.NODE_ENV === "production" && parsed.protocol !== "https:") throw new Error("SESSION_STORE_UNAVAILABLE");
  const response = await fetch(parsed.toString(), {
    method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify(args), cache: "no-store", signal: AbortSignal.timeout(5000),
  });
  if (!response.ok) throw new Error("SESSION_STORE_UNAVAILABLE");
  const payload = await response.json() as { result?: unknown; error?: unknown };
  if (!payload || payload.error || !("result" in payload)) throw new Error("SESSION_STORE_UNAVAILABLE");
  return payload.result;
}

export async function saveSession(id: string, expiresAt: number) {
  const ttl = expiresAt - Math.floor(Date.now() / 1000);
  if (ttl <= 0 || ttl > 43200 || await command(["SET", await keyFor(id), "1", "EX", ttl]) !== "OK") throw new Error("SESSION_STORE_UNAVAILABLE");
}

export async function sessionExists(id: string) {
  const result = await command(["GET", await keyFor(id)]);
  if (result !== null && result !== "1") throw new Error("SESSION_STORE_UNAVAILABLE");
  return result === "1";
}

export async function revokeSession(id: string) {
  const result = await command(["DEL", await keyFor(id)]);
  if (result !== 0 && result !== 1) throw new Error("SESSION_STORE_UNAVAILABLE");
}
