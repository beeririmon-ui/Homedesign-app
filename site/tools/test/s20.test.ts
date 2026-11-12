/**
 * S20 (QA S18): the promise gate, wider and without its blind spots; the story's line; capabilities; the contact config.
 * - ת58: QA's 48 promising lines (16 of the forms the task named) are caught: tools/test/fixtures/promise-phrases.json.
 * - ת59: QA's 26 honest lines, and the site's own honest sentences, pass.
 * - ת60: a promise split across a span, JSX, a template or "+", in value / single-quoted / aria-roledescription
 *   attributes, a JSON island, a JSON file, CSS, a script outside assets/ or under a CDN URL, a .json in api/src, or in
 *   shared/src served by the Worker: each one stops the build (QA's mutations Q1, Q7–Q10, Q12, Q14–Q20, Q26, Q27).
 * - ת56: the story's "אפשר לבקש עדכון" is a copy line in the waiting-list group, not shown without a provider.
 * - ת62: each email line comes back only with all it needs, and an email line may not promise more than its needs.
 * - ת61: the contact block's config: the public build stops without it; behind the flag it is a warning.
 */
import { describe, expect, it } from 'vitest';
import { spawnSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, relative } from 'node:path';
import { EMAIL_CAPABILITIES, canEmail, emailCapabilities, emailSends, type EmailCapability, type EmailProviders } from '@hd/shared/email';
import { codeStrings, cssStrings, htmlTexts, workerSources } from '../lib/promise-scan';
import {
  ALL_EMAIL,
  NO_EMAIL,
  STATES,
  allowedPromises,
  copyIssues,
  impliedCapabilities,
  lineOf,
  loadCopy,
  needsMet,
  normalize,
  promiseFindings,
  selectCopy,
  type CopySource,
} from '../lib/promises';
import { sitePath } from '../lib/paths';

const TSX = sitePath('node_modules/tsx/dist/cli.mjs');
const tmp = (name: string) => mkdtempSync(join(tmpdir(), `hd-s20-${name}-`));
const run = (args: string[], env: Record<string, string> = {}) =>
  spawnSync(process.execPath, [TSX, ...args], {
    cwd: sitePath(),
    encoding: 'utf8',
    timeout: 90_000,
    env: { ...process.env, HD_PUBLIC: '', HD_WRANGLER: '', ...env },
  });
const phrases = JSON.parse(readFileSync(sitePath('tools/test/fixtures/promise-phrases.json'), 'utf8')) as {
  promises: { id: string; tier: 'A' | 'B'; text: string }[];
  honest: { id: string; text: string }[];
  site_honest: string[];
};

describe('S20 ת58: what a promise is, wider', () => {
  it("QA's 48 promising lines are all caught, the 16 forms the task named among them", () => {
    const missed = phrases.promises.filter((p) => !promiseFindings(p.text).length).map((p) => `${p.id} ${p.text}`);
    expect(missed).toEqual([]);
    expect(phrases.promises.filter((p) => p.tier === 'A')).toHaveLength(16);
  });
  it('the forms the brief names', () => {
    for (const t of [
      'כשהמוצר יחזור, נשלח אליכם.',
      'את האישור תמצאו בתיבת הדואר שלכם.',
      'עדכוני משלוח ב-SMS.',
      'מעקב משלוח בוואטסאפ.',
      'We’ll email you when it ships.',
      "You'll be notified when it's back in stock.",
      'כולל מע"מ. תקבלו חשבונית מס.',
      'אישור ההזמנה ומצבה מופיעים בדף הזה. המייל עם האישור כבר בדרך.',
      'בדף המוצר אפשר לבקש עדכון כשהוא חוזר.',
      'ניצור איתכם קשר בוואטסאפ.',
      'נחזור אליכם תוך יום.',
      'נזכיר לכם לפני שהמבצע נגמר.',
      'הירשמו לעדכונים.',
    ])
      expect(promiseFindings(t), t).not.toEqual([]);
  });
  it('typographic marks, niqqud and invisible characters do not hide a promise', () => {
    expect(normalize('We’ll ־ “x” \u200Fא\u00A0ב')).toBe(`We'll - "x" א ב`);
    for (const t of ['נ\u200Bעדכן אתכם', 'נְעַדְכֵּן אתכם', 'תקבלו אישור באי־מייל', 'נשלח לכם אישור בדוא״ל']) expect(promiseFindings(t), t).not.toEqual([]);
  });
  it('a negation one word before, across a comma, does not cancel a promise (P27); right before the verb it does', () => {
    expect(promiseFindings('בלי לחכות, נשלח לכם אישור במייל.')).not.toEqual([]);
    expect(promiseFindings('אם לא תשלמו תוך שעה, נשלח לכם תזכורת במייל.')).not.toEqual([]);
    expect(promiseFindings('לא נשלח לכם אישור במייל.')).toEqual([]);
  });
});

describe('S20 ת59: honest lines pass', () => {
  it("QA's 26 honest lines", () => {
    expect(phrases.honest.filter((h) => promiseFindings(h.text).length).map((h) => `${h.id} ${h.text}`)).toEqual([]);
  });
  it('the false positives of S18 (Q31–Q35), and "עדכנו אותנו" is out of the list', () => {
    for (const t of [
      'הודעת ביטול שנשלחת אלינו באימייל תטופל תוך 3 ימי עסקים.',
      'נעדכן את המדיניות מעת לעת, והנוסח המעודכן יופיע בדף הזה.',
      'שיניתם כתובת? עדכנו אותנו לפני המשלוח.',
      'קישור למעקב יופיע כאן כשהספק ישלח את החבילה.',
      'אנחנו מקבלים פניות במייל ובטלפון.',
    ])
      expect(promiseFindings(t), t).toEqual([]);
  });
  it("the site's own honest sentences that name a channel or a verb (QA's net scan of the flag build)", () => {
    expect(phrases.site_honest.length).toBeGreaterThan(50);
    expect(phrases.site_honest.filter((s) => promiseFindings(s).length)).toEqual([]);
  });
  it('a field, the customer writing to us, a status: not promises', () => {
    for (const t of [
      'אימייל',
      'כתובת האימייל לא תקינה.',
      'אנחנו אוספים רק מה שצריך כדי לספק את ההזמנה: שם, אימייל, טלפון וכתובת למשלוח.',
      'שם, טלפון ואימייל של רכז/ת הנגישות יושלמו לפני ההשקה.',
      'להודעת ביטול: פנו אלינו באחת הדרכים שלמטה, וציינו את מספר ההזמנה.',
      'ההזמנה נשלחה אליכם בשליחות עד הבית.',
      'בקשת הביטול נשלחה לספק.',
      'ההודעה שלכם נשלחה.',
    ])
      expect(promiseFindings(t), t).toEqual([]);
  });
});

/** a small site: the pages, their entry, a lazy chunk, and the design review page with its own chunk */
function site(): string {
  const d = tmp('dist');
  for (const dir of ['assets', 'test', 'privacy', 'p/x', 'story/living-room/nordic']) mkdirSync(join(d, dir), { recursive: true });
  writeFileSync(
    join(d, 'index.html'),
    '<!doctype html><html lang="he"><head><script type="module" src="/assets/main-a1.js"></script></head><body><p>הבית</p></body></html>',
  );
  writeFileSync(
    join(d, 'privacy/index.html'),
    '<html><body><ul><li>האתר לא שולח דיוור שיווקי.</li></ul><script type="module" src="/assets/main-a1.js"></script></body></html>',
  );
  writeFileSync(join(d, 'p/x/index.html'), '<html><body><div class="waitlist"><p class="waitlist-status">המלאי אינו זמין כעת</p></div></body></html>');
  writeFileSync(
    join(d, 'story/living-room/nordic/index.html'),
    '<html><body><script type="application/json" id="st-data">{"items":{"a":{"status":"unavailable","detail_he":"ספה בכיסוי בהיר."}}}</script></body></html>',
  );
  writeFileSync(join(d, 'assets/main-a1.js'), 'const e=()=>import("./Order-b2.js");export{e};');
  writeFileSync(join(d, 'assets/Order-b2.js'), 'export const t="אישור ההזמנה ומצבה מופיעים בדף הזה.";');
  writeFileSync(join(d, 'assets/main-a1.css'), '.x::after{content:"·"}');
  writeFileSync(join(d, 'test/index.html'), '<html><body><script type="module" src="/assets/test-c3.js"></script></body></html>');
  writeFileSync(join(d, 'assets/test-c3.js'), 'export const x="עדכנו אותי כשחוזר";');
  return d;
}
const edit = (f: string, a: string, b: string) => {
  const s = readFileSync(f, 'utf8');
  if (!s.includes(a)) throw new Error(`${a} is not in ${f}`);
  writeFileSync(f, s.replace(a, b));
};
const check = (dist: string, extra: string[] = []) => {
  const json = join(dist, '..', `${relative(tmpdir(), dist).replace(/\W/g, '')}.json`);
  const r = run(['tools/check-promises.ts', `--dist=${dist}`, `--json=${json}`, '--worker-bundle=none', ...extra]);
  return {
    ...r,
    report: JSON.parse(readFileSync(json, 'utf8')) as {
      findings: { file: string; rule: string }[];
      scripts_review_only: string[];
      scripts_unreferenced: string[];
    },
  };
};

describe('S20 ת60: the scanner’s blind spots (QA S18 mutations)', () => {
  const P = 'privacy/index.html';
  const PRIV = 'האתר לא שולח דיוור שיווקי.';
  const PROD = 'p/x/index.html';
  const mutations: [string, (d: string) => void][] = [
    ['Q1 a verb in a <span>', (d) => edit(join(d, P), PRIV, 'חשבונית מס <span>נשלחת</span> במייל אחרי התשלום.')],
    [
      'Q7 a submit input’s value',
      (d) => edit(join(d, PROD), 'המלאי אינו זמין כעת</p>', 'המלאי אינו זמין כעת</p><input type="submit" value="עדכנו אותי כשחוזר">'),
    ],
    ['Q8 aria-label in single quotes', (d) => edit(join(d, PROD), 'class="waitlist-status"', 'class="waitlist-status" aria-label=\'נעדכן אתכם במייל כשחוזר\'')],
    ['Q9 aria-roledescription', (d) => edit(join(d, PROD), 'class="waitlist-status"', 'class="waitlist-status" aria-roledescription="נעדכן אתכם כשחוזר"')],
    [
      'Q10 a JSON island (the story data)',
      (d) => edit(join(d, 'story/living-room/nordic/index.html'), '"detail_he":"', '"detail_he":"נשלח לכם הודעה כשהמוצר חוזר. '),
    ],
    [
      'Q12 a JSON file in dist',
      (d) => {
        mkdirSync(join(d, 'data'));
        writeFileSync(join(d, 'data/notice.json'), '{"notice_he":"נשלח לכם הודעה כשהמוצר חוזר למלאי."}');
      },
    ],
    [
      'Q14 JSX split across <b>',
      (d) => writeFileSync(join(d, 'assets/Order-b2.js'), 'export const t=(u)=>u("p",{children:["אישור ",u("b",{children:"יישלח"})," לאימייל שלכם."]});'),
    ],
    ['Q15 a template literal split by ${}', (d) => writeFileSync(join(d, 'assets/Order-b2.js'), 'export const t=(n)=>`האישור על ${n} פריטים יישלח אליכם`;')],
    ['Q16 "a" + "b"', (d) => writeFileSync(join(d, 'assets/Order-b2.js'), 'export const t="אישור ההזמנה "+"יישלח בקרוב.";')],
    [
      'Q17 a script outside assets/',
      (d) => {
        writeFileSync(join(d, 'notice.js'), 'document.body.insertAdjacentText("beforeend","נשלח לכם אישור במייל.");');
        edit(join(d, P), '</body>', '<script src="/notice.js"></script></body>');
      },
    ],
    [
      'Q18 a chunk named by a CDN URL',
      (d) => {
        writeFileSync(join(d, 'assets/Waitlist-d4.js'), 'export const w="נשלח לכם הודעה אחת כשהמוצר חוזר.";');
        writeFileSync(join(d, 'assets/main-a1.js'), 'const e=()=>import("https://cdn.example/assets/Waitlist-d4.js");export{e};');
      },
    ],
    ['Q19 CSS content', (d) => writeFileSync(join(d, 'assets/main-a1.css'), '.waitlist-status::after{content:" נעדכן אתכם במייל כשחוזר"}')],
    ['Q20 a typographic apostrophe', (d) => edit(join(d, P), PRIV, 'We’ll email you when your order ships.')],
    ['Q21 a mailbox', (d) => edit(join(d, P), PRIV, 'את האישור תמצאו בתיבת הדואר שלכם.')],
    ['Q22 SMS and WhatsApp with no verb', (d) => edit(join(d, P), PRIV, 'עדכוני משלוח ב-SMS ובוואטסאפ.')],
    ['an inline script', (d) => edit(join(d, P), '</body>', '<script>window.x="נשלח לכם אישור במייל."</script></body>')],
    ['an unreferenced script, scanned all the same', (d) => writeFileSync(join(d, 'assets/orphan-e5.js'), 'export const o="תקבלו חשבונית מס.";')],
  ];
  it('the clean small site passes; the review page’s chunk alone is not scanned', () => {
    const r = check(site(), ['--api=none']);
    expect(r.status, r.stderr).toBe(0);
    expect(r.report.scripts_review_only).toEqual(['assets/test-c3.js']);
  });
  for (const [name, mutate] of mutations)
    it(`${name}: the build stops`, () => {
      const d = site();
      mutate(d);
      const r = check(d, ['--api=none']);
      expect(r.status, `${name}\n${r.stdout}`).toBe(1);
      expect(r.report.findings.length, name).toBeGreaterThan(0);
    });
  it('Q26 a .json of messages in api/src, Q27 shared/src served by the Worker: the build stops', () => {
    const api = tmp('api');
    mkdirSync(join(api, 'lib'));
    writeFileSync(join(api, 'lib/messages.json'), '{"order_he":"נשלח לכם אישור במייל."}');
    expect(check(site(), [`--api=${api}`]).report.findings.map((f) => f.file)).toEqual(['api/src/lib/messages.json']);
    // the real Worker reads ORDER_STATUS_HE from shared/src: it is among the files scanned
    const files = workerSources(sitePath('api/src'), sitePath('shared/src')).map((f) => relative(sitePath(), f).split('\\').join('/'));
    expect(files).toContain('shared/src/constants.ts');
    expect(files).toContain('shared/src/email.ts');
    expect(files).not.toContain('api/src/routes/admin-ui.ts');
  });
  it('reads joined text in code and HTML, every attribute, CSS strings', () => {
    expect(codeStrings('u("p",{children:["אישור ",u("b",{children:"יישלח"})," לאימייל."]})', 'x.js')).toContain('אישור יישלח לאימייל.');
    expect(codeStrings('const t=`א ${n} ב`;', 'x.js')).toContain('א  ב');
    expect(codeStrings('const t="א"+"ב"+"ג";', 'x.js')).toContain('אבג');
    expect(codeStrings('const T=<p>אישור <b>יישלח</b> במייל</p>;', 'x.tsx')).toContain('אישור יישלח במייל');
    expect(htmlTexts('<p>חשבונית <span>נשלחת</span> במייל</p>')).toContain('חשבונית נשלחת במייל');
    expect(htmlTexts('<i data-x=\'א\' value=ב aria-roledescription="ג"></i>')).toEqual(expect.arrayContaining(['א', 'ב', 'ג']));
    expect(cssStrings('.a::after{content:"\\5D0 ב"}')).toEqual(['אב']);
  });
});

describe('S20 ת56: the story’s line', () => {
  const src = loadCopy();
  it('is a copy line of the waiting-list group, shown only with a provider that sends the back-in-stock message', () => {
    const e = src.strings['story.unavailable_note'] as { group: string; needs: string[]; no_email: null; email: string };
    expect(e).toMatchObject({ group: 'waitlist', needs: ['back_in_stock'], no_email: null, email: 'בדף המוצר אפשר לבקש עדכון כשהוא חוזר.' });
    expect(lineOf(e as never, NO_EMAIL)).toBeNull();
    expect(lineOf(e as never, { capabilities: ['back_in_stock'], contact: false })).toBe(e.email);
  });
  it('the story’s code no longer writes it; the gate catches the old line in a story chunk', () => {
    const story = readFileSync(sitePath('web/src/story/story.ts'), 'utf8');
    expect(codeStrings(story, 'story.ts').filter((s) => s.includes('לבקש עדכון'))).toEqual([]);
    expect(story).toContain("copyHe('story.unavailable_note')");
    const d = site();
    writeFileSync(join(d, 'assets/story-f6.js'), 'export const w=`המלאי אינו זמין כעת.${h?" בדף המוצר אפשר לבקש עדכון כשהוא חוזר.":""}`;');
    edit(join(d, 'story/living-room/nordic/index.html'), '<body>', '<body><script type="module" src="/assets/story-f6.js"></script>');
    expect(check(d, ['--api=none']).report.findings).toEqual([expect.objectContaining({ file: 'assets/story-f6.js', rule: 'notify' })]);
  });
});

describe('S20 ת62: capabilities, not one switch', () => {
  const src = loadCopy();
  const TEST: EmailProviders = { all: [...EMAIL_CAPABILITIES], confirm: ['order_confirmation'] };
  it('a provider declares what its adapter sends; none is built', () => {
    expect(emailCapabilities('UNDECIDED')).toEqual([]);
    expect(emailCapabilities('confirm', TEST)).toEqual(['order_confirmation']);
    expect(canEmail('confirm', 'shipping_update', TEST)).toBe(false);
    expect(emailSends('confirm', TEST)).toBe(true);
    expect(emailCapabilities('toString', TEST)).toEqual([]);
  });
  const emailEntries = Object.entries(src.strings).filter(([, e]) => 'email' in e) as [
    string,
    { needs: EmailCapability[] | 'any'; email: string | null; no_email: string | null },
  ][];
  for (const [key, e] of emailEntries)
    it(`${key}: its email line only with all it needs (${Array.isArray(e.needs) ? e.needs.join(', ') : e.needs})`, () => {
      expect(lineOf(e as never, ALL_EMAIL)).toBe(e.email);
      expect(lineOf(e as never, NO_EMAIL)).toBe(e.no_email);
      if (e.needs === 'any') {
        for (const c of EMAIL_CAPABILITIES) expect(lineOf(e as never, { capabilities: [c], contact: false })).toBe(e.email);
        return;
      }
      expect(lineOf(e as never, { capabilities: e.needs, contact: false })).toBe(e.email);
      for (const missing of e.needs) {
        const caps = EMAIL_CAPABILITIES.filter((c) => c !== missing);
        expect(lineOf(e as never, { capabilities: caps, contact: false }), `${key} without ${missing}`).toBe(e.no_email);
      }
      // and what it says needs no more than it lists
      if (e.email) for (const c of impliedCapabilities(e.email)) expect(e.needs, `${key} promises ${c}`).toContain(c);
    });
  it('a provider that sends only the order confirmation brings back only the lines that need only that', () => {
    const lines = selectCopy(src, { capabilities: ['order_confirmation'], contact: false });
    const back = Object.keys(lines).filter((k) => 'email' in src.strings[k]! && lines[k] === (src.strings[k] as { email: string }).email && lines[k] !== null);
    // and the privacy line that names the email service: any email sent means it processes the address
    expect(back).toEqual(['order.no_access', 'privacy.processors']);
    expect([...allowedPromises(src, ['order_confirmation'])]).toEqual([
      'את פרטי ההזמנה שלחנו לאימייל שלכם',
      'הפרטים מועברים רק למי שצריך אותם לביצוע ההזמנה: הספק ושירות המשלוחים, חברת הסליקה, שירות החשבוניות ושירות המיילים',
    ]);
    expect(allowedPromises(src, [])).toEqual(new Set());
  });
  it('an email line that promises more than its needs, or no needs at all, is refused', () => {
    const mutate = (f: (s: CopySource) => void) => {
      const s = JSON.parse(JSON.stringify(src)) as CopySource;
      f(s);
      return copyIssues(s);
    };
    expect(
      mutate((s) => ((s.strings['order.no_access'] as { email: string }).email = 'את פרטי ההזמנה שלחנו לאימייל שלכם, ונעדכן כשההזמנה יוצאת למשלוח.')),
    ).toEqual([expect.stringContaining('order.no_access: the email line promises shipping_update')]);
    expect(mutate((s) => delete (s.strings['order.no_access'] as { needs?: unknown }).needs)).toEqual([expect.stringContaining('order.no_access: "needs"')]);
    expect(mutate((s) => ((s.strings['order.no_access'] as { needs: unknown }).needs = ['carrier_pigeon']))).toEqual([expect.stringContaining('"needs"')]);
    expect(needsMet('any', [])).toBe(false);
    expect(needsMet([], [...EMAIL_CAPABILITIES])).toBe(false);
  });
  it('the waiting-list group, the story line with it, is shown or hidden together in every state', () => {
    const keys = Object.keys(src.strings).filter((k) => src.strings[k]!.group === 'waitlist');
    expect(keys).toEqual(['waitlist.offer', 'waitlist.why', 'waitlist.submit', 'waitlist.done', 'story.unavailable_note']);
    for (const st of STATES) expect(new Set(keys.map((k) => lineOf(src.strings[k]!, st) === null)).size).toBe(1);
  });
});

describe('S20 ת61: the contact block’s config', () => {
  const dir = tmp('contact');
  const out = join(dir, 'copy.he.json');
  const wrangler = (email: string, phone = 'UNDECIDED') => {
    const f = join(dir, `w-${Math.random().toString(36).slice(2)}.jsonc`);
    const v = `"EMAIL_PROVIDER": "UNDECIDED", "CONTACT_EMAIL": "${email}", "CONTACT_PHONE": "${phone}"`;
    writeFileSync(f, `{ "vars": { ${v} }, "env": { "production": { "vars": { ${v} } } } }`);
    return f;
  };
  it('behind the flag, no contact details: a warning; the block and the "כתבו לנו" lines are out', () => {
    const r = run(['tools/build-copy.ts', `--wrangler=${wrangler('UNDECIDED')}`, `--out=${out}`]);
    expect(r.status, r.stderr).toBe(0);
    expect(r.stderr).toMatch(/warning \(top level\): no business contact/);
    const built = JSON.parse(readFileSync(out, 'utf8')) as { contact: unknown; strings: Record<string, string | null> };
    expect(built.contact).toBeNull();
    expect(built.strings['order.next.delivered']).toBe('ההזמנה נמסרה.');
    expect(built.strings['order.no_access_contact']).toBeNull();
    expect(JSON.stringify(built.strings)).not.toMatch(/כתבו לנו|פנו אלינו/);
  });
  it('the public build stops without them, or with an address reserved for examples; it passes with real ones (S22: made at run time)', () => {
    const none = run(['tools/build-copy.ts', `--wrangler=${wrangler('UNDECIDED')}`, `--out=${out}`], { HD_PUBLIC: '1' });
    expect(none.status).toBe(1);
    expect(none.stderr).toMatch(/production: no business contact.*The public build needs the shop's contact details/);
    const example = run(['tools/build-copy.ts', `--wrangler=${wrangler('hello@example.com')}`, `--out=${out}`], { HD_PUBLIC: '1' });
    expect(example.status).toBe(1);
    expect(example.stderr).toMatch(/reserved for examples/);
    // S22 (QA ת69): the repo's own test values are samples now; the address and phone that pass are made at run time
    const good = { email: `shop@hd${Date.now().toString(36)}r.co.il`, phone: `03-7${String(Date.now()).slice(-6)}` };
    const ok = run(['tools/build-copy.ts', `--wrangler=${wrangler(good.email, good.phone)}`, `--out=${out}`], { HD_PUBLIC: '1' });
    expect(ok.status, ok.stderr).toBe(0);
    const built = JSON.parse(readFileSync(out, 'utf8')) as { contact: unknown; strings: Record<string, string | null> };
    expect(built.contact).toEqual({ email: good.email, phone: good.phone, phone_href: `+9723${good.phone.slice(3)}` });
    expect(built.strings['order.next.delivered']).toMatch(/כתבו לנו/);
    expect(built.strings['legal.draft']).not.toMatch(/פרטי הקשר יושלמו/);
  });
  it('malformed contact details stop any build', () => {
    const r = run(['tools/build-copy.ts', `--wrangler=${wrangler('shop-at-hd')}`, `--out=${out}`]);
    expect(r.status).toBe(1);
    expect(r.stderr).toMatch(/CONTACT_EMAIL="shop-at-hd" is not an email address/);
  });
  it('no contact line promises, in either wording; "כתבו לנו" only in a contact line', () => {
    const src = loadCopy();
    for (const [k, e] of Object.entries(src.strings)) {
      for (const st of STATES) {
        const l = lineOf(e, st);
        if (l && !st.contact) expect(l, `${k} without contact`).not.toMatch(/כתבו לנו|פנו אלינו|לכתוב לנו/);
      }
    }
    expect(copyIssues(src)).toEqual([]);
  });
  it('no "כתבו לנו" left in the web’s or the Worker’s code outside the copy and the contact-aware error line', () => {
    const found: string[] = [];
    const walk = (d: string): void => {
      for (const n of readdirSync(d)) {
        const p = join(d, n);
        if (statSync(p).isDirectory()) {
          if (n !== 'test-page') walk(p);
        } else if (/\.tsx?$/.test(n) && codeStrings(readFileSync(p, 'utf8'), p).some((s) => /כתבו לנו|פנו אלינו|יושלמו לפני ההשקה/.test(s)))
          found.push(relative(sitePath(), p));
      }
    };
    walk(sitePath('web/src'));
    walk(sitePath('api/src'));
    expect(found).toEqual(['api/src/lib/log.ts']);
  });
});
