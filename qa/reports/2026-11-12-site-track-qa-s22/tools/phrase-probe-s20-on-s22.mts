/**
 * QA S20: a FRESH phrase list against the S20 definition of a promise (site/tools/lib/promises.ts at 8828cab9). None of
 * these lines is in QA S18's lists, which S20 keeps as a fixture (tools/test/fixtures/promise-phrases.json): this asks
 * whether the definition generalises, not whether it learned the list.
 * - PROMISES: each promises the customer an email, an SMS, a message, an update or contact back. tier A = the same kind as
 *   a form the S18 brief named (a verb of sending / updating / receiving with what is sent, "keep you updated"); B = an
 *   indirect or colloquial form.
 * - HONEST: each promises nothing the shop does not do (the customer writes to us, shipping, statuses, labels, the S20
 *   contact lines, negations, a heading "X: Y").
 *   cd <copy>/site && node node_modules/tsx/dist/cli.mjs <this file> <copy>/site/tools/lib/promises.ts [--json=<out>]
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const lib = process.argv[2]!;
const { promiseFindings, normalize } = (await import(pathToFileURL(lib).href)) as typeof import('./s22lib/promises');
const jsonOut = process.argv.find((a) => a.startsWith('--json='))?.slice(7);
const fixture = process.argv.find((a) => a.startsWith('--fixture='))?.slice(10);

type P = { id: string; tier: 'A' | 'B'; text: string; why: string };
const PROMISES: P[] = [
  { id: 'N01', tier: 'A', text: 'אישור ההזמנה ישלח למייל שלכם.', why: 'ישלח (one yod) + מייל' },
  { id: 'N02', tier: 'A', text: 'פרטי המשלוח ישלחו אליכם בהודעה.', why: 'ישלחו + הודעה' },
  { id: 'N03', tier: 'A', text: 'נעדכן בהודעה ברגע שהחבילה יוצאת.', why: 'נעדכן' },
  { id: 'N04', tier: 'A', text: 'אנחנו נשלח לכם מייל עם קוד הקופון.', why: 'נשלח לכם מייל' },
  { id: 'N05', tier: 'A', text: 'מחכה לכם מייל עם כל הפרטים.', why: 'a channel, no verb of ours' },
  { id: 'N06', tier: 'A', text: 'הקופון יישלח לכם ב-SMS.', why: 'יישלח + SMS' },
  { id: 'N07', tier: 'A', text: 'בקרוב תקבלו מאיתנו עדכון.', why: 'תקבלו עדכון' },
  { id: 'N08', tier: 'A', text: 'ההתראה תישלח לטלפון הנייד.', why: 'תישלח + התראה' },
  { id: 'N09', tier: 'A', text: 'נעדכנכם על כל שינוי.', why: 'נעדכנכם' },
  { id: 'N10', tier: 'A', text: 'עדכון יגיע אליכם כשהמוצר יחזור למלאי.', why: 'יגיע + עדכון' },
  { id: 'N11', tier: 'A', text: 'נתריע לכם כשהמחיר יורד.', why: 'נתריע' },
  { id: 'N12', tier: 'A', text: 'מספר המעקב יופיע במייל שתקבלו.', why: 'שתקבלו + מייל' },
  { id: 'N13', tier: 'A', text: 'You will get an email once it ships.', why: 'you will get' },
  { id: 'N14', tier: 'A', text: 'We’ll text you the tracking number.', why: "we'll text" },
  { id: 'N15', tier: 'A', text: 'עם יציאת החבילה יישלח מספר מעקב.', why: 'יישלח + a tracking number (not in OBJECT)' },
  { id: 'N16', tier: 'A', text: 'תקבלו את מספר המעקב ברגע שהחבילה יוצאת.', why: 'תקבלו + a tracking number (not in RECEIVED)' },
  { id: 'N17', tier: 'A', text: 'נשמור אתכם מעודכנים.', why: '"keep you updated", the Hebrew idiom' },
  { id: 'N18', tier: 'A', text: 'החשבונית תגיע אליכם תוך 24 שעות.', why: 'תגיע + חשבונית' },
  { id: 'N19', tier: 'A', text: 'נהיה איתכם בקשר לגבי מועד המסירה.', why: 'נהיה בקשר' },
  { id: 'N20', tier: 'A', text: 'ניידע אתכם ברגע שהמוצר זמין.', why: 'ניידע' },
  { id: 'N21', tier: 'A', text: 'אנו נודיעך על כל עיכוב.', why: 'נודיעך' },
  { id: 'N22', tier: 'A', text: 'נשלח קוד אימות ב-SMS.', why: 'נשלח + SMS' },
  { id: 'N23', tier: 'A', text: 'Order updates via WhatsApp', why: 'updates via whatsapp' },
  { id: 'N24', tier: 'A', text: 'תזכורת תשלח יום לפני המסירה.', why: 'תשלח (defective spelling of תישלח) + תזכורת' },
  { id: 'N25', tier: 'B', text: 'לא לשכוח לבדוק גם בתיקיית הספאם.', why: 'the spam folder: an email is coming' },
  { id: 'N26', tier: 'B', text: 'נשמח לשלוח לכם את הקטלוג החדש.', why: 'לשלוח לכם, a catalogue (marketing)' },
  { id: 'N27', tier: 'B', text: 'רוצים לדעת ראשונים? השאירו פרטים.', why: '"לדעת ראשונים" (S18 had "היו הראשונים לדעת")' },
  { id: 'N28', tier: 'B', text: 'Expect an email from us shortly.', why: 'expect an email' },
  { id: 'N29', tier: 'B', text: 'קוד הקופון ממתין לכם בתיבה.', why: '"בתיבה", the mailbox without "דואר"' },
  { id: 'N30', tier: 'B', text: 'ננסה לחזור אליכם עוד היום.', why: '"לחזור אליכם", infinitive' },
  { id: 'N31', tier: 'B', text: 'Get updates', why: 'get updates' },
  { id: 'N32', tier: 'B', text: 'התראות בזמן אמת לטלפון.', why: 'a feature line, no channel word' },
  { id: 'N33', tier: 'B', text: 'נודה אם תאשרו את קבלת המייל.', why: 'an email that was sent' },
  { id: 'N34', tier: 'B', text: 'המבצעים הבאים יגיעו ישר למייל.', why: 'יגיעו + מייל' },
  { id: 'N35', tier: 'B', text: 'קבלו 10% הנחה בהרשמה לניוזלטר.', why: 'ניוזלטר' },
  { id: 'N36', tier: 'B', text: 'נשלח לך לינק למעקב.', why: '"לינק" (not "קישור")' },
  { id: 'N37', tier: 'B', text: 'תקבלו מאיתנו מסר ברגע שהמוצר מגיע.', why: '"מסר"' },
  { id: 'N38', tier: 'B', text: 'הודעת פוש תקפוץ כשההזמנה יוצאת.', why: 'push notification' },
  { id: 'N39', tier: 'B', text: 'נעדכן אתכן.', why: 'נעדכן, feminine plural' },
  { id: 'N40', tier: 'B', text: 'האישור יוצא אליכם ברגע שהתשלום עובר.', why: '"יוצא אליכם" + אישור' },
];
const HONEST: P[] = [
  { id: 'K01', tier: 'A', text: 'שלחו לנו את מספר ההזמנה ונבדוק.', why: 'the customer writes to us' },
  { id: 'K02', tier: 'A', text: 'הודעת ביטול אפשר לשלוח לנו באימייל או בטלפון.', why: 'cancellation, to us' },
  { id: 'K03', tier: 'A', text: 'החבילה נשלחת אליכם ישירות מהספק.', why: 'shipping, not a message' },
  { id: 'K04', tier: 'A', text: 'נשלח את ההזמנה תוך 3 ימי עסקים.', why: 'we ship the order' },
  { id: 'K05', tier: 'A', text: 'ההזמנה תצא אליכם תוך 3 ימי עסקים.', why: 'shipping' },
  { id: 'K06', tier: 'A', text: 'אפשר לעדכן אותנו בכתובת חדשה עד המשלוח.', why: 'the customer updates us' },
  { id: 'K07', tier: 'A', text: 'עדכנו את הכתובת בסל לפני התשלום.', why: 'the customer edits the address' },
  { id: 'K08', tier: 'A', text: 'תקבלו את החבילה עד הבית.', why: 'delivery' },
  { id: 'K09', tier: 'A', text: 'עם קבלת החבילה, בדקו שהיא שלמה.', why: 'delivery' },
  { id: 'K10', tier: 'A', text: 'מספר המשלוח יופיע בדף ההזמנה.', why: 'the page shows it' },
  { id: 'K11', tier: 'A', text: 'אין צורך להירשם כדי להזמין.', why: 'no sign-up' },
  { id: 'K12', tier: 'A', text: 'שם מלא, טלפון ואימייל', why: 'field labels' },
  { id: 'K13', tier: 'A', text: 'כתובת האימייל אינה תקינה.', why: 'a field error' },
  { id: 'K14', tier: 'A', text: 'אימייל: shop@hd-qa.co.il', why: 'the S20 contact block' },
  { id: 'K15', tier: 'A', text: 'אפשר לכתוב לנו עם מספר ההזמנה, ונבדוק אותה.', why: 'S20 order.no_access_contact' },
  { id: 'K16', tier: 'A', text: 'להודעת ביטול: פנו אלינו באחת הדרכים שלמטה, וציינו את מספר ההזמנה.', why: 'S20 legal.returns_notice (contact)' },
  { id: 'K17', tier: 'A', text: 'נשמח לשמוע על כל קושי. פניות לרכז/ת הנגישות נענות תוך 5 ימי עסקים.', why: 'S20 legal.accessibility_contact (contact)' },
  { id: 'K18', tier: 'A', text: 'המוצר נשלח מהמחסן של הספק בסין.', why: 'shipping (נשלח = is shipped)' },
  { id: 'K19', tier: 'A', text: 'פרטי ההזמנה נשלחו לספק.', why: 'to the supplier' },
  { id: 'K20', tier: 'A', text: 'שינוי בכתובת? שלחו לנו מייל לפני שההזמנה יוצאת.', why: 'the customer writes to us' },
  { id: 'K21', tier: 'A', text: 'ההחזר הכספי יבוצע תוך 14 יום מקבלת הודעת הביטול.', why: 'the law, refunds' },
  { id: 'K22', tier: 'A', text: 'לא נשלח לכם מיילים שיווקיים.', why: 'negation' },
  { id: 'K23', tier: 'A', text: 'נעדכן את המחירים בהתאם לשער הדולר.', why: 'נעדכן + a thing' },
  { id: 'K24', tier: 'A', text: 'המייל שלכם לא יועבר לאף אחד.', why: 'negation, privacy' },
  { id: 'K25', tier: 'A', text: 'קבלה על התשלום מופיעה בדף ההזמנה.', why: 'the page shows it' },
  { id: 'K26', tier: 'A', text: 'הזמנה שנשלחה לא ניתנת לביטול באתר.', why: 'a status' },
  { id: 'K27', tier: 'A', text: 'הסכמה לדיוור אינה תנאי לרכישה.', why: 'negation' },
  { id: 'K28', tier: 'A', text: 'שמרו את מספר ההזמנה. בלי מייל, הוא הדרך היחידה לזהות אותה.', why: 'negation (בלי)' },
  { id: 'K29', tier: 'A', text: 'שירות המשלוחים יעדכן את הסטטוס בדף.', why: 'a third party updates the page' },
  { id: 'K30', tier: 'A', text: 'לעדכון כתובת, כתבו לנו.', why: 'to us' },
  { id: 'K31', tier: 'A', text: 'אנחנו לא שולחים ולא נשלח מיילים שיווקיים.', why: 'negation twice' },
  { id: 'K32', tier: 'A', text: 'מיילים שיווקיים לא נשלחים מהאתר.', why: 'negation, passive' },
  { id: 'K33', tier: 'A', text: 'אין מיילים, אין SMS ואין הודעות.', why: 'negation per clause' },
  { id: 'K34', tier: 'B', text: 'דיוור שיווקי: האתר לא שולח דיוור.', why: 'a heading "X: Y", then a negation' },
  { id: 'K35', tier: 'B', text: 'ניוזלטר: אין.', why: 'a heading "X: Y", a negation' },
  { id: 'K36', tier: 'B', text: 'מדיניות הדיוור: האתר אינו שולח מיילים שיווקיים.', why: 'a heading "X: Y", then a negation' },
  { id: 'K37', tier: 'B', text: 'We do not have a newsletter.', why: 'English negation' },
  { id: 'K38', tier: 'B', text: 'No SMS, no emails: the order page shows everything.', why: 'English negation' },
  { id: 'K39', tier: 'B', text: 'הודעה על ביטול תישלח לספק מיד.', why: 'to the supplier' },
  { id: 'K40', tier: 'B', text: 'האתר לא יעדכן אתכם במייל, וגם לא ב-SMS.', why: 'negation, two words before the verb' },
];
const caught = (t: string) => promiseFindings(t);
let fx: { promises?: { text: string }[]; honest?: { text: string }[]; site_honest?: string[] } = {};
if (fixture) fx = JSON.parse(readFileSync(fixture, 'utf8'));
const inFixture = new Set(JSON.stringify(fx).match(/"[^"]{6,}"/g)?.map((s) => normalize(s.slice(1, -1))) ?? []);
const rows: unknown[] = [];
let miss = 0;
let fp = 0;
for (const p of PROMISES) {
  const f = caught(p.text);
  if (!f.length) miss++;
  rows.push({ ...p, kind: 'promise', caught: f.length > 0, rules: f.map((x) => `${x.rule}:${x.match}`), in_fixture: inFixture.has(normalize(p.text)) });
  console.log(`${f.length ? 'caught' : 'MISSED'}  ${p.id} [${p.tier}] ${p.text}   (${p.why})${f.length ? `  ← ${f.map((x) => `${x.rule}:${x.match}`).join(', ')}` : ''}`);
}
console.log('');
for (const p of HONEST) {
  const f = caught(p.text);
  if (f.length) fp++;
  rows.push({ ...p, kind: 'honest', flagged: f.length > 0, rules: f.map((x) => `${x.rule}:${x.match}`), in_fixture: inFixture.has(normalize(p.text)) });
  console.log(`${f.length ? 'FALSE+' : 'ok    '}  ${p.id} [${p.tier}] ${p.text}   (${p.why})${f.length ? `  ← ${f.map((x) => `${x.rule}:${x.match}`).join(', ')}` : ''}`);
}
const summary = {
  promises: PROMISES.length,
  caught: PROMISES.length - miss,
  missed_tier_a: PROMISES.filter((p) => p.tier === 'A' && !caught(p.text).length).map((p) => p.id),
  missed_tier_b: PROMISES.filter((p) => p.tier === 'B' && !caught(p.text).length).map((p) => p.id),
  honest: HONEST.length,
  false_positives: HONEST.filter((p) => caught(p.text).length).map((p) => p.id),
  in_fixture: rows.filter((r) => (r as { in_fixture: boolean }).in_fixture).length,
};
console.log('\n' + JSON.stringify(summary));
if (jsonOut) writeFileSync(jsonOut, JSON.stringify({ summary, rows }, null, 1) + '\n');
