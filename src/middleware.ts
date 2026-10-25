import { NextRequest, NextResponse } from "next/server";
import { SESSION_COOKIE, verifySession } from "@/lib/auth/session";
import { sessionExists } from "@/lib/auth/session-store";
import { privateNoStoreHeaders } from "@/lib/security/cache-control";

const publicPaths = ["/access", "/api/auth/login", "/api/auth/logout"];
function isPublicPath(pathname: string) { return publicPaths.includes(pathname) || pathname.startsWith("/_next/") || pathname.startsWith("/images/") || pathname === "/favicon.ico"; }
export async function middleware(request: NextRequest) {
  if (isPublicPath(request.nextUrl.pathname)) return NextResponse.next();
  const session = await verifySession(request.cookies.get(SESSION_COOKIE)?.value, process.env.KEIBA_SESSION_SECRET);
  if (session) {
    try { if (await sessionExists(session.id)) return NextResponse.next({ headers: privateNoStoreHeaders() }); }
    catch { return NextResponse.json({ error: "SESSION_STORE_UNAVAILABLE", message: "接続できません。時間を置いて再試行してください。" }, { status: 503, headers: { ...privateNoStoreHeaders(), "Retry-After": "60" } }); }
  }
  if (request.nextUrl.pathname.startsWith("/api/")) return NextResponse.json({ error: "AUTH_REQUIRED", message: "閲覧には共通パスワードが必要です。" }, { status: 401, headers: privateNoStoreHeaders() });
  const login = new URL("/access", request.url); login.searchParams.set("next", request.nextUrl.pathname + request.nextUrl.search);
  return NextResponse.redirect(login, { headers: privateNoStoreHeaders() });
}
export const config = { matcher: ["/:path*"] };
