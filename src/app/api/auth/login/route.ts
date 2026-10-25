import { NextResponse } from "next/server";
import { passwordIsValid } from "@/lib/auth/password";
import { createSession, SESSION_COOKIE } from "@/lib/auth/session";
import { privateJson, privateNoStoreHeaders } from "@/lib/security/cache-control";
import { registerLoginAttempt } from "@/lib/security/login-rate-limit";

export const dynamic = "force-dynamic";
export async function POST(request: Request) {
  const secret = process.env.KEIBA_SESSION_SECRET;
  if (!secret || !process.env.KEIBA_ACCESS_PASSWORD) return privateJson({ error: "AUTH_NOT_CONFIGURED" }, { status: 503 });
  let body: { password?: unknown }; try { body = await request.json(); } catch { return privateJson({ error: "INVALID_REQUEST" }, { status: 400 }); }
  const passwordValid = passwordIsValid(body.password);
  const limit = await registerLoginAttempt(request.headers, secret, passwordValid);
  if (!limit.allowed) {
    const message = limit.reason === "LIMITED" ? "試行回数が上限に達しました。時間を置いて再試行してください。" : "ログイン保護機構を確認中です。時間を置いて再試行してください。";
    return privateJson({ error: limit.reason === "LIMITED" ? "TOO_MANY_ATTEMPTS" : "RATE_LIMIT_UNAVAILABLE", message }, { status: limit.reason === "LIMITED" ? 429 : 503, headers: { "Retry-After": String(limit.retryAfter) } });
  }
  if (!passwordValid) return privateJson({ error: "INVALID_PASSWORD", message: "パスワードを確認してください。" }, { status: 401 });
  const session = await createSession(secret); const response = NextResponse.json({ ok: true }, { headers: privateNoStoreHeaders() });
  response.cookies.set({ name: SESSION_COOKIE, value: session.value, httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "strict", path: "/", expires: new Date(session.expiresAt * 1000) });
  return response;
}
