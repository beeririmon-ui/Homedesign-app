/**
 * S20, QA ת61: the shop's contact details, in one place. `CONTACT_EMAIL` and, optionally, `CONTACT_PHONE` are variables
 * of each environment in api/wrangler.jsonc, `UNDECIDED` until the owner decides (CONTACT1).
 *
 * - **The site** shows one contact block (web/src/components/Contact.tsx): in the footer of every page, under "כתבו לנו"
 *   on the order page, in the cancellation and accessibility pages. tools/build-copy.ts reads the variables of the
 *   environment the site is built for and writes them into `.generated/copy.he.json`, with the lines that depend on them
 *   (site/copy/promises.he.json, `contact` / `no_contact`).
 * - **Without contact details** the block is not shown, and no line says "כתבו לנו": the `no_contact` wording offers no
 *   contact it does not have.
 * - **The public build** (`HD_PUBLIC=1`) stops without them: a shop that sells at a distance must give the customer a way
 *   to reach it (docs/ops/deploy-runbook.md, "פרטי הקשר של העסק"). Behind the flag it is a warning.
 * - **The Worker** reads the same variables for its one customer line that asks to write to us (lib/log.ts,
 *   `errorMessageHe`).
 */
export const CONTACT_UNDECIDED = 'UNDECIDED';

export type Contact = {
  email: string;
  /** as written in the config, for the page */
  phone: string | null;
  /** the phone for a tel: link (+972…, 1-800…, *1234) */
  phone_href: string | null;
};

const EMAIL = /^[^\s@<>()[\]",;:\\]+@[^\s@<>()[\]",;:\\]+\.[a-z]{2,}$/i;
/** reserved for examples and tests (RFC 2606, 6761): never a real shop's address */
const RESERVED = /@(?:[^@]*\.)?(?:example\.(?:com|net|org)|example|test|invalid|localhost)$/i;

const unset = (v: unknown): boolean => v === undefined || v === null || v === '' || v === CONTACT_UNDECIDED;

/** an Israeli number: 0X-XXXXXXX, 05X-XXXXXXX, +972…, 1-800/1-700…, or a star number (*1234) */
function phoneHref(raw: string): string | null {
  const s = raw.trim();
  if (/^\*\d{4}$/.test(s)) return s;
  if (!/^\+?[\d\s-]+$/.test(s)) return null;
  let d = s.replace(/[\s-]/g, '');
  if (d.startsWith('+972')) d = `0${d.slice(4)}`;
  if (/^1[5-9]00\d{6}$/.test(d)) return d;
  if (/^0[2-9]\d{7,8}$/.test(d)) return `+972${d.slice(1)}`;
  return null;
}

/** What is wrong with an environment's contact variables (a malformed value; a phone with no email). */
export function contactIssues(vars: Record<string, unknown>): string[] {
  const out: string[] = [];
  const email = vars.CONTACT_EMAIL;
  const phone = vars.CONTACT_PHONE;
  if (email === undefined) out.push(`CONTACT_EMAIL is not set (it is ${CONTACT_UNDECIDED} until the owner decides, CONTACT1)`);
  else if (!unset(email) && (typeof email !== 'string' || email.length > 254 || !EMAIL.test(email.trim())))
    out.push(`CONTACT_EMAIL="${String(email).slice(0, 60)}" is not an email address`);
  if (!unset(phone) && (typeof phone !== 'string' || !phoneHref(phone)))
    out.push(`CONTACT_PHONE="${String(phone).slice(0, 30)}" is not an Israeli phone number (03-1234567, 050-1234567, +972…, 1-800-…, *1234)`);
  if (unset(email) && !unset(phone)) out.push('CONTACT_PHONE without CONTACT_EMAIL: the contact block needs the email');
  return out;
}

/** The contact details an environment's variables give, or null while CONTACT_EMAIL is UNDECIDED (or malformed). */
export function contactOf(vars: Record<string, unknown>): Contact | null {
  if (contactIssues(vars).length || unset(vars.CONTACT_EMAIL)) return null;
  const phone = unset(vars.CONTACT_PHONE) ? null : String(vars.CONTACT_PHONE).trim();
  return { email: String(vars.CONTACT_EMAIL).trim(), phone, phone_href: phone ? phoneHref(phone) : null };
}

/** An address reserved for examples and tests: fine behind the flag, never in the public build. */
export const isPlaceholderEmail = (email: string): boolean => RESERVED.test(email);
