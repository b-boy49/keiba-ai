const encoder = new TextEncoder();
export const SESSION_TTL_SECONDS = 60 * 60 * 12;
export const SESSION_COOKIE = "keiba_ai_session";

function encode(value: Uint8Array) { let text = ""; for (const byte of value) text += String.fromCharCode(byte); return btoa(text).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/g, ""); }
async function sign(value: string, secret: string) { const key = await crypto.subtle.importKey("raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]); return encode(new Uint8Array(await crypto.subtle.sign("HMAC", key, encoder.encode(value)))); }
function equal(left: string, right: string) { const a = encoder.encode(left), b = encoder.encode(right); if (a.length !== b.length) return false; let different = 0; for (let index = 0; index < a.length; index += 1) different |= a[index] ^ b[index]; return different === 0; }

export async function createSession(secret: string) {
  const expiresAt = Math.floor(Date.now() / 1000) + SESSION_TTL_SECONDS;
  const id = encode(crypto.getRandomValues(new Uint8Array(32)));
  const payload = `v2.${expiresAt}.${id}`;
  return { id, value: `${payload}.${await sign(payload, secret)}`, expiresAt };
}

// Versioning intentionally rejects every cookie issued before server-side sessions.
export async function verifySession(value: string | undefined, secret: string | undefined): Promise<{ id: string; expiresAt: number } | null> {
  if (!value || !secret || value.length > 256) return null;
  const [version, expiry, id, signature, ...extra] = value.split(".");
  if (version !== "v2" || !expiry || !id || !signature || extra.length || !/^\d{10}$/.test(expiry) || !/^[A-Za-z0-9_-]{43}$/.test(id) || !/^[A-Za-z0-9_-]{43}$/.test(signature)) return null;
  const expiresAt = Number(expiry), now = Math.floor(Date.now() / 1000);
  if (expiresAt <= now || expiresAt > now + SESSION_TTL_SECONDS) return null;
  if (!equal(signature, await sign(`${version}.${expiry}.${id}`, secret))) return null;
  return { id, expiresAt };
}
