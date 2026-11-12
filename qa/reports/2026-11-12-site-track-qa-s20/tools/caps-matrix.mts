/**
 * QA S20, ת62: every one of the 64 sets of capabilities a provider could declare (2^6), against the copy file as it is
 * (site/copy/promises.he.json at 8828cab9), with and without contact details. For each set:
 * - the line selectCopy picks, against my own reading of the rule (email only when every need is real; "any" when the
 *   set is not empty);
 * - every promise in a shown line (the S20 definition) belongs to an email line whose needs are all in the set;
 * - my own map from words to capabilities (independent of the S20 IMPLIES list) on every promising sentence shown: what it
 *   says it sends must be in the set (no shipping, delay or invoice line without them);
 * - a group shows all its lines or none.
 * Then copy-file mutations (N1-N8): an email line that promises more than its needs, and a group split by two needs.
 *   cd <copy>/site && node node_modules/tsx/dist/cli.mjs <this> <copy>/site [--json=<out>]
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const SITE = process.argv[2]!;
const jsonOut = process.argv.find((a) => a.startsWith('--json='))?.slice(7);
const L = (await import(pathToFileURL(join(SITE, 'tools/lib/promises.ts')).href)) as typeof import('../build-s20/site/tools/lib/promises');
const { EMAIL_CAPABILITIES } = (await import(pathToFileURL(join(SITE, 'shared/src/email.ts')).href)) as typeof import('../build-s20/site/shared/src/email');
type Cap = (typeof EMAIL_CAPABILITIES)[number];
const src = L.loadCopy(join(SITE, 'copy/promises.he.json'));

// my own map: what a promising sentence says it sends (wider than IMPLIES on purpose)
const MINE: [Cap, RegExp][] = [
  ['invoice_email', /חשבוני|קבלה|invoice|receipt/iu],
  ['order_confirmation', /אישור|פרטי ההזמנה|confirmation/iu],
  ['shipping_update', /משלוח|מעקב|יוצאת|יצאה|החבילה|נשלחה|shipp|tracking/iu],
  ['delay_notice', /מועד המסירה|עיכוב|יתעכב|מתעכב|איחור|יתאחר|ישתנה|delay/iu],
  ['back_in_stock', /חוזר|יחזור|למלאי|במלאי|לבקש עדכון|back in stock/iu],
  ['marketing', /דיוור|שיווק|מוצרים חדשים|ניוזלטר|מבצע|הנחה|newsletter/iu],
];
const subsets: Cap[][] = [];
for (let m = 0; m < 1 << EMAIL_CAPABILITIES.length; m++) subsets.push(EMAIL_CAPABILITIES.filter((_, i) => m & (1 << i)) as Cap[]);
const problems: string[] = [];
const perState: { caps: string; contact: boolean; email_lines: string[] }[] = [];
for (const contact of [false, true])
  for (const caps of subsets) {
    const lines = L.selectCopy(src, { capabilities: caps, contact });
    const label = `${caps.join('+') || 'none'}${contact ? ' +contact' : ''}`;
    const emailShown: string[] = [];
    const groups = new Map<string, Set<boolean>>();
    for (const [key, e] of Object.entries(src.strings)) {
      const shown = lines[key];
      let want: string | null;
      if ('text' in e) want = e.text;
      else if ('contact' in e || 'no_contact' in e) want = contact ? (e as { contact: string | null }).contact : (e as { no_contact: string | null }).no_contact;
      else {
        const m = e as { email: string | null; no_email: string | null; needs: Cap[] | 'any' };
        const met = m.needs === 'any' ? caps.length > 0 : m.needs.every((c) => caps.includes(c));
        want = met ? m.email : m.no_email;
        if (met && m.email !== null) emailShown.push(key);
      }
      if (shown !== want) problems.push(`${label}: ${key} shows ${JSON.stringify(shown)}, my reading wants ${JSON.stringify(want)}`);
      if (e.group) groups.set(e.group, (groups.get(e.group) ?? new Set()).add(shown !== null));
      if (typeof shown === 'string')
        for (const f of L.promiseFindings(shown)) {
          const isEmailLine = 'email' in e && shown === e.email;
          if (!isEmailLine) problems.push(`${label}: ${key} promises in a line that is not its email wording: "${f.sentence}"`);
          // a processor's name ("שירות החשבוניות", "שירות המשלוחים") names who handles the data, it is not a promise of what is sent
          const said = f.sentence.replace(/שירות ה\S+|חברת ה\S+/gu, '');
          for (const [cap, rx] of MINE) if (rx.test(said) && !caps.includes(cap)) problems.push(`${label}: ${key} says ${cap} ("${f.sentence}"), not in the set`);
        }
    }
    for (const [g, s] of groups) if (s.size > 1) problems.push(`${label}: group ${g} is split`);
    perState.push({ caps: caps.join('+') || 'none', contact, email_lines: emailShown });
  }
const only = (c: string) => perState.find((p) => p.caps === c && !p.contact)!.email_lines;
console.log(`64 sets × 2 (contact or not) = ${perState.length} states; problems: ${problems.length}`);
for (const p of problems.slice(0, 40)) console.log(`  ${p}`);
for (const c of EMAIL_CAPABILITIES) console.log(`  ${c} alone → email lines: ${only(c).join(', ') || '(none)'}`);
console.log(`  all six → email lines: ${only(EMAIL_CAPABILITIES.join('+')).join(', ')}`);

// ---- copy-file mutations: does copyIssues stop an email line that promises more than its needs, a split group? ----
type Mut = { id: string; what: string; want: 'stop' | 'pass'; edit: (s: any) => void; oc?: string };
const MUTS: Mut[] = [
  { id: 'N1', want: 'stop', what: 'order.no_access.email adds an invoice (needs: order_confirmation)', edit: (s) => (s.strings['order.no_access'].email = 'אין לנו גישה להזמנה הזו מהדפדפן הזה. את פרטי ההזמנה ואת חשבונית המס שלחנו לאימייל שלכם.') },
  { id: 'N2', want: 'stop', what: 'order.no_access.email adds a delay notice in words outside IMPLIES ("אם המסירה תתאחר")', edit: (s) => (s.strings['order.no_access'].email = 'אין לנו גישה להזמנה הזו מהדפדפן הזה. את פרטי ההזמנה שלחנו לאימייל שלכם, ונעדכן אתכם אם המסירה תתאחר.') },
  { id: 'N3', want: 'stop', what: 'order.no_access.email adds a tracking number ("מספר המעקב יישלח במייל")', edit: (s) => (s.strings['order.no_access'].email = 'אין לנו גישה להזמנה הזו מהדפדפן הזה. את פרטי ההזמנה שלחנו לאימייל שלכם, ומספר המעקב יישלח במייל.') },
  { id: 'N4', want: 'stop', what: 'checkout.email_hint.email adds a receipt ("קבלה") with needs order_confirmation only', edit: (s) => { s.strings['checkout.email_hint'].needs = ['order_confirmation']; s.strings['checkout.email_hint'].email = 'לשם נשלחים אישור ההזמנה והקבלה.'; } },
  { id: 'N5', want: 'stop', what: 'order.no_access.email adds back in stock in words outside IMPLIES ("כשיהיה שוב במלאי")', edit: (s) => (s.strings['order.no_access'].email = 'את פרטי ההזמנה שלחנו לאימייל שלכם. נודיע לכם כשיהיה שוב במלאי.') },
  { id: 'N6', want: 'stop', what: 'order.no_access.email adds marketing in words outside IMPLIES ("הטבות והנחות")', edit: (s) => (s.strings['order.no_access'].email = 'את פרטי ההזמנה שלחנו לאימייל שלכם. נשלח לכם גם הטבות והנחות במייל.') },
  { id: 'N7', want: 'stop', what: 'checkout.total_note.needs = "any": the invoice line is shown with a provider that sends only the confirmation', edit: (s) => (s.strings['checkout.total_note'].needs = 'any'), oc: 'checkout.total_note' },
  { id: 'N8', want: 'stop', what: 'group waitlist split by two needs: offer needs back_in_stock+marketing, submit needs back_in_stock+order_confirmation', edit: (s) => { s.strings['waitlist.offer'].needs = ['back_in_stock', 'marketing']; s.strings['waitlist.submit'].needs = ['back_in_stock', 'order_confirmation']; } },
  { id: 'N8b', want: 'stop', what: 'group waitlist split only by pairs: offer and why need back_in_stock+marketing, submit, done and the story line need back_in_stock+order_confirmation', edit: (s) => { for (const k of ['waitlist.offer', 'waitlist.why']) s.strings[k].needs = ['back_in_stock', 'marketing']; for (const k of ['waitlist.submit', 'waitlist.done', 'story.unavailable_note']) s.strings[k].needs = ['back_in_stock', 'order_confirmation']; } },
  { id: 'N9', want: 'pass', what: 'control: the copy file as it is', edit: () => {} },
];
const mutRows: unknown[] = [];
for (const m of MUTS) {
  const s = JSON.parse(readFileSync(join(SITE, 'copy/promises.he.json'), 'utf8'));
  m.edit(s);
  const issues = L.copyIssues(s);
  const got = issues.length ? 'stop' : 'pass';
  let extra = '';
  if (m.id.startsWith('N8') && !issues.length) {
    const lines = L.selectCopy(s, { capabilities: ['back_in_stock', 'marketing'], contact: false });
    extra = ` | with back_in_stock+marketing: offer=${JSON.stringify(lines['waitlist.offer'])}, submit=${JSON.stringify(lines['waitlist.submit'])}`;
  }
  if (m.oc && !issues.length) {
    const lines = L.selectCopy(s, { capabilities: ['order_confirmation'], contact: false });
    const allowed = L.allowedPromises(s, ['order_confirmation']);
    extra = ` | with order_confirmation only: ${m.oc}=${JSON.stringify(lines[m.oc])}; the gate allows it: ${[...allowed].some((a) => (lines[m.oc!] ?? '').includes(a))}`;
  }
  console.log(`${got === m.want ? 'ok  ' : 'GAP '} ${m.id} want ${m.want} got ${got}  ${m.what}${issues.length ? `  | ${issues[0]}` : ''}${extra}`);
  mutRows.push({ ...m, edit: undefined, got, issues, extra });
}
if (jsonOut) writeFileSync(jsonOut, JSON.stringify({ states: perState.length, problems, perState, mutations: mutRows }, null, 1) + '\n');
