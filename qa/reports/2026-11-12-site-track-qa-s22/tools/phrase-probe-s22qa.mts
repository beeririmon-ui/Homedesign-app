/**
 * QA S22: a NEW fresh phrase list against the S22 definition of a promise (site/tools/lib/promises.ts at 9b6c6746).
 * Written before the first run and not edited after it (except for the overlap rule below). None of these lines is in
 * S22's fixture (tools/test/fixtures/promise-phrases.json), in QA S20's fresh list (tools/test/external/qa-s20-fresh.json)
 * or in frontend-dev's fresh list (tools/test/external/s22-fresh.json): the tool checks that with --fixture/--external and
 * reports every overlap (`in_lists`).
 * - kind "variant": a near variant of a QA S20 line that S22 closed, or of the form an S22 rule was written for (N15/N16
 *   tracking number, N17 "keep you updated", N24 "תשלח", N40 "יוצא אליכם", X13/X17 two-word labels, K34 heading before a
 *   negation, K37 English negation). This is the overfitting probe: a rule that learned the line, not the form, misses the
 *   variant (promises) or trips on an honest line of the same shape (honest).
 * - kind "general": the same kinds of promise / honest line, written fresh.
 * - tier A = the same kind as a form the S18/S20/S22 briefs named (a verb of sending/updating/contacting/receiving with
 *   what is sent, a channel with what is sent, "keep you updated", signing up); B = indirect or colloquial.
 * - PROMISES: each promises the customer an email, an SMS, a message, an update or contact back.
 * - HONEST: each promises no message (physical shipping of a product, on-screen/page information, the customer writing to
 *   us, refunds, field labels and errors, negations, product names).
 *   cd <copy>/site && node node_modules/tsx/dist/cli.mjs <this file> <lib>/promises.ts [--json=<out>] [--fixture=<f>]
 *     [--external=<f1>,<f2>] [--compare=<older lib>/promises.ts]
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

type Lib = { promiseFindings: (t: string) => { rule: string; match: string }[]; normalize: (t: string) => string };
const lib = (await import(pathToFileURL(process.argv[2]!).href)) as Lib;
const arg = (k: string) => process.argv.find((a) => a.startsWith(`--${k}=`))?.slice(k.length + 3);
const jsonOut = arg('json');
const older = arg('compare') ? ((await import(pathToFileURL(arg('compare')!).href)) as Lib) : null;

type P = { id: string; tier: 'A' | 'B'; kind: 'variant' | 'general'; of?: string; text: string };
const PROMISES: P[] = [
  { id: 'PR01', tier: 'A', kind: 'variant', of: 'N15', text: 'עם יציאת המשלוח יישלח לינק למעקב.' },
  { id: 'PR02', tier: 'A', kind: 'variant', of: 'N16', text: 'תקבלו את הלינק למעקב ביום שהחבילה יוצאת.' },
  { id: 'PR03', tier: 'A', kind: 'variant', of: 'N15', text: "מס' המעקב יישלח אחרי האריזה." },
  { id: 'PR04', tier: 'A', kind: 'variant', of: 'N16', text: 'פרטי המעקב יגיעו אליכם כשהחבילה יוצאת.' },
  { id: 'PR05', tier: 'A', kind: 'variant', of: 'N17', text: 'נשאיר אתכן מעודכנות.' },
  { id: 'PR06', tier: 'B', kind: 'variant', of: 'N17', text: 'נקפיד לשמור אתכם בעניינים.' },
  { id: 'PR07', tier: 'A', kind: 'variant', of: 'N24', text: 'תשלח אליכם הודעה ביום המסירה.' },
  { id: 'PR08', tier: 'A', kind: 'variant', of: 'N24', text: 'תשלח לכם תזכורת יום לפני.' },
  { id: 'PR09', tier: 'A', kind: 'variant', of: 'N40', text: 'האישור מגיע אליכם מיד אחרי התשלום.' },
  { id: 'PR10', tier: 'A', kind: 'variant', of: 'N40', text: 'החשבונית יוצאת אליכם ברגע שהתשלום מאושר.' },
  { id: 'PR11', tier: 'A', kind: 'variant', of: 'X17', text: 'קבלה במייל' },
  { id: 'PR12', tier: 'A', kind: 'variant', of: 'X17', text: 'אישור בוואטסאפ' },
  { id: 'PR13', tier: 'A', kind: 'variant', of: 'X17', text: 'מייל אישור' },
  { id: 'PR14', tier: 'A', kind: 'variant', of: 'K34 rule', text: 'ניוזלטר: בלי ספאם, רק השראה.' },
  { id: 'PR15', tier: 'A', kind: 'variant', of: 'K34 rule', text: 'עדכוני משלוח ב-SMS: בלי הרשמה ובלי עלות.' },
  { id: 'PR16', tier: 'A', kind: 'variant', of: 'K34 rule', text: 'התראות לוואטסאפ: אין צורך באפליקציה.' },
  { id: 'PR17', tier: 'A', kind: 'variant', of: 'K37 rule', text: "No account needed and we'll email the receipt." },
  { id: 'PR18', tier: 'A', kind: 'variant', of: 'K37 rule', text: "Not sure about the size? We'll email you the size chart." },
  { id: 'PR19', tier: 'A', kind: 'general', text: 'נתקשר אליכם לתיאום מועד המסירה.' },
  { id: 'PR20', tier: 'A', kind: 'general', text: 'נציג שלנו יחזור אליכם תוך יום עסקים.' },
  { id: 'PR21', tier: 'A', kind: 'general', text: 'הצוות שלנו יעדכן אתכם כשהמוצר נשלח.' },
  { id: 'PR22', tier: 'A', kind: 'general', text: 'המערכת תודיע לכם ברגע שהתשלום עובר.' },
  { id: 'PR23', tier: 'A', kind: 'general', text: 'נציג ייצור איתכם קשר לפני המשלוח.' },
  { id: 'PR24', tier: 'A', kind: 'general', text: 'נכתוב לכם ברגע שהמוצר חוזר למלאי.' },
  { id: 'PR25', tier: 'A', kind: 'general', text: 'נעביר לכם את מספר המעקב מיד כשנקבל אותו.' },
  { id: 'PR26', tier: 'A', kind: 'general', text: 'נשמור איתכם על קשר עד שהחבילה אצלכם.' },
  { id: 'PR27', tier: 'A', kind: 'general', text: 'הירשמו לקבלת הטבות ומבצעים.' },
  { id: 'PR28', tier: 'A', kind: 'general', text: 'הצטרפו לרשימת הלקוחות שמקבלים מבצעים ראשונים.' },
  { id: 'PR29', tier: 'A', kind: 'general', text: 'המבצע יישלח רק לנרשמים.' },
  { id: 'PR30', tier: 'A', kind: 'general', text: 'ההצעות הבלעדיות שלנו נשלחות פעם בחודש.' },
  { id: 'PR31', tier: 'A', kind: 'general', text: 'הודעה אישית תצא אליכם עם יציאת ההזמנה.' },
  { id: 'PR32', tier: 'A', kind: 'general', text: 'בעוד כמה דקות יחכה לכם מייל עם הקבלה.' },
  { id: 'PR33', tier: 'A', kind: 'general', text: 'תקבלו מאיתנו מכתב תודה עם קוד הנחה.' },
  { id: 'PR34', tier: 'A', kind: 'general', text: 'עד המסירה תקבלו מאיתנו שתי הודעות.' },
  { id: 'PR35', tier: 'A', kind: 'general', text: 'כל שבוע נשלח לכם השראה חדשה לבית.' },
  { id: 'PR36', tier: 'A', kind: 'general', text: 'Tracking details will follow by email.' },
  { id: 'PR37', tier: 'A', kind: 'general', text: 'Order updates by text.' },
  { id: 'PR38', tier: 'A', kind: 'general', text: 'Email confirmation included.' },
  { id: 'PR39', tier: 'A', kind: 'general', text: "We'll reach out once your order ships." },
  { id: 'PR40', tier: 'B', kind: 'general', text: 'סמס יגיע אליכם רגע לפני שהשליח מגיע.' },
  { id: 'PR41', tier: 'B', kind: 'general', text: 'נקפיץ לכם התראה כשהמחיר יורד.' },
  { id: 'PR42', tier: 'B', kind: 'general', text: 'נוודא שתדעו מתי החבילה יוצאת.' },
  { id: 'PR43', tier: 'B', kind: 'general', text: 'קבלו את המבצעים הבאים ישר לנייד.' },
  { id: 'PR44', tier: 'B', kind: 'general', text: 'הצטרפו לקהילה שלנו וקבלו השראה כל שבוע.' },
  { id: 'PR45', tier: 'B', kind: 'general', text: 'שימו עין על הדואר הנכנס שלכם.' },
  { id: 'PR46', tier: 'B', kind: 'general', text: 'השאירו מספר נייד ונסמס לכם כשהמוצר חוזר.' },
  { id: 'PR47', tier: 'B', kind: 'general', text: "You'll hear from us within a day." },
  { id: 'PR48', tier: 'B', kind: 'general', text: "Get a heads-up when it's back." },
  { id: 'PR49', tier: 'B', kind: 'general', text: 'Text alerts for every order.' },
  { id: 'PR50', tier: 'B', kind: 'general', text: 'Check the promotions tab in Gmail.' },
];
const HONEST: P[] = [
  { id: 'HN01', tier: 'A', kind: 'variant', of: 'N26 rule (toYou)', text: 'המנורה נשלחת אליכם מפורקת, עם הוראות הרכבה.' },
  { id: 'HN02', tier: 'A', kind: 'variant', of: 'N26 rule (toYou)', text: 'הספה נשלחת אליכם בשני ארגזים.' },
  { id: 'HN03', tier: 'A', kind: 'variant', of: 'N26 rule (toYou)', text: 'הכריות יישלחו אליכם דחוסות בוואקום.' },
  { id: 'HN04', tier: 'A', kind: 'variant', of: 'S18 "נשלח אליכם"', text: 'את השטיח נשלח אליכם מגולגל ועטוף.' },
  { id: 'HN05', tier: 'A', kind: 'variant', of: 'N16 rule (TRACKING)', text: 'מספר המעקב יופיע כאן ברגע שהחבילה תצא מהמחסן.' },
  { id: 'HN06', tier: 'A', kind: 'variant', of: 'N40 rule (ARRIVE_NOW)', text: 'החשבונית יוצאת אליכם בתוך החבילה.' },
  { id: 'HN07', tier: 'A', kind: 'variant', of: 'N30 rule (לחזור אליכם)', text: 'הכסף אמור לחזור אליכם לכרטיס תוך 14 ימי עסקים.' },
  { id: 'HN08', tier: 'A', kind: 'variant', of: 'X17 rule (FIELD_NAME)', text: 'אימייל (רשות)' },
  { id: 'HN09', tier: 'A', kind: 'variant', of: 'X17 rule (FIELD_NAME)', text: 'אימייל שגוי' },
  { id: 'HN10', tier: 'A', kind: 'variant', of: 'X17 rule (FIELD_NAME)', text: 'אימייל *' },
  { id: 'HN11', tier: 'B', kind: 'variant', of: 'N25 rule (ספאם)', text: 'אנחנו שונאים ספאם בדיוק כמוכם.' },
  { id: 'HN12', tier: 'B', kind: 'variant', of: 'N27 rule (לדעת ראשונים)', text: 'רוצים לדעת ראשונים מה מתאים לחדר? קראו את המדריך שלנו.' },
  { id: 'HN13', tier: 'A', kind: 'variant', of: 'N32 rule (TO_PHONE)', text: 'התאמה מלאה לטלפון: כל פרטי ההזמנה בדף אחד.' },
  { id: 'HN14', tier: 'B', kind: 'variant', of: 'N37 rule (מסר)', text: 'כרית עם מסר רקום ביד, תקבלו אותה ארוזה למתנה.' },
  { id: 'HN15', tier: 'B', kind: 'variant', of: 'K37 rule', text: 'Nothing will be emailed to you.' },
  { id: 'HN16', tier: 'B', kind: 'variant', of: 'K35/K37', text: 'Newsletter: none.' },
  { id: 'HN17', tier: 'A', kind: 'variant', of: 'N24 rule (תשלח)', text: 'את ההודעה תשלח לנו מכתובת המייל שלך.' },
  { id: 'HN18', tier: 'A', kind: 'variant', of: 'N24 rule (תשלח)', text: 'הודעת הביטול תשלח לספק באותו יום.' },
  { id: 'HN19', tier: 'A', kind: 'variant', of: 'K34 rule (heading)', text: 'תזכורת: המבצע נגמר בחצות.' },
  { id: 'HN20', tier: 'A', kind: 'variant', of: 'N15 rule (TRACKING)', text: 'קוד ההנחה: הזינו אותו בקופה.' },
  { id: 'HN21', tier: 'A', kind: 'general', text: 'מיד אחרי התשלום תקבלו אישור על המסך עם מספר ההזמנה.' },
  { id: 'HN22', tier: 'A', kind: 'general', text: 'קישור למעקב יופיע בדף ההזמנה כשהחבילה תצא.' },
  { id: 'HN23', tier: 'A', kind: 'general', text: 'לא צריך מייל כדי לעקוב: הכול מופיע בדף ההזמנה.' },
  { id: 'HN24', tier: 'A', kind: 'general', text: 'תיבת דואר מעוצבת לכניסה, פליז מוברש.' },
  { id: 'HN25', tier: 'A', kind: 'general', text: 'כל הזמנה תשלח מהמחסן של הספק.' },
  { id: 'HN26', tier: 'A', kind: 'general', text: 'פרטי ההזמנה נשמרים בדף ההזמנה.' },
  { id: 'HN27', tier: 'A', kind: 'general', text: 'ההזמנה עוברת לספק מיד אחרי התשלום.' },
  { id: 'HN28', tier: 'A', kind: 'general', text: 'We never send a newsletter.' },
  { id: 'HN29', tier: 'A', kind: 'general', text: 'No newsletter here, just the order page.' },
  { id: 'HN30', tier: 'A', kind: 'general', text: 'Your receipt is on the order page.' },
  { id: 'HN31', tier: 'A', kind: 'general', text: 'Questions? Email us at the address below.' },
  { id: 'HN32', tier: 'A', kind: 'general', text: 'אפשר לשלוח לנו תמונה של המוצר בוואטסאפ.' },
  { id: 'HN33', tier: 'A', kind: 'general', text: 'מספר הטלפון משמש את השליח בלבד.' },
  { id: 'HN34', tier: 'A', kind: 'general', text: 'פרטי המשלוח: שם, כתובת וטלפון.' },
  { id: 'HN35', tier: 'A', kind: 'general', text: 'המייל שלכם נשמר רק לצורך ההזמנה.' },
  { id: 'HN36', tier: 'A', kind: 'general', text: 'כתובת המייל שלכם נשמרת רק לצורך ההזמנה.' },
  { id: 'HN37', tier: 'A', kind: 'general', text: 'השטיח עבר בדיקת איכות לפני שיצא אליכם.' },
  { id: 'HN38', tier: 'A', kind: 'general', text: 'מחיר המשלוח כולל מעקב.' },
  { id: 'HN39', tier: 'A', kind: 'general', text: 'כל העדכונים על ההזמנה מופיעים בדף שלה.' },
  { id: 'HN40', tier: 'A', kind: 'general', text: 'בלי הרשמה ובלי סיסמה: מספר ההזמנה מספיק.' },
  { id: 'HN41', tier: 'A', kind: 'general', text: 'הוראות ההרכבה מצורפות לחבילה.' },
  { id: 'HN42', tier: 'A', kind: 'general', text: 'מנורת הקיר מגיעה עם כבל קצר לשקע.' },
  { id: 'HN43', tier: 'A', kind: 'general', text: 'הפוף יוצא אליכם בלי מילוי.' },
  { id: 'HN44', tier: 'A', kind: 'general', text: 'תוכלו לעקוב אחרי ההזמנה בדף ההזמנה בכל רגע.' },
  { id: 'HN45', tier: 'A', kind: 'general', text: 'הזמנה שלא שולמה לא נשלחת לספק.' },
  { id: 'HN46', tier: 'A', kind: 'general', text: 'השליח מתאם את המסירה ישירות מול הספק.' },
  { id: 'HN47', tier: 'A', kind: 'general', text: 'מספר ההזמנה מופיע גם בקבלה מהסליקה.' },
  { id: 'HN48', tier: 'A', kind: 'general', text: 'שלחו לנו מייל ונענה תוך יומיים.' },
];

// overlap with every list S22 keeps (the fixture and both external lists) and QA S20's list (in the external file)
const lists = [arg('fixture'), ...(arg('external')?.split(',') ?? [])].filter(Boolean) as string[];
const known = new Set<string>();
const walk = (v: unknown): void => {
  if (typeof v === 'string') known.add(lib.normalize(v).trim());
  else if (Array.isArray(v)) v.forEach(walk);
  else if (v && typeof v === 'object') Object.values(v).forEach(walk);
};
for (const f of lists) walk(JSON.parse(readFileSync(f, 'utf8')));
const find = (l: Lib, t: string) => l.promiseFindings(t).map((x) => `${x.rule}:${x.match}`);
const rows = [...PROMISES.map((p) => ({ ...p, kind2: 'promise' as const })), ...HONEST.map((p) => ({ ...p, kind2: 'honest' as const }))].map((p) => {
  const now = find(lib, p.text);
  const before = older ? find(older, p.text) : null;
  return { ...p, findings: now, flagged: now.length > 0, before_flagged: before ? before.length > 0 : null, in_lists: known.has(lib.normalize(p.text).trim()) };
});
for (const r of rows) {
  const tag = r.kind2 === 'promise' ? (r.flagged ? 'caught' : 'MISSED') : r.flagged ? 'FALSE+' : 'ok    ';
  const was = r.before_flagged === null ? '' : ` [before: ${r.before_flagged ? 'flagged' : 'clean'}]`;
  console.log(`${tag}  ${r.id} [${r.tier}/${r.kind}${r.of ? ' ' + r.of : ''}] ${r.text}${r.flagged ? '  ← ' + r.findings.join(', ') : ''}${was}${r.in_lists ? '  (IN A LIST)' : ''}`);
}
const pr = rows.filter((r) => r.kind2 === 'promise');
const hn = rows.filter((r) => r.kind2 === 'honest');
const cnt = (xs: typeof rows, f: (r: (typeof rows)[number]) => boolean) => `${xs.filter(f).length}/${xs.length}`;
const summary = {
  promises: pr.length,
  caught: cnt(pr, (r) => r.flagged),
  caught_tier_a: cnt(pr.filter((r) => r.tier === 'A'), (r) => r.flagged),
  caught_tier_b: cnt(pr.filter((r) => r.tier === 'B'), (r) => r.flagged),
  caught_variants: cnt(pr.filter((r) => r.kind === 'variant'), (r) => r.flagged),
  caught_general: cnt(pr.filter((r) => r.kind === 'general'), (r) => r.flagged),
  missed: pr.filter((r) => !r.flagged).map((r) => r.id),
  honest: hn.length,
  false_positives: hn.filter((r) => r.flagged).map((r) => r.id),
  fp_variants: cnt(hn.filter((r) => r.kind === 'variant'), (r) => r.flagged),
  fp_general: cnt(hn.filter((r) => r.kind === 'general'), (r) => r.flagged),
  ...(older
    ? {
        before_caught: cnt(pr, (r) => !!r.before_flagged),
        before_false_positives: hn.filter((r) => r.before_flagged).map((r) => r.id),
        new_false_positives_in_this_lib: hn.filter((r) => r.flagged && !r.before_flagged).map((r) => r.id),
        new_catches_in_this_lib: pr.filter((r) => r.flagged && !r.before_flagged).map((r) => r.id),
        lost_catches_in_this_lib: pr.filter((r) => !r.flagged && r.before_flagged).map((r) => r.id),
      }
    : {}),
  in_lists: rows.filter((r) => r.in_lists).map((r) => r.id),
  lists_checked: lists,
};
console.log('\n' + JSON.stringify(summary, null, 1));
if (jsonOut) writeFileSync(jsonOut, JSON.stringify({ summary, rows }, null, 1) + '\n');
