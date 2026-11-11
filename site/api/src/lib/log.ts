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
 */

export type LogLevel = 'info' | 'warn' | 'error';
type Fields = Record<string, unknown>;

/** keys whose values are a person's details: dropped wherever they appear */
const PII_KEY =
  /^(e-?mail|phone|tel|mobile|full_?name|first_?name|last_?name|name|customer|customers|address|address_json|ship_?to|city|street|house|apartment|zip|notes?|ip|cf-connecting-ip|marketing_consent)$/i;
const EMAIL_RE = /[^\s@"'<>(),;:]+@[^\s@"'<>(),;:]+\.[a-z]{2,}/gi;
/** Israeli phone numbers as people write them: 05x-xxxxxxx, 0x-xxxxxxx, +972…, with or without dashes and spaces */
const PHONE_RE = /(?:\+972[-\s]?|\b0)(?:[23489]|5\d|7\d)[-\s]?\d{3}[-\s]?\d{4}\b/g;

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

function errorFields(err: unknown): Fields {
  if (err instanceof Error) return { error_name: err.name, error_message: scrub(err.message.slice(0, 300)) };
  return { error_message: scrub(String(err).slice(0, 300)) };
}

/** A short id a person can read out: "E-" and eight characters without look-alikes (no 0/O, 1/I/L). */
export function newErrorId(): string {
  const abc = '23456789ABCDEFGHJKMNPQRSTUVWXYZ';
  const b = crypto.getRandomValues(new Uint8Array(8));
  return `E-${[...b].map((x) => abc[x % abc.length]).join('')}`;
}

/** The row as it is written (exported for the tests: it is what reaches Workers Logs). */
export function logRow(level: LogLevel, event: string, fields: Fields = {}, err?: unknown): Fields {
  return { level, event, at: new Date().toISOString(), ...(redact(fields) as Fields), ...(err === undefined ? {} : errorFields(err)) };
}

export const log = {
  info(event: string, fields?: Fields): void {
    console.log(logRow('info', event, fields));
  },
  warn(event: string, fields?: Fields, err?: unknown): void {
    console.warn(logRow('warn', event, fields, err));
  },
  /** Writes an error row and returns its id (a new one unless `fields.error_id` is given). */
  error(event: string, fields: Fields = {}, err?: unknown): string {
    const error_id = typeof fields.error_id === 'string' ? fields.error_id : newErrorId();
    console.error(logRow('error', event, { ...fields, error_id }, err));
    return error_id;
  },
};

/** The customer's short message for an error they cannot fix, with the id of its log row. */
export const errorMessageHe = (errorId: string): string => `משהו השתבש אצלנו. נסו שוב בעוד רגע. אם זה חוזר, כתבו לנו וציינו את הקוד ${errorId}.`;
