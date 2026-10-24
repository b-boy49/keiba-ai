import { NextRequest, NextResponse } from "next/server";
import { SESSION_COOKIE, verifySession } from "@/lib/auth/session";

const publicPaths = ["/access", "/api/auth/login", "/api/auth/logout"];
function isPublicPath(pathname: string) { return publicPaths.includes(pathname) || pathname.startsWith("/_next/") || pathname.startsWith("/images/") || pathname === "/favicon.ico"; }
export async function middleware(request: NextRequest) {
  if (isPublicPath(request.nextUrl.pathname)) return NextResponse.next();
  const authenticated = await verifySession(request.cookies.get(SESSION_COOKIE)?.value, process.env.KEIBA_SESSION_SECRET);
  if (authenticated) return NextResponse.next();
  if (request.nextUrl.pathname.startsWith("/api/")) return NextResponse.json({ error: "AUTH_REQUIRED", message: "閲覧には共通パスワードが必要です。" }, { status: 401, headers: { "Cache-Control": "no-store" } });
  const login = new URL("/access", request.url); login.searchParams.set("next", request.nextUrl.pathname + request.nextUrl.search);
  return NextResponse.redirect(login);
}
export const config = { matcher: ["/:path*"] };
