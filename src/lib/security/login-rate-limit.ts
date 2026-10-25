import "server-only";
import { createHmac } from "node:crypto";

const DEFAULT_WINDOW_SECONDS = 15 * 60;
const DEFAULT_MAX_FAILURES = 12;
const UNAVAILABLE_RETRY_SECONDS = 60;

type UpstashResult<T> = { result?: T; error?: string };
type LimitResult =
  | { allowed: true }
  | { allowed: false; retryAfter: number; reason: "LIMITED" | "UNAVAILABLE" };

function developmentNumber(name: string, fallback: number) {
  if (process.env.NODE_ENV === "production") return fallback;
  const value = Number(process.env[name]);
  return Number.isInteger(value) && value > 0 ? value : fallback;
}

function settings() {
  const url = process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN;
  if (!url || !token) return null;
  try {
    const parsed = new URL(url);
    if (process.env.NODE_ENV === "production" && parsed.protocol !== "https:") return null;
    return {
      url: parsed.toString().replace(/\/$/, ""),
      token,
      windowSeconds: developmentNumber("KEIBA_LOGIN_RATE_LIMIT_WINDOW_SECONDS", DEFAULT_WINDOW_SECONDS),
      maxFailures: developmentNumber("KEIBA_LOGIN_RATE_LIMIT_MAX_ATTEMPTS", DEFAULT_MAX_FAILURES),
    };
  } catch {
    return null;
  }
}

function clientKey(ip: string, secret: string) {
  const digest = createHmac("sha256", secret).update(ip).digest("hex").slice(0, 32);
  return `keiba-ai:login-failures:${digest}`;
}

function clientIp(headers: Headers) {
  const value = headers.get("x-vercel-forwarded-for") ?? headers.get("x-forwarded-for") ?? headers.get("x-real-ip") ?? "unknown";
  return value.split(",")[0].trim().slice(0, 128) || "unknown";
}

async function redisEval(url: string, token: string, key: string, windowSeconds: number, maxFailures: number, passwordValid: boolean) {
  // One atomic decision prevents concurrent successes from erasing failures or
  // concurrent failures from passing the limit. Successes do not consume slots.
  const script = "local count=tonumber(redis.call('GET',KEYS[1]) or '0'); if count>=tonumber(ARGV[2]) then return {0,redis.call('TTL',KEYS[1])} end; if ARGV[3]=='0' then count=redis.call('INCR',KEYS[1]); if count==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end end; return {1,0}";
  const response = await fetch(url, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify(["EVAL", script, 1, key, String(windowSeconds), String(maxFailures), passwordValid ? "1" : "0"]),
    cache: "no-store",
    signal: AbortSignal.timeout(5000),
  });
  if (!response.ok) throw new Error("RATE_LIMIT_STORE_ERROR");
  const payload = await response.json() as UpstashResult<[number, number]>;
  if (!Array.isArray(payload.result) || !Number.isInteger(payload.result[0]) || !Number.isInteger(payload.result[1])) throw new Error("RATE_LIMIT_STORE_INVALID");
  const [allowed, ttl] = payload.result;
  if ((allowed !== 0 && allowed !== 1) || (allowed === 0 && ttl < 0)) throw new Error("RATE_LIMIT_STORE_INVALID");
  return { allowed: allowed === 1, ttl };
}

/** Shared external limiter; unavailable storage blocks login instead of falling back to per-instance memory. */
export async function registerLoginAttempt(headers: Headers, secret: string, passwordValid: boolean): Promise<LimitResult> {
  const config = settings();
  if (!config) return { allowed: false, retryAfter: UNAVAILABLE_RETRY_SECONDS, reason: "UNAVAILABLE" };
  try {
    const result = await redisEval(config.url, config.token, clientKey(clientIp(headers), secret), config.windowSeconds, config.maxFailures, passwordValid);
    if (!result.allowed) return { allowed: false, retryAfter: Math.max(1, result.ttl), reason: "LIMITED" };
    return { allowed: true };
  } catch {
    return { allowed: false, retryAfter: UNAVAILABLE_RETRY_SECONDS, reason: "UNAVAILABLE" };
  }
}
