/**
 * HMAC-SHA256 webhook signatures (Web Crypto: runs in Workers, browsers and Node 22).
 * Header format used by the mock provider: `t=<unix seconds>,v1=<hex hmac of "<t>.<raw body>">`.
 * A real provider adapter maps its own scheme onto `verifyHmacSignature` (see api/src/lib/payments).
 */
const enc = new TextEncoder();

async function hmacKey(secret: string): Promise<CryptoKey> {
  return crypto.subtle.importKey('raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, [
    'sign',
  ]);
}

export function toHex(buf: ArrayBuffer): string {
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

export async function hmacHex(secret: string, message: string): Promise<string> {
  return toHex(await crypto.subtle.sign('HMAC', await hmacKey(secret), enc.encode(message)));
}

export async function sha256Hex(message: string): Promise<string> {
  return toHex(await crypto.subtle.digest('SHA-256', enc.encode(message)));
}

/** Constant-time comparison of two hex strings. */
export function timingSafeEqualHex(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

export async function signWebhook(secret: string, rawBody: string, nowSec: number): Promise<string> {
  return `t=${nowSec},v1=${await hmacHex(secret, `${nowSec}.${rawBody}`)}`;
}

export type VerifyResult = { ok: true; timestamp: number } | { ok: false; reason: 'format' | 'stale' | 'mismatch' };

export async function verifyWebhook(
  secret: string,
  header: string | null | undefined,
  rawBody: string,
  nowSec: number,
  toleranceSec = 300,
): Promise<VerifyResult> {
  if (!header || !secret) return { ok: false, reason: 'format' };
  const parts = Object.fromEntries(
    header.split(',').map((p) => {
      const i = p.indexOf('=');
      return [p.slice(0, i).trim(), p.slice(i + 1).trim()];
    }),
  );
  const t = Number(parts.t);
  const v1 = parts.v1;
  if (!Number.isInteger(t) || !v1 || !/^[0-9a-f]{64}$/.test(v1)) return { ok: false, reason: 'format' };
  if (Math.abs(nowSec - t) > toleranceSec) return { ok: false, reason: 'stale' };
  const expected = await hmacHex(secret, `${t}.${rawBody}`);
  return timingSafeEqualHex(expected, v1) ? { ok: true, timestamp: t } : { ok: false, reason: 'mismatch' };
}

/** Random URL-safe token (order access tokens, session ids). */
export function randomToken(bytes = 24): string {
  const a = crypto.getRandomValues(new Uint8Array(bytes));
  let s = '';
  for (const b of a) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
