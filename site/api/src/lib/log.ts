/**
 * S13 (launch checklist 6.2): structured logs for Workers Logs, with no personal details.
 *
 * - **One object per row** (`console.log({...})`): Workers Logs indexes the fields of a logged object. Every row has
 *   `level`, `event` and, for an error, an `error_id` the customer is shown ("קוד שגיאה: E-…"), so a message to the shop
 *   finds its row.
 * - **No PII, by construction:** a field whose key names a person's detail (email, phone, name, address and its parts,
 *   notes, the customer, the ship-to block) is dropped whatever it holds, and every string is scrubbed of anything that
 *   looks like an email or an Israeli phone number. An error's message is scrubbed the same way and cut short. A full
 *   name cannot be recognised in free text, so free text from a customer is never logged (the keys above).
 * - **Order numbers stay:** they are random ten-digit numbers (lib/http.ts `orderId`), not a person's detail, and they are
 *   how a row is tied to an order.
 * - **S17, QA ת46:** when the order is known (`orderLog`, `log.forOrder`), its own customer values are stripped from every
 *   row, in whatever script they were typed, case-insensitive, a phone by its digits. When it is not, production logs an
 *   error by its name and code only. Outside production the scrubbed message stays, for the developer.
 */
import { HttpError } from './http';
import { SupplierRefused } from './suppliers/types';

export type LogLevel = 'info' | 'warn' | 'error';
type Fields = Record<string, unknown>;

/**
 * S17, QA ת46: in production an error whose order is not known is logged by its name and code only, never its text.
 * Set once per request and per queue batch from ENVIRONMENT (app.ts, index.ts). Until then the strict rule holds.
 */
let PRODUCTION = true;
export function configureLog(env: { ENVIRONMENT?: string } | null | undefined): void {
  PRODUCTION = !env?.ENVIRONMENT || env.ENVIRONMENT === 'production';
}

/** keys whose values are a person's details: dropped wherever they appear */
const PII_KEY =
  /^(e-?mail|phone|tel|mobile|full_?name|first_?name|last_?name|name|customer|customers|address|address_json|ship_?to|city|street|house|apartment|zip|notes?|ip|cf-connecting-ip|marketing_consent)$/i;
const EMAIL_RE = /[^\s@"'<>(),;:]+@[^\s@"'<>(),;:]+\.[a-z]{2,}/gi;
/**
 * Israeli phone numbers as people write them: 05x-xxxxxxx, 0x-xxxxxxx, +972…, and (S17, QA ת46) 972… and 00972…
 * without the plus, with or without dashes and spaces
 */
const PHONE_RE = /(?:(?:\+|\b00)972[-\s]?|\b972[-\s]?|\b0)(?:[23489]|5\d|7\d)[-\s]?\d{3}[-\s]?\d{4}\b/g;

/** A string with emails and phone numbers masked. */
export function scrub(s: string): string {
  return s.replace(EMAIL_RE, '[email]').replace(PHONE_RE, '[phone]');
}

/** A copy of a value fit for a log row: PII keys dropped, strings scrubbed, depth and size bounded. */
export function redact(value: unknown, depth = 0): unknown {
  if (value === null || value === undefined) return value;
  if (typeof value === 'string') return scrub(value.length > 500 ? `${value.slice(0, 500)}…` : value);
  if (typeof value === 'number' || typeof value === 'boolean') return value;
  if (value instanceof Error) return errorFields(value);
  if (depth > 4) return '[deep]';
  if (Array.isArray(value)) return value.slice(0, 20).map((v) => redact(v, depth + 1));
  if (typeof value === 'object') {
    const out: Fields = {};
    for (const [k, v] of Object.entries(value as Fields)) if (!PII_KEY.test(k)) out[k] = redact(v, depth + 1);
    return out;
  }
  return String(value);
}

/**
 * S16, QA ת38: an exception's text may quote a customer's values (a name or an address inside a library's message, a
 * JSON parse error that shows a piece of its input). Before it is logged, beyond emails and phone numbers: anything in
 * quotes, and every run of Hebrew letters (a name, a street, a city as the customer typed them) are masked. Our own
 * messages and the runtime's are English and keep their meaning. A provider's error is never logged as text at all
 * (`errorCode`): its full text stays in D1, behind Access.
 */
export function scrubMessage(s: string): string {
  return scrub(s)
    .replace(/"[^"\n]{0,400}"|“[^”\n]{0,400}”|'[^'\n]{0,400}'/g, '"[…]"')
    .replace(/[֐-׿יִ-ﭏ]+(?:[\s'"״׳-]+[֐-׿יִ-ﭏ]+)*/g, '[he]');
}

/**
 * S17, QA ת46: the customer's own values of a known order (its name, email, phone, address), to strip from every log
 * message whatever script they were typed in (QA's leak: a name and an address typed in Latin letters inside an
 * exception). Case-insensitive; each value whole and each of its words of three letters or more; a phone by its digits
 * alone, in any of the forms it is written (05…, 5…, 972…, +972…, 00972…, with any separators); a zip code by its digits.
 */
export type KnownValues = { words: RegExp | null; phones: RegExp[] };
const SEP = '[\\s().-]*';
const esc = (x: string) => x.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
export function knownValues(v: {
  full_name?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: Record<string, unknown> | null;
}): KnownValues {
  const texts = [v.full_name, v.email, ...Object.values(v.address ?? {}).map((x) => (typeof x === 'string' ? x : null))]
    .filter((x): x is string => !!x && !!x.trim())
    .map((x) => x.trim());
  const parts = new Set<string>();
  for (const t of texts) {
    // a number alone (a house, a flat) is no one's detail; a zip code is stripped by its digits below
    if (t.length >= 2 && !/^[\d\s-]+$/.test(t)) parts.add(t);
    for (const w of t.split(/[\s,.;:()"'״׳@/\\־-]+/)) if (w.length >= 3 && !/^\d+$/.test(w)) parts.add(w);
  }
  if (v.email?.includes('@')) parts.add(v.email.split('@')[0]!);
  const words = parts.size
    ? new RegExp(
        [...parts]
          .sort((a, b) => b.length - a.length)
          .map(esc)
          .join('|'),
        'giu',
      )
    : null;
  const phones: RegExp[] = [];
  const digitsOf = (x: string) => x.replace(/\D/g, '');
  if (v.phone) {
    // the number without its prefix (0, 972, 00972), matched with any prefix in front of it
    const nsn = digitsOf(v.phone).replace(/^(?:00972|972|0)/, '');
    if (nsn.length >= 7) phones.push(new RegExp(`(?<!\\d)(?:(?:\\+|00)?972${SEP}|0${SEP})?${nsn.split('').join(SEP)}(?!\\d)`, 'g'));
  }
  for (const t of texts) if (/^[\d\s-]{5,10}$/.test(t)) phones.push(new RegExp(`(?<!\\d)${digitsOf(t).split('').join(SEP)}(?!\\d)`, 'g'));
  return { words, phones };
}
/** A string without the known order's customer values. */
export function stripKnown(s: string, k: KnownValues | undefined): string {
  if (!k) return s;
  let out = s;
  for (const re of k.phones) out = out.replace(re, '[phone]');
  if (k.words) out = out.replace(k.words, '[customer]');
  return out;
}

const NAME_RE = /^[A-Za-z]{1,40}$/;
function errorFields(err: unknown, known?: KnownValues): Fields {
  const name = err instanceof Error && NAME_RE.test(err.name) ? err.name : 'Error';
  const code = errorCode(err);
  // S17 (ת46): an order not known, in production: the name and the code, never the text
  if (!known && PRODUCTION) return { error_name: name, error_code: code };
  const raw = err instanceof Error ? err.message : String(err);
  return { error_name: name, error_code: code, error_message: stripKnown(scrubMessage(raw.slice(0, 300)), known) };
}

/**
 * S16, QA ת38/ת39: a provider's error (the supplier, the invoice or payment provider) as a code, never its text. The
 * text stays in D1 (`last_error`), behind Access.
 * S17, QA ת46: the error's own `code` only from our own classes (SupplierRefused, HttpError) or a system code (ECONNRESET,
 * ERR_…): a provider's `code` is its own free text and may carry the buyer ('invalid_consignee:Orna'). Then a timeout,
 * an HTTP status, the code our own messages start with (a snake_case word: "cj_order_api_docs_needed",
 * "set_composition_missing: …"), else the error's class name.
 */
export function errorCode(err: unknown): string {
  if (!err || typeof err !== 'object') return 'unknown';
  const e = err as { code?: unknown; status?: unknown; name?: unknown; message?: unknown };
  const own = err instanceof SupplierRefused || err instanceof HttpError;
  if (typeof e.code === 'string' && ((own && /^[a-z][a-z0-9_.-]{1,60}$/i.test(e.code)) || /^E[A-Z0-9_]{2,40}$/.test(e.code))) return e.code;
  if (e.name === 'CallTimedOut') return 'timeout';
  if (e.name === 'AbortError' || e.name === 'TimeoutError') return 'aborted';
  if (typeof e.status === 'number' && e.status >= 100 && e.status < 600) return `http_${e.status}`;
  const prefix = typeof e.message === 'string' ? /^([a-z][a-z0-9]*(?:_[a-z0-9]+)+)(?::|$)/.exec(e.message) : null;
  if (prefix) return prefix[1]!;
  return typeof e.name === 'string' && NAME_RE.test(e.name) ? e.name : 'Error';
}

/** A short id a person can read out: "E-" and eight characters without look-alikes (no 0/O, 1/I/L). */
export function newErrorId(): string {
  const abc = '23456789ABCDEFGHJKMNPQRSTUVWXYZ';
  const b = crypto.getRandomValues(new Uint8Array(8));
  return `E-${[...b].map((x) => abc[x % abc.length]).join('')}`;
}

/** The row as it is written (exported for the tests: it is what reaches Workers Logs). */
export function logRow(level: LogLevel, event: string, fields: Fields = {}, err?: unknown, known?: KnownValues): Fields {
  const f = redact(fields) as Fields;
  // S17 (ת46): a known order's customer values leave every string of the row too
  if (known) for (const [k, v] of Object.entries(f)) if (typeof v === 'string') f[k] = stripKnown(v, known);
  return { level, event, at: new Date().toISOString(), ...f, ...(err === undefined ? {} : errorFields(err, known)) };
}

function logger(known?: KnownValues) {
  return {
    info(event: string, fields?: Fields): void {
      console.log(logRow('info', event, fields, undefined, known));
    },
    warn(event: string, fields?: Fields, err?: unknown): void {
      console.warn(logRow('warn', event, fields, err, known));
    },
    /** Writes an error row and returns its id (a new one unless `fields.error_id` is given). */
    error(event: string, fields: Fields = {}, err?: unknown): string {
      const error_id = typeof fields.error_id === 'string' ? fields.error_id : newErrorId();
      console.error(logRow('error', event, { ...fields, error_id }, err, known));
      return error_id;
    },
  };
}
export type Logger = ReturnType<typeof logger>;

export const log = {
  ...logger(),
  /** S17 (ת46): a logger that strips this order's customer values from every row */
  forOrder: (known: KnownValues | undefined): Logger => logger(known),
};

/**
 * S17 (ת46): the logger of an order: its customer's values loaded from D1 (the customer and the ship-to address), to
 * strip from every row. Without the order (or if D1 fails), the plain logger: in production, name and code only.
 */
export async function orderLog(db: D1Database | undefined, orderId: unknown): Promise<Logger> {
  if (!db || typeof orderId !== 'string' || !/^\d{6,20}$/.test(orderId)) return log;
  try {
    const r = await db
      .prepare('SELECT c.full_name, c.email, c.phone, o.address_json FROM orders o LEFT JOIN customers c ON c.id = o.customer_id WHERE o.id = ?')
      .bind(orderId)
      .first<{ full_name: string | null; email: string | null; phone: string | null; address_json: string | null }>();
    if (!r) return log;
    let address: Record<string, unknown> | null = null;
    try {
      address = r.address_json ? (JSON.parse(r.address_json) as Record<string, unknown>) : null;
    } catch {
      address = null;
    }
    return log.forOrder(knownValues({ full_name: r.full_name, email: r.email, phone: r.phone, address }));
  } catch {
    return log;
  }
}

/** an order number in a request's path (/api/orders/<id>, /admin/orders/<id>…) */
export const orderIdInPath = (path: string): string | null => /\/orders\/(\d{6,20})(?:\/|$)/.exec(path)?.[1] ?? null;

/** The customer's short message for an error they cannot fix, with the id of its log row. */
export const errorMessageHe = (errorId: string): string => `משהו השתבש אצלנו. נסו שוב בעוד רגע. אם זה חוזר, כתבו לנו וציינו את הקוד ${errorId}.`;
