import { NextResponse } from "next/server";

export const PRIVATE_NO_STORE = "private, no-store";

export function privateNoStoreHeaders() {
  return {
    "Cache-Control": PRIVATE_NO_STORE,
    "CDN-Cache-Control": "no-store",
    "Vercel-CDN-Cache-Control": "no-store",
  };
}

export function privateJson(body: unknown, init?: ResponseInit) {
  const headers = new Headers(init?.headers);
  for (const [name, value] of Object.entries(privateNoStoreHeaders())) headers.set(name, value);
  return NextResponse.json(body, { ...init, headers });
}
