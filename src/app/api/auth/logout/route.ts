import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/auth/session";
import { privateNoStoreHeaders } from "@/lib/security/cache-control";
export async function POST() { const response = NextResponse.json({ ok: true }, { headers: privateNoStoreHeaders() }); response.cookies.set({ name: SESSION_COOKIE, value: "", httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "strict", path: "/", maxAge: 0 }); return response; }
