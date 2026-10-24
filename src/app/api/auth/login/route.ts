import { NextResponse } from "next/server";
import { passwordIsValid } from "@/lib/auth/password";
import { createSession, SESSION_COOKIE } from "@/lib/auth/session";

export const dynamic = "force-dynamic";
export async function POST(request: Request) {
  const secret = process.env.KEIBA_SESSION_SECRET;
  if (!secret || !process.env.KEIBA_ACCESS_PASSWORD) return NextResponse.json({ error: "AUTH_NOT_CONFIGURED" }, { status: 503, headers: { "Cache-Control": "no-store" } });
  let body: { password?: unknown }; try { body = await request.json(); } catch { return NextResponse.json({ error: "INVALID_REQUEST" }, { status: 400 }); }
  if (!passwordIsValid(body.password)) return NextResponse.json({ error: "INVALID_PASSWORD", message: "パスワードを確認してください。" }, { status: 401, headers: { "Cache-Control": "no-store" } });
  const session = await createSession(secret); const response = NextResponse.json({ ok: true }, { headers: { "Cache-Control": "no-store" } });
  response.cookies.set({ name: SESSION_COOKIE, value: session.value, httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "strict", path: "/", expires: new Date(session.expiresAt * 1000) });
  return response;
}
