import type { Context, MiddlewareHandler } from 'hono';
import type { z } from 'zod';
import type { AppEnv, RateLimiter } from '../env';

export class HttpError extends Error {
  constructor(
    public status: 400 | 401 | 403 | 404 | 409 | 413 | 422 | 429 | 500 | 502 | 503,
    public code: string,
    public messageHe?: string,
  ) {
    super(code);
  }
}

/** The page CSP (same as web/public/_headers) for HTML the Worker serves itself. */
export const SITE_CSP =
  "default-src 'self'; script-src 'self'; style-src-elem 'self'; style-src-attr 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; worker-src 'self' blob:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'";

export const nowIso = (): string => new Date().toISOString();

/** Security headers for every API/Worker response (static assets get theirs from web/public/_headers). */
export const securityHeaders: MiddlewareHandler<AppEnv> = async (c, next) => {
  await next();
  const h = c.res.headers;
  h.set('X-Content-Type-Options', 'nosniff');
  h.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  h.set('Cross-Origin-Opener-Policy', 'same-origin');
  h.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');
  if (!h.has('Content-Security-Policy')) h.set('Content-Security-Policy', "default-src 'none'; frame-ancestors 'none'");
  if (!h.has('Cache-Control')) h.set('Cache-Control', 'no-store');
  if (c.env.ENVIRONMENT === 'production' || c.env.ENVIRONMENT === 'preview') h.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
};

export async function readJson<T extends z.ZodType>(c: Context<AppEnv>, schema: T, maxBytes = 16_384): Promise<z.output<T>> {
  const len = Number(c.req.header('content-length') ?? '0');
  if (len > maxBytes) throw new HttpError(413, 'payload_too_large');
  const ct = c.req.header('content-type') ?? '';
  if (!ct.includes('application/json')) throw new HttpError(400, 'expected_json');
  const text = await c.req.text();
  if (text.length > maxBytes) throw new HttpError(413, 'payload_too_large');
  let raw: unknown;
  try {
    raw = JSON.parse(text);
  } catch {
    throw new HttpError(400, 'invalid_json');
  }
  const parsed = schema.safeParse(raw);
  if (!parsed.success) throw new HttpError(422, 'invalid_body', 'חלק מהפרטים חסרים או לא תקינים.');
  return parsed.data;
}

export function clientKey(c: Context<AppEnv>): string {
  return c.req.header('cf-connecting-ip') ?? 'local';
}

/** Workers Rate Limiting binding when present; no binding (unit tests) means no limit. */
export async function rateLimit(limiter: RateLimiter | undefined, key: string): Promise<void> {
  if (!limiter) return;
  const { success } = await limiter.limit({ key });
  if (!success) throw new HttpError(429, 'rate_limited', 'יותר מדי בקשות. נסו שוב בעוד דקה.');
}

const ALPHABET = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ';
/** Human-friendly order id, e.g. HD-7KQ2M9XA (no 0/O/1/I). */
export function orderId(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(8));
  return 'HD-' + [...bytes].map((b) => ALPHABET[b % ALPHABET.length]).join('');
}
