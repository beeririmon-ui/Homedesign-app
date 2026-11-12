/**
 * QA S22, ת68: NEW copy-file mutations against copyIssues (site/tools/lib/promises.ts at 9b6c6746), beyond my S20 N1-N9.
 * - M-any-*: `needs: "any"` on a line that promises a specific message, in words outside IMPLIES (the rule "any only for a
 *   line that implies no capability" is only as wide as IMPLIES); and controls in IMPLIES' words.
 * - M-list-*: a needs list that is narrower than what the line promises, in words outside IMPLIES.
 * - M-grp-*: groups split by contact details, by a no_email line, by "any" against a list.
 * - M-ctl-*: controls that must pass.
 * For each mutation that passes copyIssues, the tool also shows what a build with ONE capability shows (the worst case:
 * the line appears with a provider that does not send what it promises).
 *   cd <copy>/site && node node_modules/tsx/dist/cli.mjs <this> <copy>/site [--json=<out>]
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const SITE = process.argv[2]!;
const jsonOut = process.argv.find((a) => a.startsWith('--json='))?.slice(7);
type Lib = {
  copyIssues: (s: unknown) => string[];
  selectCopy: (s: unknown, st: { capabilities: string[]; contact: boolean }) => Record<string, string | null>;
  impliedCapabilities: (l: string) => string[];
  promiseFindings: (t: string) => { rule: string; match: string }[];
  STATES: unknown[];
};
const L = (await import(pathToFileURL(join(SITE, 'tools/lib/promises.ts')).href)) as Lib;
const base = () => JSON.parse(readFileSync(join(SITE, 'copy/promises.he.json'), 'utf8'));
const PRIV = 'הפרטים מועברים רק למי שצריך אותם לביצוע ההזמנה: הספק ושירות המשלוחים, חברת הסליקה, שירות החשבוניות ושירות המיילים.';

type Mut = { id: string; want: 'stop' | 'pass'; what: string; edit: (s: any) => void; probe?: [string, string[]] };
const anyLine = (id: string, want: 'stop' | 'pass', extra: string, what: string): Mut => ({
  id,
  want,
  what: `privacy.processors (needs "any") + "${extra}": ${what}`,
  edit: (s) => (s.strings['privacy.processors'].email = `${PRIV} ${extra}`),
  probe: ['privacy.processors', ['invoice_email']],
});
const MUTS: Mut[] = [
  anyLine('M-any-1', 'stop', 'נעדכן אתכם כשהשליח יוצא לדרך.', 'a shipping update, words outside IMPLIES (שליח, יוצא)'),
  anyLine('M-any-2', 'stop', 'נודיע לכם כשהמחיר יורד.', 'a price alert: a promise no capability covers'),
  anyLine('M-any-3', 'stop', "We'll email you the moment it's on its way.", 'a shipping update in English, outside IMPLIES'),
  anyLine('M-any-4', 'stop', 'נשלח לכם השראה ורעיונות לבית במייל.', 'marketing, outside IMPLIES (השראה)'),
  anyLine('M-any-5', 'stop', 'נעדכן אתכם כשהמוצר יהיה זמין.', 'back in stock, outside IMPLIES (יהיה זמין)'),
  anyLine('M-any-6', 'stop', 'אם יהיה שינוי בתאריך, נודיע לכם.', 'a delay notice, outside IMPLIES (שינוי בתאריך)'),
  anyLine('M-any-7', 'stop', 'את חשבון המס נשלח לכם במייל.', 'an invoice, outside IMPLIES (חשבון המס)'),
  anyLine('M-any-8', 'stop', 'נעדכן אתכם כשהחבילה יוצאת.', 'control in IMPLIES words (החבילה, יוצאת)'),
  anyLine('M-any-9', 'stop', 'נשלח לכם קופון הנחה במייל.', 'control in IMPLIES words (קופון, הנחה)'),
  {
    id: 'M-any-10',
    want: 'pass',
    what: 'checkout.total_note: needs "any" and an email line with no promise ("כולל מע"מ.")',
    edit: (s) => {
      s.strings['checkout.total_note'].needs = 'any';
      s.strings['checkout.total_note'].email = 'כולל מע"מ.';
    },
  },
  {
    id: 'M-any-11',
    want: 'stop',
    what: 'checkout.email_hint: needs "any" and "לשם נשלחים כל העדכונים על ההזמנה." (an update of unnamed kind)',
    edit: (s) => {
      s.strings['checkout.email_hint'].needs = 'any';
      s.strings['checkout.email_hint'].email = 'לשם נשלחים כל העדכונים על ההזמנה.';
    },
    probe: ['checkout.email_hint', ['marketing']],
  },
  {
    id: 'M-list-1',
    want: 'stop',
    what: 'order.no_access (needs order_confirmation) + "ונודיע לכם כשהשליח בדרך." (shipping, outside IMPLIES)',
    edit: (s) => (s.strings['order.no_access'].email = 'אין לנו גישה להזמנה הזו מהדפדפן הזה. את פרטי ההזמנה שלחנו לאימייל שלכם, ונודיע לכם כשהשליח בדרך.'),
    probe: ['order.no_access', ['order_confirmation']],
  },
  {
    id: 'M-list-2',
    want: 'stop',
    what: 'order.no_access (needs order_confirmation) + "גם חשבון המס נשלח לשם." (an invoice, outside IMPLIES)',
    edit: (s) => (s.strings['order.no_access'].email = 'אין לנו גישה להזמנה הזו מהדפדפן הזה. את פרטי ההזמנה שלחנו לאימייל שלכם. גם חשבון המס נשלח לשם.'),
    probe: ['order.no_access', ['order_confirmation']],
  },
  {
    id: 'M-list-3',
    want: 'stop',
    what: 'waitlist.why (needs back_in_stock) + "ונשלח לכם גם קולקציות חדשות." (marketing, outside IMPLIES)',
    edit: (s) => (s.strings['waitlist.why'].email = 'נשלח הודעה אחת כשהמוצר חוזר למלאי, ונשלח לכם גם קולקציות חדשות.'),
    probe: ['waitlist.why', ['back_in_stock']],
  },
  {
    id: 'M-grp-1',
    want: 'stop',
    what: 'group waitlist: waitlist.why becomes a contact line (contact: its text, no_contact: null)',
    edit: (s) => (s.strings['waitlist.why'] = { where: s.strings['waitlist.why'].where, group: 'waitlist', contact: 'אפשר לכתוב לנו ונבדוק מתי המוצר חוזר.', no_contact: null }),
  },
  {
    id: 'M-grp-2',
    want: 'stop',
    what: 'group waitlist: waitlist.why gets a no_email line ("המלאי אינו זמין כעת.") while the rest of the group is null',
    edit: (s) => (s.strings['waitlist.why'].no_email = 'המלאי אינו זמין כעת.'),
  },
  {
    id: 'M-grp-3',
    want: 'stop',
    what: 'group waitlist: waitlist.done needs "any" (its line has no promise words in IMPLIES? it has "חוזר")',
    edit: (s) => (s.strings['waitlist.done'].needs = 'any'),
  },
  {
    id: 'M-grp-4',
    want: 'stop',
    what: 'group waitlist: waitlist.submit needs "any" and its line "עדכנו אותי" (a promise, no capability word)',
    edit: (s) => (s.strings['waitlist.submit'].needs = 'any'),
  },
  {
    id: 'M-grp-5',
    want: 'stop',
    what: 'a new group "pair" of two lines split by three capabilities (a triple, not a pair)',
    edit: (s) => {
      s.strings['order.delay.followup'].group = 'pair';
      s.strings['order.delay.followup'].needs = ['delay_notice', 'shipping_update', 'order_confirmation'];
      s.strings['checkout.marketing_consent'].group = 'pair';
      s.strings['checkout.marketing_consent'].needs = ['marketing', 'delay_notice', 'shipping_update', 'order_confirmation'];
    },
  },
  { id: 'M-ctl-1', want: 'pass', what: 'control: the copy file as it is', edit: () => {} },
  {
    id: 'M-ctl-2',
    want: 'pass',
    what: 'control: privacy.processors keeps "any" and names one more processor ("ושירות ה-SMS")',
    edit: (s) => (s.strings['privacy.processors'].email = PRIV.replace('ושירות המיילים', 'שירות המיילים ושירות ה-SMS')),
  },
];
console.log(`STATES: ${L.STATES.length}`);
const rows: unknown[] = [];
let ok = 0;
for (const m of MUTS) {
  const s = base();
  m.edit(s);
  const issues = L.copyIssues(s);
  const got = issues.length ? 'stop' : 'pass';
  if (got === m.want) ok++;
  let shown = '';
  if (m.probe && got === 'pass') {
    const [key, caps] = m.probe;
    const line = L.selectCopy(s, { capabilities: caps, contact: false })[key];
    shown = ` | with ${caps.join('+')} only, ${key} shows: ${JSON.stringify(line)} (implied: ${JSON.stringify(line ? L.impliedCapabilities(line) : [])})`;
  }
  console.log(`${got === m.want ? 'ok  ' : 'GAP '} ${m.id} want ${m.want} got ${got}  ${m.what}${issues.length ? `  | ${issues[0]}` : ''}${shown}`);
  rows.push({ id: m.id, want: m.want, got, what: m.what, issues, shown });
}
console.log(`\n${ok}/${MUTS.length} as expected`);
if (jsonOut) writeFileSync(jsonOut, JSON.stringify({ states: L.STATES.length, ok, total: MUTS.length, rows }, null, 1) + '\n');
