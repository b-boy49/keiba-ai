const encoder = new TextEncoder();
const SESSION_TTL_SECONDS = 60 * 60 * 12;
export const SESSION_COOKIE = "keiba_ai_session";

function encode(value: Uint8Array) { let text = ""; for (const byte of value) text += String.fromCharCode(byte); return btoa(text).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/g, ""); }
function decode(value: string) { const normalized = value.replaceAll("-", "+").replaceAll("_", "/") + "=".repeat((4 - value.length % 4) % 4); const raw = atob(normalized); return Uint8Array.from(raw, (character) => character.charCodeAt(0)); }
async function sign(value: string, secret: string) { const key = await crypto.subtle.importKey("raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]); return encode(new Uint8Array(await crypto.subtle.sign("HMAC", key, encoder.encode(value)))); }
function equal(left: string, right: string) { const a = encoder.encode(left), b = encoder.encode(right); let different = a.length ^ b.length; for (let index = 0; index < Math.max(a.length, b.length); index += 1) different |= (a[index % a.length] ?? 0) ^ (b[index % b.length] ?? 0); return different === 0; }

export async function createSession(secret: string) {
  const expiresAt = Math.floor(Date.now() / 1000) + SESSION_TTL_SECONDS;
  const payload = `${expiresAt}.${crypto.randomUUID()}`;
  return { value: `${payload}.${await sign(payload, secret)}`, expiresAt };
}

export async function verifySession(value: string | undefined, secret: string | undefined) {
  if (!value || !secret) return false;
  const [expiresAt, nonce, signature, ...extra] = value.split(".");
  if (!expiresAt || !nonce || !signature || extra.length || !/^\d+$/.test(expiresAt) || Number(expiresAt) <= Math.floor(Date.now() / 1000)) return false;
  return equal(signature, await sign(`${expiresAt}.${nonce}`, secret));
}
