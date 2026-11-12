/**
 * S18: no promise of an email without a provider (briefs/site-s18-honest-email-copy-2026-11-12.md).
 * - What a promise is (tools/lib/promises.ts): every line the site said before S18 is caught; the words alone are not.
 * - The copy (site/copy/promises.he.json): no line shown without a provider promises; the email wording comes back
 *   with a provider; a promise put in the wording without a provider stops the copy build.
 * - EMAIL_PROVIDER: UNDECIDED, or a provider that really sends (none yet); never a mock, a typo or nothing.
 * - The build check (tools/check-promises.ts): a promise in a page, in a chunk a page loads, or in the Worker's
 *   customer strings stops the build; the design test page's chunk is not the customer's.
 */
import { describe, expect, it } from 'vitest';
import { spawnSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, relative } from 'node:path';
import { EMAIL_PROVIDERS, emailProviderIssue, emailSends } from '@hd/shared/email';
import { codeStrings, htmlTexts } from '../lib/promise-scan';
import { COPY_FILE, NEEDED, copyIssues, emailTarget, lineOf, loadCopy, promiseFindings, selectCopy, type CopySource } from '../lib/promises';
import { sitePath } from '../lib/paths';

const TSX = sitePath('node_modules/tsx/dist/cli.mjs');
const tmp = (name: string) => mkdtempSync(join(tmpdir(), `hd-s18-${name}-`));
const run = (args: string[], env: Record<string, string> = {}) =>
  spawnSync(process.execPath, [TSX, ...args], { cwd: sitePath(), encoding: 'utf8', timeout: 60_000, env: { ...process.env, HD_PUBLIC: '', ...env } });

/** every email promise the site made before S18 (Checkout.tsx, Order.tsx, Waitlist.tsx, Legal.tsx at a988b099) */
const BEFORE = [
  'אישור וחשבונית מס יישלחו לאימייל. נעדכן כשההזמנה יוצאת למשלוח.',
  'אין לנו גישה להזמנה הזו מהדפדפן הזה. את פרטי ההזמנה שלחנו לאימייל שלכם.',
  'לשם נשלחים אישור ההזמנה והחשבונית.',
  'כולל מע"מ. חשבונית מס נשלחת במייל אחרי התשלום.',
  'אשמח לקבל עדכונים על מוצרים חדשים במייל (רשות, אפשר להסיר בכל עת).',
  'נשלח הודעה אחת כשהמוצר חוזר למלאי. הכתובת לא תשמש לשום דבר אחר.',
  'נרשמתם. נשלח הודעה אחת כשהמוצר חוזר.',
  'עדכנו אותי כשחוזר',
  'עדכנו אותי',
  'דיוור שיווקי נשלח רק אם סימנתם הסכמה, ואפשר להסיר בכל עת.',
  // master-designer's third sentence (§7), never shown so far
  'אם מועד המסירה ישתנה, נעדכן אותך במייל.',
];
/** the words alone, the customer writing to us, the statuses: not promises */
const NEUTRAL = [
  'אימייל',
  'כתובת האימייל לא תקינה.',
  'נא למלא כתובת אימייל תקינה, למשל name@example.com.',
  'אנחנו אוספים רק מה שצריך כדי לספק את ההזמנה: שם, אימייל, טלפון וכתובת למשלוח.',
  'להודעת ביטול: באימייל או בטלפון של שירות הלקוחות (יושלמו לפני ההשקה). יש לציין את מספר ההזמנה.',
  'שם, טלפון ואימייל יושלמו לפני ההשקה. נשמח לשמוע על כל קושי ונחזור תוך 5 ימי עסקים.',
  'ההזמנה בדרך אליכם. מספר המשלוח למעלה.',
  'בקשת הביטול נשלחה לספק. ההזמנה תבוטל ותזוכה כשהספק יאשר.',
  'ההזמנה כבר נשלחה. אי אפשר לבטל; אפשר להחזיר כסף (מלא או חלקי) אחרי שהפריט חוזר.',
  'התקבלה · בהכנה · נשלחה · נמסרה',
  'ההחזר הכספי יבוצע תוך 14 יום מקבלת הודעת הביטול, באמצעי התשלום שבו שולם.',
  'מי שביקש להפחית תנועה במכשיר מקבל מעברים מיידיים, בלי זום ובלי סרטוני מעבר.',
  'האתר לא שולח דיוור שיווקי.',
  'עוד ₪50 בסל, והמשלוח החסכוני חינם.',
];

describe('S18: what a promise is', () => {
  it('every promise the site made before S18 is caught, by its rule', () => {
    for (const t of BEFORE) expect(promiseFindings(t), t).not.toEqual([]);
    expect(promiseFindings(BEFORE[0]!).map((f) => `${f.rule}:${f.match}`)).toEqual(['send:יישלחו', 'notify:נעדכן']);
    expect(promiseFindings(BEFORE[4]!).map((f) => f.rule)).toEqual(['receive']);
    expect(promiseFindings('עדכנו אותי כשחוזר').map((f) => f.rule)).toEqual(['notify']);
  });
  it('the words alone, the customer writing to us and the statuses are not promises', () => {
    for (const t of NEUTRAL) expect(promiseFindings(t), t).toEqual([]);
  });
  it('a negated verb is not a promise; the same verb affirmed is', () => {
    expect(promiseFindings('לא נשלח לכם מייל.')).toEqual([]);
    expect(promiseFindings('נשלח לכם מייל.')).toHaveLength(1);
    expect(promiseFindings('האתר שולח דיוור שיווקי.')).toHaveLength(1);
  });
  it('an SMS, a message app and a promise in English are promises too', () => {
    expect(promiseFindings('נשלח SMS כשהשליח בדרך.')).toHaveLength(1);
    expect(promiseFindings('תקבלו הודעת ווטסאפ עם מספר המשלוח.')).toHaveLength(1);
    expect(promiseFindings('נודיע לכם כשהמוצר חוזר.')).toHaveLength(1);
    expect(promiseFindings("We'll email you when it ships.")).toHaveLength(1);
  });
  it('per sentence: a verb and an object in two sentences are not one promise', () => {
    expect(promiseFindings('ההזמנה נשלחה. האישור בדף הזה.')).toEqual([]);
    expect(promiseFindings('ההזמנה נשלחה · אישור')).toEqual([]);
  });
});

describe('S18: the copy (site/copy/promises.he.json)', () => {
  const src = loadCopy();
  it('is well formed, and no line shown without a provider promises', () => {
    expect(copyIssues(src)).toEqual([]);
    for (const [key, e] of Object.entries(src.strings)) {
      const line = lineOf(e, 'no_email');
      if (line) expect(promiseFindings(line), key).toEqual([]);
    }
    for (const line of Object.values(selectCopy(src, false))) if (line) expect(promiseFindings(line), line).toEqual([]);
  });
  it('with a provider, the email lines come back (the wording of the site before S18, and §7)', () => {
    const lines = Object.values(selectCopy(src, true));
    for (const t of BEFORE) expect(lines, t).toContain(t);
  });
  it('without a provider: no marketing box, no waiting-list form, no §7 third sentence; the pages keep their lines', () => {
    const lines = selectCopy(src, false);
    for (const k of ['checkout.marketing_consent', 'order.delay.followup', 'waitlist.offer', 'waitlist.why', 'waitlist.submit', 'waitlist.done'])
      expect(lines[k], k).toBeNull();
    for (const k of NEEDED) expect(typeof lines[k], k).toBe('string');
    expect(lines['order.next.received']).toMatch(/בדף הזה/);
    expect(lines['checkout.total_note']).toBe('כולל מע"מ.');
  });
  const mutate = (f: (s: CopySource) => void): string[] => {
    const s = JSON.parse(JSON.stringify(src)) as CopySource;
    f(s);
    return copyIssues(s);
  };
  it('a promise in the wording without a provider, a group shown in part, a needed line hidden, a missing wording: refused', () => {
    expect(mutate((s) => ((s.strings['order.next.received'] as { no_email: string }).no_email = BEFORE[0]!))).toEqual([
      expect.stringContaining('order.next.received: the line shown without an email provider promises (send: "יישלחו")'),
      expect.stringContaining('order.next.received: the line shown without an email provider promises (notify: "נעדכן")'),
    ]);
    expect(mutate((s) => (s.strings['order.next.shipped'] = { where: 'x', text: 'נעדכן כשההזמנה יוצאת.' }))).toHaveLength(1);
    expect(mutate((s) => ((s.strings['waitlist.why'] as { no_email: string | null }).no_email = 'הכתובת לא תשמש לשום דבר אחר.'))).toEqual([
      'group waitlist: in "no_email" its lines are shown or hidden together (some are null, some are not)',
    ]);
    expect(mutate((s) => ((s.strings['order.no_access'] as { no_email: string | null }).no_email = null))).toEqual([
      'order.no_access: a page needs this line in "no_email" (null is not allowed)',
    ]);
    expect(mutate((s) => delete (s.strings['checkout.email_hint'] as { email?: unknown }).email)).toEqual([
      expect.stringContaining('checkout.email_hint: "email" is missing'),
    ]);
  });
});

describe('S18: EMAIL_PROVIDER', () => {
  it('none is built: UNDECIDED never sends; a mock, a typo or nothing is refused, and never sends', () => {
    expect(EMAIL_PROVIDERS).toEqual([]);
    expect(emailProviderIssue('UNDECIDED')).toBeNull();
    expect(emailSends('UNDECIDED')).toBe(false);
    for (const v of ['mock', 'Mock', 'resend', 'UNDECIDED ', '', undefined, null, 1]) {
      expect(emailProviderIssue(v), String(v)).not.toBeNull();
      expect(emailSends(v), String(v)).toBe(false);
    }
    expect(emailProviderIssue('mock')).toMatch(/no mock/);
  });
  it('wrangler.jsonc: UNDECIDED in every environment; the public build reads production, the others the top level', () => {
    expect(emailTarget({ publicBuild: false })).toEqual({ env: 'top level', value: 'UNDECIDED', issue: null, sends: false });
    expect(emailTarget({ publicBuild: true })).toEqual({ env: 'production', value: 'UNDECIDED', issue: null, sends: false });
    const wrangler = readFileSync(sitePath('api/wrangler.jsonc'), 'utf8');
    expect(wrangler.match(/"EMAIL_PROVIDER": "UNDECIDED"/g)).toHaveLength(3);
  });
});

describe('S18: the copy build (tools/build-copy.ts)', () => {
  const dir = tmp('copy');
  const out = join(dir, 'copy.he.json');
  const wranglerWith = (top: string, prod: string) => {
    const f = join(dir, `wrangler-${top}-${prod}.jsonc`);
    writeFileSync(f, `{ // test\n "vars": { "EMAIL_PROVIDER": "${top}" },\n "env": { "production": { "vars": { "EMAIL_PROVIDER": "${prod}", }, }, },\n}`);
    return f;
  };
  it('UNDECIDED: writes the wording without an email, and only it', () => {
    const r = run(['tools/build-copy.ts', `--out=${out}`]);
    expect(r.status, r.stderr).toBe(0);
    expect(r.stdout).toMatch(/EMAIL_PROVIDER=UNDECIDED \(top level\) → the wording without an email/);
    const built = JSON.parse(readFileSync(out, 'utf8')) as { sends: boolean; strings: Record<string, string | null> };
    expect(built.sends).toBe(false);
    expect(built.strings).toEqual(selectCopy(loadCopy(), false));
    for (const t of BEFORE) expect(JSON.stringify(built), t).not.toContain(t);
  });
  it('a promise in the wording without a provider stops it', () => {
    const src = JSON.parse(readFileSync(COPY_FILE, 'utf8')) as CopySource;
    (src.strings['checkout.total_note'] as { no_email: string }).no_email = BEFORE[3]!;
    const f = join(dir, 'promising.json');
    writeFileSync(f, JSON.stringify(src));
    const r = run(['tools/build-copy.ts', `--copy=${f}`, `--out=${join(dir, 'never.json')}`]);
    expect(r.status).toBe(1);
    expect(r.stderr).toContain('checkout.total_note: the line shown without an email provider promises (send: "נשלחת")');
  });
  it('a mock, a typo or no EMAIL_PROVIDER stops it; the public build reads production', () => {
    for (const v of ['mock', 'resend', ''])
      expect(run(['tools/build-copy.ts', `--wrangler=${wranglerWith(v, 'UNDECIDED')}`, `--out=${out}`]).status, v).toBe(1);
    const f = wranglerWith('UNDECIDED', 'mock');
    expect(run(['tools/build-copy.ts', `--wrangler=${f}`, `--out=${out}`]).status).toBe(0);
    const pub = run(['tools/build-copy.ts', `--wrangler=${f}`, `--out=${out}`], { HD_PUBLIC: '1' });
    expect(pub.status).toBe(1);
    expect(pub.stderr).toContain('production: EMAIL_PROVIDER=mock is refused');
  });
});

describe('S18: the build check (tools/check-promises.ts)', () => {
  /** a small site: a page, its entry, a lazy page chunk, and the design test page with its own chunk */
  function site(o: { orderLine?: string; pageText?: string; testLine?: string } = {}): string {
    const d = tmp('dist');
    mkdirSync(join(d, 'assets'));
    mkdirSync(join(d, 'test'));
    mkdirSync(join(d, 'privacy'));
    writeFileSync(
      join(d, 'index.html'),
      '<!doctype html><html lang="he"><head><script type="module" src="/assets/main-a1.js"></script></head><body><p>הבית</p></body></html>',
    );
    writeFileSync(
      join(d, 'privacy/index.html'),
      `<html><body><ul><li>${o.pageText ?? 'האתר לא שולח דיוור שיווקי.'}</li></ul><script type="module" src="/assets/main-a1.js"></script></body></html>`,
    );
    writeFileSync(join(d, 'assets/main-a1.js'), 'const e=()=>import("./Order-b2.js");export{e};');
    writeFileSync(join(d, 'assets/Order-b2.js'), `export const t=${JSON.stringify(o.orderLine ?? 'אישור ההזמנה ומצבה מופיעים בדף הזה.')},n=\`מספר \${1}\`;`);
    writeFileSync(join(d, 'test/index.html'), '<html><body><script type="module" src="/assets/test-c3.js"></script></body></html>');
    writeFileSync(join(d, 'assets/test-c3.js'), `export const x=${JSON.stringify(o.testLine ?? 'עדכנו אותי כשחוזר')};`);
    return d;
  }
  const check = (dist: string, extra: string[] = []) => {
    const json = join(dist, '..', `${relative(tmpdir(), dist).replace(/\W/g, '')}.json`);
    const r = run(['tools/check-promises.ts', `--dist=${dist}`, `--json=${json}`, ...extra]);
    return {
      ...r,
      report: JSON.parse(readFileSync(json, 'utf8')) as { findings: { file: string; rule: string }[]; skipped_chunks: string[]; problems: string[] },
    };
  };

  it('a clean site passes; the test page chunk is not the customer’s (listed, not scanned)', () => {
    const r = check(site());
    expect(r.status, r.stderr).toBe(0);
    expect(r.report.findings).toEqual([]);
    expect(r.report.skipped_chunks).toEqual(['assets/test-c3.js']);
  });
  it('the order page’s old line in a lazy chunk stops the build', () => {
    const r = check(site({ orderLine: BEFORE[0] }));
    expect(r.status).toBe(1);
    expect(r.report.findings.map((f) => `${f.file} ${f.rule}`)).toEqual(['assets/Order-b2.js send', 'assets/Order-b2.js notify']);
  });
  it('a promise in a page’s text stops the build', () => {
    const r = check(site({ pageText: 'נרשמתם. <strong>נשלח</strong> הודעה אחת כשהמוצר חוזר.' }));
    expect(r.status).toBe(1);
    expect(r.report.findings).toEqual([expect.objectContaining({ file: 'privacy/index.html', rule: 'send' })]);
  });
  it('a promise in the Worker’s customer strings stops the build; the owner’s screens are not the customer’s', () => {
    const api = tmp('api');
    mkdirSync(join(api, 'routes'));
    mkdirSync(join(api, 'lib'));
    writeFileSync(join(api, 'routes/public.ts'), "export const m = { message_he: 'ההזמנה התקבלה. נשלח אליכם אישור במייל.' };");
    writeFileSync(join(api, 'routes/admin-ui.ts'), "export const a = 'נעדכן את הבעלים במייל';");
    const r = check(site(), [`--api=${api}`]);
    expect(r.status).toBe(1);
    expect(r.report.findings.map((f) => f.file)).toEqual(['api/src/routes/public.ts']);
  });
  it('a copy built for another EMAIL_PROVIDER fails: the build’s choice must be this build’s', () => {
    const d = site();
    const f = join(d, '..', 'copy-other.json');
    writeFileSync(f, JSON.stringify({ email_provider: 'resend', sends: true, strings: {} }));
    const r = check(d, [`--copy-out=${f}`]);
    expect(r.status).toBe(1);
    expect(r.report.problems).toEqual([expect.stringContaining('was built for EMAIL_PROVIDER=resend, this build is for UNDECIDED')]);
  });
  it('reads what a person reads in HTML (text, labels, JSON-LD), and every string in code', () => {
    expect(htmlTexts('<a aria-label="נעדכן אתכם">x</a><script type="application/ld+json">{"d":"נודיע לכם"}</script><p>מע&quot;מ</p>')).toEqual([
      'נודיע לכם',
      'נעדכן אתכם',
      'x',
      'מע"מ',
    ]);
    expect(codeStrings('const a="א",b=`ב${c}ג`;/"/.test(d);', 'x.js')).toEqual(['א', 'ב', 'ג']);
  });
});

describe('S18: the web’s own strings', () => {
  it('no promise is written in the web’s code (the copy is the one place for these lines); the design test page aside', () => {
    const found: string[] = [];
    const walk = (d: string): void => {
      for (const n of readdirSync(d)) {
        const p = join(d, n);
        if (statSync(p).isDirectory()) {
          if (n !== 'test-page') walk(p);
        } else if (/\.tsx?$/.test(n))
          for (const s of codeStrings(readFileSync(p, 'utf8'), p))
            for (const f of promiseFindings(s)) found.push(`${relative(sitePath(), p)}: "${f.sentence}"`);
      }
    };
    walk(sitePath('web/src'));
    walk(sitePath('shared/src'));
    expect(found).toEqual([]);
  });
});
