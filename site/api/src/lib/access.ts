/**
 * Cloudflare Access for /api/admin/*. Access sits in front of the route (policy: allowed emails only) and
 * adds a signed JWT in `Cf-Access-Jwt-Assertion`; the Worker verifies it again (defence in depth):
 * RS256 signature against the team's JWKS, `aud` = the Access application AUD, `iss` = the team domain, `exp`.
 */
import type { Env } from '../env';

type Jwk = JsonWebKey & { kid?: string };
type JwtHeader = { alg: string; kid?: string };
type JwtPayload = { aud?: string | string[]; iss?: string; exp?: number; nbf?: number; email?: string; sub?: string };

let jwksCache: { domain: string; keys: Jwk[]; at: number } | null = null;

function b64urlDecode(s: string): Uint8Array<ArrayBuffer> {
  const pad = s.length % 4 === 0 ? '' : '='.repeat(4 - (s.length % 4));
  const bin = atob(s.replace(/-/g, '+').replace(/_/g, '/') + pad);
  const out = new Uint8Array(new ArrayBuffer(bin.length));
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

async function teamKeys(domain: string, fetcher: typeof fetch): Promise<Jwk[]> {
  if (jwksCache && jwksCache.domain === domain && Date.now() - jwksCache.at < 10 * 60_000) return jwksCache.keys;
  const res = await fetcher(`https://${domain}/cdn-cgi/access/certs`);
  if (!res.ok) throw new Error(`access certs ${res.status}`);
  const body = (await res.json()) as { keys: Jwk[] };
  jwksCache = { domain, keys: body.keys, at: Date.now() };
  return body.keys;
}

export function resetAccessCache(): void {
  jwksCache = null;
}

export async function verifyAccessJwt(
  token: string,
  opts: { domain: string; aud: string; nowSec: number; fetcher?: typeof fetch },
): Promise<{ ok: true; email: string } | { ok: false; reason: string }> {
  const parts = token.split('.');
  if (parts.length !== 3) return { ok: false, reason: 'format' };
  const [h, p, s] = parts as [string, string, string];
  let header: JwtHeader;
  let payload: JwtPayload;
  try {
    header = JSON.parse(new TextDecoder().decode(b64urlDecode(h))) as JwtHeader;
    payload = JSON.parse(new TextDecoder().decode(b64urlDecode(p))) as JwtPayload;
  } catch {
    return { ok: false, reason: 'format' };
  }
  if (header.alg !== 'RS256') return { ok: false, reason: 'alg' };
  const keys = await teamKeys(opts.domain, opts.fetcher ?? fetch);
  const jwk = keys.find((k) => k.kid === header.kid) ?? (keys.length === 1 ? keys[0] : undefined);
  if (!jwk) return { ok: false, reason: 'kid' };
  const key = await crypto.subtle.importKey('jwk', jwk, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['verify']);
  const valid = await crypto.subtle.verify('RSASSA-PKCS1-v1_5', key, b64urlDecode(s), new TextEncoder().encode(`${h}.${p}`));
  if (!valid) return { ok: false, reason: 'signature' };
  const auds = Array.isArray(payload.aud) ? payload.aud : payload.aud ? [payload.aud] : [];
  if (!auds.includes(opts.aud)) return { ok: false, reason: 'aud' };
  if (payload.iss !== `https://${opts.domain}`) return { ok: false, reason: 'iss' };
  if (typeof payload.exp !== 'number' || payload.exp < opts.nowSec) return { ok: false, reason: 'expired' };
  if (typeof payload.nbf === 'number' && payload.nbf > opts.nowSec + 60) return { ok: false, reason: 'nbf' };
  return { ok: true, email: payload.email ?? payload.sub ?? 'unknown' };
}

/** Local development only: `ADMIN_DEV_BYPASS=1` in .dev.vars, never honoured in preview or production. */
export function devBypassAllowed(env: Env): boolean {
  return (env.ENVIRONMENT === 'development' || env.ENVIRONMENT === 'test') && env.ADMIN_DEV_BYPASS === '1';
}
