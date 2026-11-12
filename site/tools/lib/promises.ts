/**
 * S18: the site never promises what it does not do. Today the shop sends the customer no email and no SMS
 * (EMAIL_PROVIDER is UNDECIDED, @hd/shared/email), so no public line may say that something will be sent, that we will
 * update or notify, or offer to be updated. The principle is master-designer's (docs/proposals/wm-phase2-r5-eye-2026-11-11.md
 * §7): "לא מבטיחים מה שלא קורה".
 *
 * - **What a promise is** (`promiseFindings`), per sentence of what the customer reads:
 *   - **send:** a verb of sending (נשלח, יישלחו, שלחנו, שולחים…) with what is sent to the customer (an email, an SMS, a
 *     confirmation, an invoice, an update, a message, a link) in the same sentence: "חשבונית מס נשלחת במייל".
 *   - **notify:** we will update or tell (נעדכן, נודיע…), or the customer's ask to be told ("עדכנו אותי"), with no
 *     channel needed: "נעדכן כשההזמנה יוצאת למשלוח" promises contact all the same.
 *   - **receive:** the customer will get an email, an SMS, a message or updates: "תקבלו הודעה", "לקבל עדכונים במייל".
 *   - A negated verb ("האתר לא שולח דיוור") is not a promise. The words alone are not either: a field called "אימייל",
 *     "כתובת האימייל לא תקינה", the customer writing to us ("להודעת ביטול: באימייל"), "ההזמנה נשלחה" (the status).
 * - **The copy** (site/copy/promises.he.json, master-designer's words): `loadCopy` checks it, `selectCopy` picks the
 *   wording for the build. tools/build-copy.ts writes the chosen lines; tools/check-promises.ts scans what ships.
 */
import { readFileSync } from 'node:fs';
import { emailProviderIssue, emailSends } from '@hd/shared/email';
import { sitePath } from './paths';

const HE = '\\u05D0-\\u05EA';
/** a Hebrew word, with the prefixes that attach to it (ו, ש, כ, ל, ב, ה, מ), and nothing Hebrew around it */
const words = (alts: string[]): string => `(?<![${HE}])[ושכלבהמ]{0,3}(?:${alts.join('|')})(?![${HE}])`;

/** the channels: email, SMS, messaging */
const CHANNEL_HE = [
  'מייל(?:ים)?',
  'אי[-־]?מייל(?:ים)?',
  'דוא["״]ל',
  'דואר אלקטרוני',
  'מסרונ(?:ים)?',
  'מסרון',
  'הודעות? טקסט',
  'ו?ואטסאפ',
  'ווטסאפ',
  'ניוזלטר',
  'דיוור',
];
const CHANNEL_LATIN = '\\b(?:e-?mail(?:s|ed)?|SMS|WhatsApp|newsletter)\\b';
/** what is sent to a customer */
const OBJECT_HE = ['אישור(?:ים)?', 'חשבוני(?:ת|ות)', 'עדכונ(?:ים)?', 'עדכון', 'הודע(?:ה|ות|ת)', 'התרא(?:ה|ות)', 'תזכורת', 'קישור', 'קבלה', 'פרטי ההזמנה'];
/** sending, by us or to the customer: past, present, future (not the customer's "תשלחו", which is to us) */
const SEND_HE = ['נשלח(?:ת|ים|ות|ו|ה|נו)?', 'יישלח(?:ו)?', 'ישלח(?:ו)?', 'תישלח', 'שלחנו', 'נשלוח', 'שולח(?:ים|ת)?'];
/** we will tell, or the customer asks to be told */
const NOTIFY_HE = ['נעדכן', 'נעדכנכם', 'נעדכנך', 'נודיע', 'נודיעכם', 'נתריע', 'ניידע', 'עדכנו אותי', 'עדכנו אותנו', 'עדכני אותי', 'עדכן אותי', 'הודיעו לי'];
/** the customer will get */
const RECEIVE_HE = ['תקבל(?:ו|י)?', 'יקבלו', 'לקבל', 'מקבלים'];
const RECEIVED_HE = ['הודע(?:ה|ות)', 'עדכונ(?:ים)?', 'עדכון', 'התרא(?:ה|ות)', 'תזכורת'];
const LATIN_PROMISE =
  "\\b(?:we(?:'ll| will)? (?:send|e-?mail|notify|text)|will be (?:sent|e-?mailed)|you(?:'ll| will) (?:receive|get) (?:an? )?(?:e-?mail|sms|text|confirmation|invoice|update)|notify me|keep me (?:posted|updated))\\b";

const RE = {
  channel: new RegExp(`${words(CHANNEL_HE)}|${CHANNEL_LATIN}`, 'iu'),
  object: new RegExp(words(OBJECT_HE), 'u'),
  send: new RegExp(words(SEND_HE), 'gu'),
  notify: new RegExp(words(NOTIFY_HE), 'gu'),
  receive: new RegExp(words(RECEIVE_HE), 'gu'),
  received: new RegExp(words(RECEIVED_HE), 'u'),
  latin: new RegExp(LATIN_PROMISE, 'giu'),
};
/** "לא", "אין", "בלי" right before the verb: "האתר לא שולח דיוור", "לא נשלח לכם מייל" */
const NEGATED = /(?:^|[\s(])(?:לא|אין|בלי|אינו|איננו)\s+(?:\S+\s+)?$/u;

export type PromiseRule = 'send' | 'notify' | 'receive' | 'latin';
export type PromiseFinding = { rule: PromiseRule; match: string; sentence: string };

/** the sentences of a text: split at . ! ? ; a line break, and the "·" between items */
export function sentences(text: string): string[] {
  return text
    .split(/[.!?;\n]+|\s[·•]\s/u)
    .map((s) => s.replace(/\s+/g, ' ').trim())
    .filter(Boolean);
}

function verbs(re: RegExp, s: string): string[] {
  const out: string[] = [];
  for (const m of s.matchAll(re)) if (!NEGATED.test(s.slice(0, m.index))) out.push(m[0].trim());
  return out;
}

/** Every promise of an email, an SMS, a message or an update in a text the customer reads (see the header). */
export function promiseFindings(text: string): PromiseFinding[] {
  const out: PromiseFinding[] = [];
  for (const s of sentences(text)) {
    const sent = verbs(RE.send, s);
    if (sent.length && (RE.channel.test(s) || RE.object.test(s))) out.push({ rule: 'send', match: sent[0]!, sentence: s });
    for (const m of verbs(RE.notify, s)) out.push({ rule: 'notify', match: m, sentence: s });
    const got = verbs(RE.receive, s);
    if (got.length && (RE.channel.test(s) || RE.received.test(s))) out.push({ rule: 'receive', match: got[0]!, sentence: s });
    for (const m of s.matchAll(RE.latin)) out.push({ rule: 'latin', match: m[0], sentence: s });
  }
  return out;
}

// ---------- the copy (site/copy/promises.he.json) ----------

export const COPY_FILE = sitePath('copy/promises.he.json');
export const COPY_OUT = sitePath('.generated/copy.he.json');
export const WRANGLER_FILE = sitePath('api/wrangler.jsonc');

type Line = string | null;
export type CopyEntry = { where: string; group?: string } & ({ text: string } | { email: Line; no_email: Line });
export type CopySource = { note?: string; strings: Record<string, CopyEntry> };
export type Mode = 'email' | 'no_email';
/** the lines a build shows, by key; null: the line (or its control) is not shown */
export type CopyLines = Record<string, Line>;

const KEY = /^[a-z]+(?:\.[a-z_]+)+$/;
/** the lines a page cannot do without: a line in both wordings (the order page's line and its error, the checkout's
 * total, the privacy policy's items). The others may be null in a wording: their line or control is then not shown. */
export const NEEDED = [
  'checkout.total_note',
  'order.next.received',
  'order.next.shipped',
  'order.next.shipped_no_number',
  'order.next.delivered',
  'order.no_access',
  'privacy.processors',
  'privacy.marketing',
] as const;

/** The line of an entry in a mode. */
export function lineOf(e: CopyEntry, mode: Mode): Line {
  return 'text' in e ? e.text : e[mode];
}

/**
 * What is wrong with the copy, whatever the build: its shape; a `no_email` or `text` line that promises (it is what the
 * customer reads while no provider sends); a line of a group shown without the rest of its group.
 */
export function copyIssues(src: unknown): string[] {
  const out: string[] = [];
  const strings = (src as CopySource | null)?.strings;
  if (!strings || typeof strings !== 'object') return ['the copy has no "strings"'];
  const groups = new Map<string, { email: boolean[]; no_email: boolean[] }>();
  for (const [key, e] of Object.entries(strings)) {
    if (!KEY.test(key)) out.push(`${key}: a key is lowercase words joined by dots (page.line)`);
    if (!e || typeof e !== 'object') {
      out.push(`${key}: not an entry`);
      continue;
    }
    if (typeof e.where !== 'string' || !e.where.trim()) out.push(`${key}: "where" says where the line is shown`);
    const hasText = 'text' in e;
    const hasModes = 'email' in e || 'no_email' in e;
    if (hasText === hasModes) {
      out.push(`${key}: either "text" (the same line either way) or both "email" and "no_email"`);
      continue;
    }
    if (hasText && (typeof e.text !== 'string' || !e.text.trim())) out.push(`${key}: "text" is a line`);
    if (!hasText) {
      const m = e as { email?: unknown; no_email?: unknown };
      for (const mode of ['email', 'no_email'] as const) {
        if (!(mode in m)) out.push(`${key}: "${mode}" is missing (null hides the line)`);
        else if (m[mode] !== null && (typeof m[mode] !== 'string' || !(m[mode] as string).trim())) out.push(`${key}: "${mode}" is a line or null`);
      }
    }
    const shown = lineOf(e, 'no_email');
    if (typeof shown === 'string')
      for (const f of promiseFindings(shown)) out.push(`${key}: the line shown without an email provider promises (${f.rule}: "${f.match}"): "${f.sentence}"`);
    if (e.group !== undefined) {
      if (typeof e.group !== 'string' || !KEY.test(`${e.group}.x`)) out.push(`${key}: "group" is a lowercase word`);
      const g = groups.get(e.group) ?? { email: [], no_email: [] };
      g.email.push(lineOf(e, 'email') !== null);
      g.no_email.push(lineOf(e, 'no_email') !== null);
      groups.set(e.group, g);
    }
  }
  for (const key of NEEDED) {
    const e = strings[key];
    if (!e) out.push(`${key}: missing (a page needs this line)`);
    else
      for (const mode of ['email', 'no_email'] as const)
        if (typeof lineOf(e, mode) !== 'string') out.push(`${key}: a page needs this line in "${mode}" (null is not allowed)`);
  }
  for (const [name, g] of groups)
    for (const mode of ['email', 'no_email'] as const)
      if (new Set(g[mode]).size > 1) out.push(`group ${name}: in "${mode}" its lines are shown or hidden together (some are null, some are not)`);
  return out;
}

export function loadCopy(file = COPY_FILE): CopySource {
  return JSON.parse(readFileSync(file, 'utf8')) as CopySource;
}

/** The lines of a build: `email` only when a provider really sends; `no_email` otherwise. */
export function selectCopy(src: CopySource, sends: boolean): CopyLines {
  const mode: Mode = sends ? 'email' : 'no_email';
  return Object.fromEntries(Object.entries(src.strings).map(([k, e]) => [k, lineOf(e, mode)]));
}

// ---------- which environment the build is for, and its EMAIL_PROVIDER ----------

/** wrangler.jsonc: comments and trailing commas, outside strings (the same reading as api/scripts/jsonc.ts) */
function parseJsonc(text: string): unknown {
  let out = '';
  let inStr = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i]!;
    if (inStr) {
      out += ch;
      if (ch === '\\') out += text[++i] ?? '';
      else if (ch === '"') inStr = false;
    } else if (ch === '"') {
      inStr = true;
      out += ch;
    } else if (ch === '/' && text[i + 1] === '/') {
      while (i < text.length && text[i] !== '\n') i++;
      out += '\n';
    } else if (ch === '/' && text[i + 1] === '*') {
      i = text.indexOf('*/', i + 2) + 1;
    } else out += ch;
  }
  return JSON.parse(out.replace(/,(\s*[}\]])/g, '$1'));
}

export type EmailTarget = { env: string; value: unknown; issue: string | null; sends: boolean };

/**
 * The EMAIL_PROVIDER of the environment the site is built for: `production` for the public build (HD_PUBLIC=1, the
 * deploy), the top level otherwise (development, the local preview, the e2e suite). A value that is not UNDECIDED or a
 * provider from the closed list stops the build (`issue`).
 */
export function emailTarget(opts: { publicBuild: boolean; wrangler?: string }): EmailTarget {
  const cfg = parseJsonc(readFileSync(opts.wrangler ?? WRANGLER_FILE, 'utf8')) as {
    vars?: Record<string, unknown>;
    env?: Record<string, { vars?: Record<string, unknown> }>;
  };
  const env = opts.publicBuild ? 'production' : 'top level';
  const vars = opts.publicBuild ? cfg.env?.production?.vars : cfg.vars;
  if (!vars) return { env, value: undefined, issue: `wrangler.jsonc has no vars for ${env}`, sends: false };
  const value = vars.EMAIL_PROVIDER;
  return { env, value, issue: emailProviderIssue(value), sends: emailSends(value) };
}
