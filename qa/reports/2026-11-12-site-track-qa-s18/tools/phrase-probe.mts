/**
 * QA S18: my own phrase list against the gate's definition of a promise (site/tools/lib/promises.ts, promiseFindings) at
 * 3013d630. Two lists:
 * - PROMISES: lines that promise the customer an email, an SMS, a message or an update (direct and indirect forms, Hebrew
 *   and English). Each one should be caught. `tier`: A = a form the brief or the task names ("נעדכן", "תקבלו", "יישלח",
 *   "נשלח אליכם", "בתיבת הדואר", SMS, וואטסאפ, notify, "we'll email"), B = a common indirect form.
 * - HONEST: lines that promise nothing the shop does not do (the customer writing to us, statuses, legal boilerplate,
 *   negations, a page that shows something). Each one should pass.
 *   cd <copy>/site && node node_modules/tsx/dist/cli.mjs <this file> <copy>/site/tools/lib/promises.ts [--json=<out>]
 */
import { writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const lib = process.argv[2]!;
const { promiseFindings } = (await import(pathToFileURL(lib).href)) as typeof import('../build-s18/site/tools/lib/promises');
const jsonOut = process.argv.find((a) => a.startsWith('--json='))?.slice(7);

type P = { id: string; tier: 'A' | 'B'; text: string; why: string };
const PROMISES: P[] = [
  // the forms the task names
  { id: 'P01', tier: 'A', text: 'נעדכן אתכם כשההזמנה יוצאת למשלוח.', why: 'נעדכן' },
  { id: 'P02', tier: 'A', text: 'תקבלו אישור במייל.', why: 'תקבלו + מייל' },
  { id: 'P03', tier: 'A', text: 'האישור יישלח אליכם בהקדם.', why: 'יישלח + אישור' },
  { id: 'P04', tier: 'A', text: 'נשלח אליכם הודעה כשהמוצר חוזר.', why: 'נשלח אליכם + הודעה' },
  { id: 'P05', tier: 'A', text: 'כשהמוצר יחזור, נשלח אליכם.', why: 'נשלח אליכם, elliptical (what is sent is implied)' },
  { id: 'P06', tier: 'A', text: 'את האישור תמצאו בתיבת הדואר שלכם.', why: 'בתיבת הדואר' },
  { id: 'P07', tier: 'A', text: 'בדקו את תיבת הדואר הנכנס.', why: 'תיבת הדואר, imperative' },
  { id: 'P08', tier: 'A', text: 'עדכוני משלוח ב-SMS.', why: 'SMS, a feature line with no verb' },
  { id: 'P09', tier: 'A', text: 'מעקב משלוח בוואטסאפ.', why: 'וואטסאפ, a feature line with no verb' },
  { id: 'P10', tier: 'A', text: "We'll email you when it ships.", why: "we'll email" },
  { id: 'P11', tier: 'A', text: 'We’ll email you when it ships.', why: "we'll email, typographic apostrophe (U+2019)" },
  { id: 'P12', tier: 'A', text: 'Notify me', why: 'notify' },
  { id: 'P13', tier: 'A', text: "You'll be notified when it's back in stock.", why: 'notified (passive)' },
  { id: 'P14', tier: 'A', text: 'Get notified when it is back.', why: 'get notified' },
  { id: 'P15', tier: 'A', text: 'נשלח לכם SMS כשהשליח בדרך.', why: 'נשלח + SMS' },
  { id: 'P16', tier: 'A', text: 'תקבלו הודעה בוואטסאפ עם מספר המשלוח.', why: 'תקבלו + וואטסאפ' },
  // indirect Hebrew forms
  { id: 'P17', tier: 'B', text: 'תעודכנו במייל כשההזמנה יוצאת.', why: 'תעודכנו (passive future)' },
  { id: 'P18', tier: 'B', text: 'נשמח לעדכן אתכם כשהמוצר חוזר.', why: 'לעדכן (infinitive after נשמח)' },
  { id: 'P19', tier: 'B', text: 'נדאג לעדכן אתכם בכל שלב.', why: 'נדאג לעדכן' },
  { id: 'P20', tier: 'B', text: 'נחזור אליכם במייל תוך יום עסקים.', why: 'נחזור אליכם במייל' },
  { id: 'P21', tier: 'B', text: 'ניצור איתכם קשר בוואטסאפ לתיאום המשלוח.', why: 'ניצור קשר + וואטסאפ' },
  { id: 'P22', tier: 'B', text: 'הירשמו לניוזלטר שלנו.', why: 'newsletter sign-up' },
  { id: 'P23', tier: 'B', text: 'הצטרפו לרשימת התפוצה.', why: 'mailing list sign-up' },
  { id: 'P24', tier: 'B', text: 'SMS עם מספר המעקב יגיע ברגע שהחבילה יוצאת.', why: 'יגיע + SMS' },
  { id: 'P25', tier: 'B', text: 'מייל אישור בדרך אליכם.', why: 'בדרך אליכם + מייל, no verb' },
  { id: 'P26', tier: 'B', text: 'אם לא תשלמו תוך שעה, נשלח לכם תזכורת במייל.', why: 'a conditional "לא" one word before the verb' },
  { id: 'P27', tier: 'B', text: 'בלי לחכות, נשלח לכם אישור במייל.', why: '"בלי" one word before the verb' },
  { id: 'P28', tier: 'B', text: 'תקבלו חשבונית מס.', why: 'תקבלו + חשבונית (no channel)' },
  { id: 'P29', tier: 'B', text: 'תקבלו קישור למעקב.', why: 'תקבלו + קישור (no channel)' },
  { id: 'P30', tier: 'B', text: 'נזכיר לכם במייל לפני שהמבצע נגמר.', why: 'נזכיר + מייל' },
  { id: 'P31', tier: 'B', text: 'היו הראשונים לדעת כשהמוצר חוזר.', why: 'waitlist idiom' },
  { id: 'P32', tier: 'B', text: 'שלחנו לכם את כל הפרטים.', why: 'שלחנו + הפרטים' },
  { id: 'P33', tier: 'B', text: 'ההודעה תגיע לנייד שלכם.', why: 'תגיע + הודעה' },
  { id: 'P34', tier: 'B', text: 'השאירו מייל ונחזור אליכם.', why: 'leave your email and we will get back' },
  { id: 'P35', tier: 'B', text: 'השאירו כתובת אימייל לקבלת עדכון כשהמוצר חוזר.', why: 'לקבלת עדכון' },
  { id: 'P36', tier: 'B', text: 'קבלו התראה כשהמוצר חוזר למלאי.', why: 'קבלו (imperative) + התראה' },
  { id: 'P37', tier: 'B', text: 'שלחו לי הודעה כשהמוצר חוזר.', why: 'the customer asks us to send (like עדכנו אותי)' },
  { id: 'P38', tier: 'B', text: 'בהזמנה תקבלו חשבונית מס דיגיטלית.', why: 'תקבלו + חשבונית' },
  { id: 'P39', tier: 'B', text: 'הודעה במייל תצא אליכם כשהמשלוח יוצא.', why: 'תצא + מייל' },
  { id: 'P40', tier: 'B', text: 'המייל עם האישור כבר בדרך.', why: 'בדרך + מייל' },
  // indirect English forms
  { id: 'P41', tier: 'B', text: 'Email me when available', why: 'email me' },
  { id: 'P42', tier: 'B', text: 'Check your inbox for the confirmation.', why: 'inbox' },
  { id: 'P43', tier: 'B', text: 'A confirmation email is on its way.', why: 'on its way' },
  { id: 'P44', tier: 'B', text: 'Sign up for our newsletter.', why: 'newsletter' },
  { id: 'P45', tier: 'B', text: "We'll let you know when it ships.", why: 'let you know' },
  { id: 'P46', tier: 'B', text: 'Receive updates by email.', why: 'receive updates' },
  { id: 'P47', tier: 'B', text: 'Subscribe for updates', why: 'subscribe' },
  { id: 'P48', tier: 'B', text: 'You’ll receive an SMS with the tracking number.', why: "you'll receive, typographic apostrophe" },
];

type H = { id: string; text: string; why: string };
const HONEST: H[] = [
  { id: 'H01', text: 'ההזמנה נשלחה.', why: 'status' },
  { id: 'H02', text: 'ההזמנה נשלחה אליכם בשליחות עד הבית.', why: 'shipping, not a message' },
  { id: 'H03', text: 'אישור ההזמנה ומצבה מופיעים בדף הזה.', why: 'the page shows it' },
  { id: 'H04', text: 'חשבונית מס תופיע בדף ההזמנה אחרי שתונפק.', why: 'the page shows it' },
  { id: 'H05', text: 'שלחו לנו מייל עם מספר ההזמנה.', why: 'the customer writes to us' },
  { id: 'H06', text: 'אפשר לשלוח לנו הודעה בוואטסאפ.', why: 'the customer writes to us' },
  { id: 'H07', text: 'שולחים לנו מייל? ציינו את מספר ההזמנה.', why: 'the customer writes to us (שולחים, present)' },
  { id: 'H08', text: 'הודעת ביטול שנשלחת אלינו באימייל תטופל תוך 3 ימי עסקים.', why: 'the customer writes to us (terms / cancellation)' },
  { id: 'H09', text: 'ההודעה שלכם נשלחה. נקרא אותה בהקדם.', why: 'a contact form confirmation: the customer wrote to us' },
  { id: 'H10', text: 'קישור למעקב יופיע כאן כשהספק ישלח את החבילה.', why: 'the page shows it; the supplier ships the parcel' },
  { id: 'H11', text: 'נעדכן את המדיניות מעת לעת, והנוסח המעודכן יופיע בדף הזה.', why: 'legal boilerplate: we update the page, not the customer' },
  { id: 'H12', text: 'עדכנו אותנו אם הכתובת השתנתה.', why: 'the customer updates us' },
  { id: 'H13', text: 'אנחנו מקבלים פניות במייל ובוואטסאפ.', why: 'we accept inquiries (מקבלים = we)' },
  { id: 'H14', text: 'תקבלו את ההזמנה תוך 7–14 ימי עסקים.', why: 'delivery time' },
  { id: 'H15', text: 'האתר לא שולח דיוור שיווקי.', why: 'negation' },
  { id: 'H16', text: 'אנחנו לא שולחים מיילים בשלב הזה.', why: 'negation' },
  { id: 'H17', text: 'שימו לב: לא נשלח אישור במייל. האישור מופיע בדף הזה.', why: 'negation, then the page' },
  { id: 'H18', text: 'עודכן לאחרונה: 12.11.2026', why: 'legal date' },
  { id: 'H19', text: 'המחירים מתעדכנים מדי יום.', why: 'prices' },
  { id: 'H20', text: 'בקשת הביטול נשלחה לספק.', why: 'a request to the supplier' },
  { id: 'H21', text: 'המוצרים נשלחים ישירות מהספק.', why: 'shipping' },
  { id: 'H22', text: 'אימייל', why: 'a field label' },
  { id: 'H23', text: 'לפנייה בנושא ההזמנה, אם יהיה צורך.', why: 'S18 line' },
  { id: 'H24', text: 'ההזמנה בדרך אליכם. מספר המשלוח למעלה.', why: 'S18 line' },
  { id: 'H25', text: 'Your order was sent to the supplier.', why: 'status, English' },
  { id: 'H26', text: 'שירות הלקוחות זמין באימייל ובטלפון.', why: 'a contact channel, no promise of sending' },
];

const promises = PROMISES.map((p) => {
  const f = promiseFindings(p.text);
  return { ...p, caught: f.length > 0, findings: f };
});
const honest = HONEST.map((h) => {
  const f = promiseFindings(h.text);
  return { ...h, flagged: f.length > 0, findings: f };
});
for (const p of promises) console.log(`${p.caught ? 'caught' : 'MISSED'}  ${p.id} [${p.tier}] ${p.text}   (${p.why})${p.caught ? `  ← ${p.findings[0]!.rule}:${p.findings[0]!.match}` : ''}`);
console.log('');
for (const h of honest) console.log(`${h.flagged ? 'FALSE+' : 'ok    '}  ${h.id} ${h.text}   (${h.why})${h.flagged ? `  ← ${h.findings[0]!.rule}:${h.findings[0]!.match}` : ''}`);
const missed = promises.filter((p) => !p.caught);
const fp = honest.filter((h) => h.flagged);
const summary = {
  promises: promises.length,
  caught: promises.length - missed.length,
  missed_tier_a: missed.filter((p) => p.tier === 'A').map((p) => p.id),
  missed_tier_b: missed.filter((p) => p.tier === 'B').map((p) => p.id),
  honest: honest.length,
  false_positives: fp.map((h) => h.id),
};
console.log('\n' + JSON.stringify(summary));
if (jsonOut) writeFileSync(jsonOut, JSON.stringify({ summary, promises, honest }, null, 1) + '\n');
