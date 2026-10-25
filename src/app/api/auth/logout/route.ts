import { NextRequest, NextResponse } from "next/server";
import { SESSION_COOKIE, verifySession } from "@/lib/auth/session";
import { revokeSession } from "@/lib/auth/session-store";
import { privateJson, privateNoStoreHeaders } from "@/lib/security/cache-control";

export async function POST(request: NextRequest) {
  const value = request.cookies.get(SESSION_COOKIE)?.value;
  const secret = process.env.KEIBA_SESSION_SECRET;
  if (value && !secret) return privateJson({ error: "AUTH_NOT_CONFIGURED" }, { status: 503 });
  const session = await verifySession(value, secret);
  if (session) {
    try { await revokeSession(session.id); }
    catch { return privateJson({ error: "SESSION_STORE_UNAVAILABLE", message: "ログアウトできません。時間を置いて再試行してください。" }, { status: 503, headers: { "Retry-After": "60" } }); }
  }
  const response = NextResponse.json({ ok: true }, { headers: privateNoStoreHeaders() });
  response.cookies.set({ name: SESSION_COOKIE, value: "", httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "strict", path: "/", maxAge: 0 });
  return response;
}
