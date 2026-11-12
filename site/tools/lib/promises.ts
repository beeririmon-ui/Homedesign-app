/**
 * S18: the site never promises what it does not do. Today the shop sends the customer no email and no SMS
 * (EMAIL_PROVIDER is UNDECIDED, @hd/shared/email), so no public line may say that something will be sent, that we will
 * update or notify, or offer to be updated. The principle is master-designer's (docs/proposals/wm-phase2-r5-eye-2026-11-11.md
 * §7): "לא מבטיחים מה שלא קורה".
 *
 * **What a promise is** (`promiseFindings`), per sentence of what the customer reads, after `normalize` (typographic
 * apostrophes and quotes, niqqud, maqaf, invisible characters). S20 widened it to QA S18's 48 lines (ת58) and made it
 * pass the honest ones (ת59):
 * - **send:** a verb of sending by us or the system (נשלח, יישלח, נשלחת, שולחים, לשלוח, שלחנו…) with what is sent (an
 *   email, an SMS, a confirmation, an invoice, an update, a message, a link, the details) in the sentence. "נשלח אליכם"
 *   alone is one too (what is sent is implied). A past passive ("נשלחה") is a status, unless a channel is named.
 *   Not a promise: a negated verb right before it ("האתר לא שולח"), the customer writing to us or the supplier after
 *   the verb ("שנשלחת אלינו", "נשלחת לספק"), a parcel as its object ("כשהספק ישלח את החבילה").
 * - **notify:** we will update, tell, remind, contact or get back ("נעדכן", "נודיע", "נזכיר לכם", "ניצור קשר",
 *   "נחזור אליכם", "תעודכנו", "לעדכן אתכם"), or the customer asks to be told ("עדכנו אותי", "שלחו לי", "לבקש עדכון",
 *   "היו הראשונים לדעת"). "נעדכן" only with a person or no object: "נעדכן את המדיניות" is not one. "עדכנו אותנו" is the
 *   customer updating us.
 * - **receive:** the customer will get, or is invited to get, a message, an update, a confirmation, an invoice or a link
 *   ("תקבלו חשבונית מס", "קבלו התראה", "לקבלת עדכון"). "מקבלים" (we) is not one, nor "תקבלו את ההזמנה".
 * - **arrive:** a message on its way to the customer ("ההודעה תגיע", "בדרך אליכם" with an email or a confirmation).
 * - **signup:** joining a list of updates ("הירשמו לעדכונים", "הצטרפו לרשימת התפוצה").
 * - **channel:** a sentence that names a channel (email, SMS, WhatsApp, Telegram, a newsletter, a mailing list, a
 *   mailbox) is a promise ("עדכוני משלוח ב-SMS", "המייל עם האישור כבר בדרך"), unless it negates, it is the way to reach
 *   us ("כתבו לנו", "שירות הלקוחות", "הודעת ביטול"), or the channel is a field ("כתובת האימייל", "שם, אימייל, טלפון").
 * - **latin:** the same in English ("We'll email you", "Get notified", "Check your inbox", "Sign up for our newsletter").
 *
 * **The copy** (site/copy/promises.he.json, master-designer's words): `loadCopy` reads it, `copyIssues` checks it,
 * `selectCopy` picks the wording for the build: by what the provider really sends (`needs`, S20 ת62) and by whether the
 * shop has contact details (`contact` / `no_contact`, S20 ת61). tools/build-copy.ts writes the chosen lines;
 * tools/check-promises.ts scans what ships.
 */
import { readFileSync } from 'node:fs';
import { EMAIL_CAPABILITIES, emailCapabilities, emailProviderIssue, type EmailCapability } from '@hd/shared/email';
import { sitePath } from './paths';

// ---------- what a promise is ----------

const HE = '\\u05D0-\\u05EA';
/** a Hebrew word (or phrase), with the prefixes that attach to it (ו, ש, כ, ל, ב, ה, מ) when asked, and nothing Hebrew around it */
const words = (alts: string[], prefix = true): string => `(?<![${HE}])${prefix ? '[ושכלבהמ]{0,3}' : ''}(?:${alts.join('|')})(?![${HE}])`;
const re = (src: string, flags = 'u') => new RegExp(src, flags);

/** The text as a person reads it: typographic apostrophes and quotes, niqqud, maqaf, spaces and invisible characters. */
export function normalize(text: string): string {
  return text
    .normalize('NFC')
    .replace(/\u05BE/g, '-')
    .replace(/[\u0591-\u05C7]/g, '')
    .replace(/[\u2018\u2019\u201A\u201B\u02BC\u2032\u00B4`\u05F3]/g, "'")
    .replace(/[\u201C\u201D\u201E\u201F\u2033\u05F4]/g, '"')
    .replace(/[\u00AD\u200B-\u200F\u202A-\u202E\u2060-\u2064\uFEFF]/g, '')
    .replace(/[\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000]/g, ' ');
}

/** the channels: email, SMS, messaging, a newsletter or a mailing list, a mailbox */
const CHANNEL_HE = [
  'מייל(?:ים)?',
  'אי-?מייל(?:ים)?',
  'דוא"ל',
  'דואר אלקטרוני',
  'מסרונ(?:ים)?',
  'מסרון',
  'הודע(?:ות|ת) טקסט',
  'ו?ואטסאפ',
  'ווטסאפ',
  'ו?ואצאפ',
  'ווצאפ',
  'טלגרם',
  'ניוזלטר',
  'דיוור',
  'רשימת (?:ה)?(?:תפוצה|דיוור)',
  'תיבת (?:ה)?(?:דואר|מייל|אימייל)(?: (?:ה)?נכנס)?',
  // S22 (QA ת67, B): the spam folder (an email is on its way), a push notification
  'ספאם',
  'דואר (?:ה)?זבל',
  'פוש',
];
const CHANNEL = re(`${words(CHANNEL_HE)}|\\b(?:e-?mail|sms|whats ?app|telegram|newsletter|push notifications?)\\b`, 'giu');
/** S22 (QA ת67): a tracking number, code or link is sent as a message too ("יישלח מספר מעקב", "תקבלו את מספר המעקב") */
const TRACKING = ['(?:מספר|קוד|קישור)(?:י)? (?:ה)?מעקב', 'קוד(?:י)? (?:ה)?(?:הנחה|קופון|אימות)'];
/** what is sent to a customer */
const OBJECT = re(
  words([
    'אישור(?:ים)?',
    'חשבוני(?:ת|ות)',
    'עדכונ(?:ים|י)?',
    'עדכון',
    'הודע(?:ה|ות|ת)',
    'התרא(?:ה|ות|ת)',
    'תזכור(?:ת|ות)',
    'קישור(?:ים)?',
    'קבלה',
    'פרטי(?:ם)?',
    'מסרונ(?:ים)?',
    'מסרון',
    // S22 (QA ת67): a tracking number, a code; a message ("מסר"), a coupon, a catalogue (B)
    ...TRACKING,
    'מסר(?:ים)?',
    'קופו(?:ן|נים)',
    'קטלוג(?:ים)?',
  ]),
);
/** what the customer gets (receive, arrive) */
const RECEIVED = re(
  words([
    'הודע(?:ה|ות|ת)',
    'עדכונ(?:ים|י)?',
    'עדכון',
    'התרא(?:ה|ות|ת)',
    'תזכור(?:ת|ות)',
    'אישור(?:ים)?',
    'חשבוני(?:ת|ות)',
    'קישור(?:ים)?',
    'מסרונ(?:ים)?',
    'מסרון',
    'קבלה',
    ...TRACKING,
    'מסר(?:ים)?',
  ]),
);
/** sending by us: first person (with "אליכם" alone it is a promise) */
const SEND_FIRST = re(words(['נשלח', 'נשלוח', 'שלחנו']), 'gu');
/** sending, present, future, infinitive (not the customer's "תשלחו", which is to us) */
const SEND_OTHER = re(words(['נשלחת', 'נשלחים', 'נשלחות', 'יישלח(?:ו)?', 'ישלח(?:ו)?', 'תישלח(?:נה)?', 'שולח(?:ים|ת|ות)?', 'לשלוח']), 'gu');
/** sent, past passive: a status, unless a channel is named */
const SEND_PAST = re(words(['נשלחה', 'נשלחו']), 'gu');
/**
 * S22 (QA ת67, N24): "תשלח" is the customer's "you will send" ("תשלח לנו"), or the defective spelling of "תישלח". It is
 * a promise only when what is sent is its subject: a message, a reminder, a confirmation before it in the clause
 * ("תזכורת תשלח יום לפני", "ההודעה תשלח אליכם").
 */
const SEND_DEFECTIVE = re(words(['תשלח', 'תשלחנה']), 'gu');
const TO_CUSTOMER = re(words(['לכם', 'אליכם', 'לכן', 'אליכן', 'לך', 'אליך', 'אלייך'], false));
const TO_US = re(`${words(['לנו', 'אלינו', 'אצלנו', 'איתנו', 'עמנו'])}|(?<![${HE}])ו?(?:ל|אל ה)ספק(?:ים)?(?![${HE}])`);
const SHIP_NOUNS = ['חבילה', 'חבילות', 'הזמנה', 'הזמנות', 'מוצר', 'מוצרים', 'פריט', 'פריטים', 'משלוח', 'משלוחים', 'מארז'];
const SHIP = re(words(SHIP_NOUNS));
const SHIP_OBJECT = re(`^\\s+(?:${'לכם|אליכם|לך|אליך'}\\s+)?את\\s+(?:כל\\s+)?ה(?:${SHIP_NOUNS.join('|')})(?![${HE}])`);

const WE_NOTIFY = re(words(['נעדכן', 'נעדכנכם', 'נעדכנך', 'נודיע', 'נודיעכם', 'נודיעך', 'נתריע', 'ניידע', 'נבשר']), 'gu');
const REMIND = re(words(['נזכיר']), 'gu');
const NOTIFY_PHRASE = re(
  [
    words(['תעודכנו', 'תעודכני', 'תיודעו']),
    `${words(['לעדכן', 'ליידע', 'להודיע', 'להתריע', 'להזכיר', 'לבשר'], false)}\\s+(?:אתכם|אותכם|אותך|אתכן|לכם|לכן|לך)(?![${HE}])`,
    words(['ניצור(?:\\s+\\S+)?\\s+קשר', 'נהיה(?:\\s+\\S+)?\\s+בקשר', 'נחזור\\s+(?:אליכם|אליך|אלייך|אליכן)']),
    // S22 (QA ת67): "keep you updated" ("נשמור אתכם מעודכנים", "נשאיר אותך מעודכן"), and getting back, infinitive (B)
    `${words(['נשמור', 'נשאיר', 'לשמור', 'להשאיר'], false)}\\s+(?:אתכם|אותכם|אותך|אתכן|אותכן|אתך)\\s+מעודכ(?:ן|נים|נות|נת)(?![${HE}])`,
    `${words(['תישארו', 'תישארי', 'הישארו', 'הישארי', 'תהיו', 'תהיי'], false)}\\s+מעודכ(?:ן|נים|נות|נת)(?![${HE}])`,
    words(['לחזור\\s+(?:אליכם|אליך|אלייך|אליכן)'], false),
    // the customer asks to be told
    words([
      'עדכנו אותי',
      'עדכני אותי',
      'עדכן אותי',
      'תעדכנו אותי',
      'הודיעו לי',
      'הודיעי לי',
      'תודיעו לי',
      'שלחו לי',
      'שלחי לי',
      'שלח לי',
      'תשלחו לי',
      'הזכירו לי',
      'תזכירו לי',
      'צרו (?:איתי|עמי) קשר',
      'צרו קשר (?:איתי|עמי)',
      '(?:היו )?(?:ה)?ראשונ(?:ים|ות) לדעת',
      // S22 (QA ת67, B): the same, reversed ("רוצים לדעת ראשונים?")
      'לדעת (?:ה)?ראשונ(?:ים|ות)',
      'לבקש (?:עדכון|עדכונים|התראה|הודעה|תזכורת)',
      'בקשו (?:עדכון|עדכונים|התראה|הודעה|תזכורת)',
      'לקבלת (?:עדכון|עדכונים|התראה|התראות|הודעה|הודעות|תזכורת)',
    ]),
  ].join('|'),
  'gu',
);
const RECEIVE = re(words(['תקבלו', 'תקבלי', 'תקבל', 'יקבלו', 'לקבל', 'קבלו', 'קבלי']), 'gu');
const ARRIVE = re(words(['תגיע', 'יגיע', 'יגיעו', 'תגענה', 'תצא', 'יצא', 'יצאו', 'בדרך(?: אליכם| אליך| אלייך)?']), 'gu');
/** S22 (QA ת67, B): present, on its way to you ("האישור יוצא אליכם"): only with what is received in the same clause */
const ARRIVE_NOW = re(words(['יוצא', 'יוצאת', 'יוצאים', 'יוצאות']), 'gu');
/** S22 (QA ת67, B): a message to the customer's phone ("התראות בזמן אמת לטלפון"): a channel when a message is named */
const TO_PHONE = re(`(?<![${HE}])ל(?:טלפון|נייד|סלולרי)(?: (?:ה)?(?:נייד|שלכם|שלך))?(?![${HE}])`, 'u');
const SIGNUP = re(words(['הירשמו', 'הרשמו', 'הירשמי', 'הרשמי', 'הצטרפו', 'הצטרפי', 'להירשם', 'להצטרף', 'הרשמה', 'הצטרפות']), 'gu');
const SIGNUP_TO = re(words(['עדכונים', 'עדכוני', 'התראות', 'ניוזלטר', 'דיוור', 'רשימת (?:ה)?(?:תפוצה|המתנה|דיוור)', 'מועדון']));
/** the sentence is the way to reach us (the customer writes, calls, cancels) */
const INBOUND = re(
  words([
    'לנו',
    'אלינו',
    'אצלנו',
    'איתנו',
    'עמנו',
    'פנו',
    'פנייה',
    'פניות',
    'שירות הלקוחות',
    'צרו קשר',
    'יצירת קשר',
    'פרטי (?:ה)?קשר',
    'הודע(?:ת|ות) (?:ה)?ביטול',
    'רכז(?:ת)? (?:ה)?נגישות',
  ]),
);
/** a negation; S22 (QA ת67, N25): "לא לשכוח", "לא לפספס" ask the reader to do it, they negate nothing */
const NEG_WORD = `(?:(?:לא|אין|בלי|ללא|אינו|אינה|איננו|אינם|אינן|אף פעם|never|not|no|don't|won't)(?!\\s+(?:לשכוח|תשכחו|תשכחי|תשכח|לפספס|תפספסו|תפספסי|להחמיץ|תחמיצו)(?![${HE}])))`;
/** a negation right before the verb, at most one word between them, in the same clause: "האתר לא שולח", "לא נשלח לכם" */
const NEGATED = re(`(?:^|[\\s(])ו?${NEG_WORD}\\s+(?:[^\\s,;:]+\\s+)?$`, 'iu');
const NEGATION = re(`(?<![${HE}])ו?${NEG_WORD}(?![${HE}\\w])`, 'iu');
/** the channel as a field: "כתובת האימייל", "שדה המייל", "האימייל לא תקין", "שם, אימייל, טלפון" */
const FIELD_BEFORE = re(`(?:כתובת|שדה|בכתובת|בשדה|לכתובת)\\s+$|${words(['שם', 'טלפון', 'נייד', 'כתובת', 'כתובת למשלוח'])}\\s*,?\\s*$`);
const FIELD_AFTER = re(`^\\s*(?:לא\\s+)?תקינ|^\\s*,?\\s*${words(['שם', 'טלפון', 'נייד', 'כתובת'])}`);
/**
 * S22 (QA ת67): a label of two words is a field's only when its second word names a field ("כתובת אימייל", "אימייל
 * וטלפון", "שם ומייל"). "חשבונית במייל", "עדכונים ב-SMS", "אישור במייל" offer what is sent, by a channel.
 */
const FIELD_NAME = re(`^ו?(?:שם|שם מלא|טלפון|נייד|כתובת|אימייל|אי-?מייל|מייל|דוא"ל|e-?mail|email|phone|name|address)[:.]?$`, 'iu');
/** S22 (QA ת67): "X: Y", a heading before its line; with a negation in the line, the heading is a label */
const HEADING = /^([^:]{1,40}):\s*(\S.*)$/u;

const LATIN: RegExp[] = [
  /\bwe(?:'ll| will| shall)?\s+(?:send|e-?mail|notify|text|message|remind|contact|let you know|get back to you|be in touch|keep you (?:posted|updated|informed))\b/i,
  /\b(?:will|'ll) be (?:sent|e-?mailed|notified|texted|messaged)\b/i,
  /\byou(?:'ll| will) (?:receive|get|be (?:notified|e-?mailed|updated|texted|sent))\b/i,
  /\b(?:get|be) notified\b/i,
  /\b(?:e-?mail|text|message|notify|remind) me\b/i,
  /\bkeep me (?:posted|updated|informed)\b/i,
  /\blet (?:me|you) know\b/i,
  /\b(?:sign up|subscribe|join) (?:to|for)\b/i,
  /\b(?:check|see) your (?:inbox|e-?mail|spam)\b/i,
  /\b(?:inbox|newsletter|mailing list)\b/i,
  /\breceive (?:updates|notifications|an? (?:e-?mail|sms|text|confirmation|invoice))\b/i,
  /\bupdates? (?:by|via) (?:e-?mail|sms|text|whats ?app)\b/i,
  /\b(?:e-?mail|sms|text|message|confirmation|receipt|invoice)\b.*\bon (?:its|the|their) way\b/i,
  // S22 (QA ת67, B): "Expect an email", "Get updates"
  /\bexpect (?:an? |our )?(?:e-?mail|text|message|sms|confirmation|update)s?\b/i,
  /\bget (?:updates|notifications|alerts)\b/i,
];
/**
 * S22 (QA ת67, K37): a negation in the same clause, at most three words before the English rule's match, speaks for it
 * ("We do not have a newsletter", "No newsletter"). "Don't forget to check your inbox" is not one: a negated forget,
 * miss, hesitate or fail asks the reader to do it.
 */
const LATIN_NEGATED = /(?:^|[\s(])(?:not|no|never|without|nor|cannot|\w+n't)\s+(?!(?:forget|miss|hesitate|fail)\b)(?:\S+\s+){0,3}$/i;
function latinFinding(s: string): string | null {
  for (const rx of LATIN)
    for (const m of s.matchAll(new RegExp(rx.source, `${rx.flags}g`))) {
      const clause =
        s
          .slice(0, m.index)
          .split(/[,;:!?]|\s[-–—]\s/u)
          .pop() ?? '';
      if (!LATIN_NEGATED.test(clause)) return m[0];
    }
  return null;
}

export type PromiseRule = 'send' | 'notify' | 'receive' | 'arrive' | 'signup' | 'channel' | 'latin';
export type PromiseFinding = { rule: PromiseRule; match: string; sentence: string };

/** the sentences of a text: split at . ! ? ; a line break, and the "·" or "•" between items */
export function sentences(text: string): string[] {
  return normalize(text)
    .split(/[.!?;\n]+|\s[·•|]\s/u)
    .map((s) => s.replace(/\s+/g, ' ').trim())
    .filter(Boolean);
}
/** the clauses of a sentence: a negation, "לנו" or a parcel speak for their own clause only */
const clauses = (s: string): string[] => s.split(/[,:،]|\s[-–—]\s/u);

type Hit = { match: string; before: string; after: string; clause: string };
function hits(rx: RegExp, s: string): Hit[] {
  const out: Hit[] = [];
  for (const clause of clauses(s))
    for (const m of clause.matchAll(rx)) {
      const before = clause.slice(0, m.index);
      if (!NEGATED.test(before)) out.push({ match: m[0].trim(), before, after: clause.slice(m.index! + m[0].length), clause });
    }
  return out;
}

function channelFinding(s: string): string | null {
  if (!re(`[${HE}]`).test(s) || INBOUND.test(s)) return null;
  const objects = OBJECT.test(s) || RECEIVED.test(s);
  const words2 = s.split(' ');
  // S22 (QA ת67): one word is a label; two words only when the second names a field ("כתובת אימייל", "אימייל וטלפון")
  const shortLabel = words2.length === 1 || (words2.length === 2 && FIELD_NAME.test(words2[1]!));
  // S22 (QA ת67, K34): "דיוור שיווקי: האתר לא שולח דיוור": the heading of a line that negates is a label
  const heading = HEADING.exec(s);
  // and a heading that is a field's name ("אימייל: shop@…", the contact block) is a label whatever follows it
  const headingEnd = heading && (NEGATION.test(heading[2]!) || FIELD_NAME.test(heading[1]!.trim())) ? heading[1]!.length : -1;
  for (const m of s.matchAll(CHANNEL)) {
    if (m.index! < headingEnd) continue;
    const before = s.slice(0, m.index);
    const after = s.slice(m.index! + m[0].length);
    // a negation speaks for its own clause
    const clause = (before.split(/[,:،]|\s[-–—]\s/u).pop() ?? '') + m[0] + (after.split(/[,:،]|\s[-–—]\s/u)[0] ?? '');
    if (NEGATION.test(clause)) continue;
    const label = shortLabel || (!objects && (FIELD_BEFORE.test(before) || FIELD_AFTER.test(after)));
    if (!label) return m[0];
  }
  // S22 (QA ת67, B): a message to the phone ("התראות בזמן אמת לטלפון"), not negated
  const phone = TO_PHONE.exec(s);
  if (phone && objects && headingEnd < 0 && !NEGATION.test(s)) return phone[0];
  return null;
}

/** Every promise of an email, an SMS, a message or an update in a text the customer reads (see the header). */
export function promiseFindings(text: string): PromiseFinding[] {
  const out: PromiseFinding[] = [];
  for (const s of sentences(text)) {
    const add = (rule: PromiseRule, match: string) => out.push({ rule, match, sentence: s });
    const channel = CHANNEL.test(s);
    CHANNEL.lastIndex = 0;
    const object = OBJECT.test(s);
    const received = RECEIVED.test(s);
    // send
    const sendOk = (h: Hit) => !TO_US.test(h.after) && !SHIP_OBJECT.test(h.after);
    // S22 (QA ת67, B): "לשלוח לכם", "יישלח אליכם" with no parcel in the clause is sending to the customer, like "נשלח לכם"
    const toYou = (h: Hit) => TO_CUSTOMER.test(h.after) && !SHIP.test(h.clause);
    const send =
      hits(SEND_FIRST, s).find((h) => sendOk(h) && (channel || object || toYou(h))) ??
      hits(SEND_OTHER, s).find((h) => sendOk(h) && (channel || object || toYou(h))) ??
      hits(SEND_PAST, s).find((h) => sendOk(h) && (channel || (object && TO_CUSTOMER.test(h.after)))) ??
      hits(SEND_DEFECTIVE, s).find((h) => sendOk(h) && (OBJECT.test(h.before) || RECEIVED.test(h.before)));
    if (send) add('send', send.match);
    // notify
    for (const h of hits(WE_NOTIFY, s)) if (!/^\s+את\s+ה(?!לקוח)/u.test(h.after)) add('notify', h.match);
    for (const h of hits(REMIND, s)) if (channel || /^\s+(?:לכם|לך|אתכם|אותך|אותכם)(?![א-ת])/u.test(h.after)) add('notify', h.match);
    for (const h of hits(NOTIFY_PHRASE, s)) add('notify', h.match);
    // receive, arrive, signup
    const got = hits(RECEIVE, s)[0];
    if (got && (channel || received)) add('receive', got.match);
    // a message on its way, a list to join: when no verb above said so already
    const said = () => out.some((f) => f.sentence === s);
    const coming = hits(ARRIVE, s)[0];
    if (coming && (channel || received) && !said()) add('arrive', coming.match);
    const now = hits(ARRIVE_NOW, s).find((h) => RECEIVED.test(h.clause) && TO_CUSTOMER.test(h.after));
    if (now && !said()) add('arrive', now.match);
    const signup = hits(SIGNUP, s)[0];
    if (signup && (channel || SIGNUP_TO.test(s)) && !said()) add('signup', signup.match);
    // a channel named, with no verb that says so
    if (!out.some((f) => f.sentence === s)) {
      const c = channelFinding(s);
      if (c) add('channel', c);
    }
    const latin = latinFinding(s);
    if (latin) add('latin', latin);
  }
  return out;
}

// ---------- the copy (site/copy/promises.he.json) ----------

export const COPY_FILE = sitePath('copy/promises.he.json');
export const COPY_OUT = sitePath('.generated/copy.he.json');
/** the config the build reads; HD_WRANGLER points a test build at another file (never the deploy's) */
export const WRANGLER_FILE = process.env.HD_WRANGLER ? sitePath(process.env.HD_WRANGLER) : sitePath('api/wrangler.jsonc');

type Line = string | null;
export type Needs = EmailCapability[] | 'any';
export type CopyEntry = { where: string; group?: string } & (
  | { text: string }
  | { email: Line; no_email: Line; needs: Needs }
  | { contact: Line; no_contact: Line }
);
export type CopySource = { note?: string; strings: Record<string, CopyEntry> };
export type Mode = 'email' | 'no_email';
/** what a build has: the capabilities its email provider declares, and whether the shop has contact details */
export type CopyState = { capabilities: readonly EmailCapability[]; contact: boolean };
/** the lines a build shows, by key; null: the line (or its control) is not shown */
export type CopyLines = Record<string, Line>;

export const NO_EMAIL: CopyState = { capabilities: [], contact: false };
export const ALL_EMAIL: CopyState = { capabilities: EMAIL_CAPABILITIES, contact: false };

const KEY = /^[a-z]+(?:\.[a-z_]+)+$/;
/** the lines a page cannot do without: a line in every wording (the order page's line and its error, the checkout's
 * total, the privacy policy's items, the legal pages' contact lines). The others may be null in a wording: their line
 * or control is then not shown. */
export const NEEDED = [
  'checkout.total_note',
  'order.next.received',
  'order.next.shipped',
  'order.next.shipped_no_number',
  'order.next.delivered',
  'order.no_access',
  'privacy.processors',
  'privacy.marketing',
  'legal.draft',
  'legal.returns_notice',
  'legal.accessibility_contact',
] as const;

const kind = (e: CopyEntry): 'text' | 'email' | 'contact' => ('text' in e ? 'text' : 'contact' in e || 'no_contact' in e ? 'contact' : 'email');
const asState = (mode: Mode | CopyState): CopyState => (typeof mode === 'string' ? (mode === 'email' ? ALL_EMAIL : NO_EMAIL) : mode);

/** Whether a line's needs are all real in a build. */
export function needsMet(needs: Needs, capabilities: readonly EmailCapability[]): boolean {
  if (needs === 'any') return capabilities.length > 0;
  return Array.isArray(needs) && needs.length > 0 && needs.every((c) => capabilities.includes(c));
}

/** The line of an entry in a build (a mode stands for every capability, or none, and no contact details). */
export function lineOf(e: CopyEntry, mode: Mode | CopyState): Line {
  const st = asState(mode);
  if ('text' in e) return e.text;
  if (kind(e) === 'contact') {
    const c = e as { contact: Line; no_contact: Line };
    return st.contact ? c.contact : c.no_contact;
  }
  const m = e as { email: Line; no_email: Line; needs: Needs };
  return needsMet(m.needs, st.capabilities) ? m.email : m.no_email;
}

/** what an email line's promises say they need (QA ת62): the copy check wants them in its `needs` */
/**
 * What an email line's promises say they need (QA ת62): the copy check wants them in its `needs`. S22 (QA ת68): wider
 * (a late delivery, a receipt, back in stock, perks and discounts; and in English), and a processor's name ("שירות
 * החשבוניות", "חברת הסליקה") is who handles the data, not what is sent: it implies nothing.
 */
const IMPLIES: [EmailCapability, RegExp][] = [
  ['invoice_email', /חשבוני|(?<![א-ת])[ושכלבהמ]{0,2}קבלה(?![א-ת])|קבלות|invoice|receipt/iu],
  ['order_confirmation', /אישור|פרטי ההזמנה|confirmation|order details/iu],
  ['shipping_update', /משלוח|מעקב|יוצאת|יצאה|נשלחה|החבילה|shipp|tracking|dispatch/iu],
  ['delay_notice', /מועד המסירה|עיכוב|יתעכב|תתעכב|מתעכב|איחור|יתאחר|תתאחר|יתאחרו|מאחר|delay|\blate\b/iu],
  ['back_in_stock', /חוזר|יחזור|יחזרו|למלאי|במלאי|שוב זמין|back in stock|restock/iu],
  ['marketing', /דיוור|שיווק|מוצרים חדשים|ניוזלטר|מבצע|הטב|הנח|קופו|newsletter|offers|discount|promo/iu],
];
const PROCESSOR = /(?:שירות|חברת|ספק)\s+ה\S+/gu;
const implied = new Map<string, EmailCapability[]>();
export function impliedCapabilities(line: string): EmailCapability[] {
  const known = implied.get(line);
  if (known) return known;
  const said = [...new Set(promiseFindings(line).map((f) => f.sentence.replace(PROCESSOR, '')))];
  const caps = IMPLIES.filter(([, rx]) => said.some((s) => rx.test(s))).map(([c]) => c);
  implied.set(line, caps);
  return caps;
}

/**
 * Every state a build can be in, for the checks. S22 (QA ת68): every set of capabilities a provider could declare (all
 * 2^6 = 64, so a group split only by a pair is caught), each with and without contact details: 128 states.
 */
export const STATES: CopyState[] = [false, true].flatMap((contact) =>
  Array.from({ length: 1 << EMAIL_CAPABILITIES.length }, (_, m) => ({
    capabilities: EMAIL_CAPABILITIES.filter((_c, i) => m & (1 << i)),
    contact,
  })),
);

/**
 * What is wrong with the copy, whatever the build: its shape; a line shown without a provider that promises (a
 * `no_email`, `text`, `contact` or `no_contact` line: what the customer reads while no provider sends); an email line
 * that promises what its `needs` do not cover; a line of a group shown without the rest of its group.
 */
export function copyIssues(src: unknown): string[] {
  const out: string[] = [];
  const strings = (src as CopySource | null)?.strings;
  if (!strings || typeof strings !== 'object') return ['the copy has no "strings"'];
  const groups = new Map<string, string[]>();
  for (const [key, e] of Object.entries(strings)) {
    if (!KEY.test(key)) out.push(`${key}: a key is lowercase words joined by dots (page.line)`);
    if (!e || typeof e !== 'object') {
      out.push(`${key}: not an entry`);
      continue;
    }
    if (typeof e.where !== 'string' || !e.where.trim()) out.push(`${key}: "where" says where the line is shown`);
    const has = (k: string) => k in e;
    const shapes = [has('text'), has('email') || has('no_email') || has('needs'), has('contact') || has('no_contact')].filter(Boolean).length;
    if (shapes !== 1) {
      out.push(`${key}: one of "text" (the same line always), "email" + "no_email" + "needs", or "contact" + "no_contact"`);
      continue;
    }
    const k = kind(e);
    const pair = k === 'email' ? (['email', 'no_email'] as const) : k === 'contact' ? (['contact', 'no_contact'] as const) : null;
    if (!pair && (typeof (e as { text: unknown }).text !== 'string' || !(e as { text: string }).text.trim())) out.push(`${key}: "text" is a line`);
    if (pair) {
      const m = e as unknown as Record<string, unknown>;
      for (const w of pair) {
        if (!(w in m)) out.push(`${key}: "${w}" is missing (null hides the line)`);
        else if (m[w] !== null && (typeof m[w] !== 'string' || !(m[w] as string).trim())) out.push(`${key}: "${w}" is a line or null`);
      }
    }
    if (k === 'email') {
      const needs = (e as { needs?: unknown }).needs;
      const known = (c: unknown) => (EMAIL_CAPABILITIES as readonly unknown[]).includes(c);
      if (needs !== 'any' && (!Array.isArray(needs) || !needs.length || !needs.every(known)))
        out.push(`${key}: "needs" is "any" or a list of what the provider must send (${EMAIL_CAPABILITIES.join(', ')})`);
      else {
        const line = (e as { email: Line }).email;
        if (typeof line === 'string') {
          const caps = impliedCapabilities(line);
          // S22 (QA ת68, N7): "any" is for a line that implies no capability; one that does names what it needs
          if (needs === 'any' && caps.length) out.push(`${key}: "needs" is "any", but the email line promises ${caps.join(', ')}: list what it needs`);
          if (needs !== 'any')
            for (const c of caps) if (!(needs as string[]).includes(c)) out.push(`${key}: the email line promises ${c}, which its "needs" do not list`);
        }
      }
    }
    // what is read while no provider sends: never a promise
    const quiet =
      k === 'text'
        ? [lineOf(e, NO_EMAIL)]
        : k === 'contact'
          ? [(e as { contact: Line }).contact, (e as { no_contact: Line }).no_contact]
          : [lineOf(e, NO_EMAIL)];
    for (const shown of quiet)
      if (typeof shown === 'string')
        for (const f of promiseFindings(shown))
          out.push(`${key}: the line shown without an email provider promises (${f.rule}: "${f.match}"): "${f.sentence}"`);
    if (e.group !== undefined) {
      if (typeof e.group !== 'string' || !KEY.test(`${e.group}.x`)) out.push(`${key}: "group" is a lowercase word`);
      else groups.set(e.group, [...(groups.get(e.group) ?? []), key]);
    }
  }
  for (const key of NEEDED) {
    const e = strings[key];
    if (!e) out.push(`${key}: missing (a page needs this line)`);
    else if (STATES.some((st) => typeof lineOf(e, st) !== 'string')) out.push(`${key}: a page needs this line in every wording (null is not allowed)`);
  }
  for (const [name, keys] of groups)
    for (const st of STATES) {
      const shown = new Set(keys.map((k) => lineOf(strings[k]!, st) !== null));
      if (shown.size > 1) {
        out.push(
          `group ${name}: its lines are shown or hidden together (with ${st.capabilities.length ? st.capabilities.join('+') : 'no email'}, some are null and some are not)`,
        );
        break;
      }
    }
  // S22 (QA ת68): every line, in every one of the 128 states: what it shows promises only what that state sends
  if (!out.length)
    for (const [key, e] of Object.entries(strings)) {
      const bad = STATES.find((st) => {
        const shown = lineOf(e, st);
        if (typeof shown !== 'string') return false;
        const isEmail = 'email' in e && shown === e.email && needsMet(e.needs, st.capabilities);
        if (!isEmail) return promiseFindings(shown).length > 0;
        return impliedCapabilities(shown).some((c) => !st.capabilities.includes(c));
      });
      if (bad)
        out.push(
          `${key}: with ${bad.capabilities.join('+') || 'no email'}${bad.contact ? ' and contact details' : ''}, the line it shows promises what that provider does not send`,
        );
    }
  return out;
}

export function loadCopy(file = COPY_FILE): CopySource {
  return JSON.parse(readFileSync(file, 'utf8')) as CopySource;
}

/** The lines of a build: each `email` line only when its needs are real; `contact` only with contact details. A
 * boolean stands for every capability (true) or none (false), without contact details. */
export function selectCopy(src: CopySource, state: CopyState | boolean): CopyLines {
  const st: CopyState = typeof state === 'boolean' ? (state ? ALL_EMAIL : NO_EMAIL) : state;
  return Object.fromEntries(Object.entries(src.strings).map(([k, e]) => [k, lineOf(e, st)]));
}

/**
 * S20 (QA ת62): the promises a build may make: the sentences of each `email` line whose needs its provider really
 * sends. None without a provider. The build check (tools/check-promises.ts) lets these through, and nothing else.
 */
export function allowedPromises(src: CopySource, capabilities: readonly EmailCapability[]): Set<string> {
  const out = new Set<string>();
  for (const e of Object.values(src.strings))
    if ('email' in e && e.email && needsMet(e.needs, capabilities)) for (const f of promiseFindings(e.email)) out.add(f.sentence);
  return out;
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

export type EmailTarget = {
  env: string;
  value: unknown;
  issue: string | null;
  sends: boolean;
  capabilities: EmailCapability[];
  vars: Record<string, unknown>;
};

/**
 * The EMAIL_PROVIDER of the environment the site is built for: `production` for the public build (HD_PUBLIC=1, the
 * deploy), the top level otherwise (development, the local preview, the e2e suite). A value that is not UNDECIDED or a
 * provider from the closed list stops the build (`issue`). `capabilities`: what that provider declares it sends (S20).
 * `vars`: the environment's variables (the contact details, S20 ת61).
 */
export function emailTarget(opts: { publicBuild: boolean; wrangler?: string }): EmailTarget {
  const cfg = parseJsonc(readFileSync(opts.wrangler ?? WRANGLER_FILE, 'utf8')) as {
    vars?: Record<string, unknown>;
    env?: Record<string, { vars?: Record<string, unknown> }>;
  };
  const env = opts.publicBuild ? 'production' : 'top level';
  const vars = opts.publicBuild ? cfg.env?.production?.vars : cfg.vars;
  if (!vars) return { env, value: undefined, issue: `wrangler.jsonc has no vars for ${env}`, sends: false, capabilities: [], vars: {} };
  const value = vars.EMAIL_PROVIDER;
  const capabilities = emailCapabilities(value);
  return { env, value, issue: emailProviderIssue(value), sends: capabilities.length > 0, capabilities, vars };
}
