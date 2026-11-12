/**
 * S22 (QA S20's findings):
 * - ת67: the definition of a promise on two external lists, kept out of the fixture: QA S20's fresh list and
 *   frontend-dev's own S22 list (written before the change, never tuned to). Both numbers are in the S22 README.
 * - ת68: `needs: "any"` only for a line that implies nothing; IMPLIES wider; groups and lines over all 128 states.
 * - ת69 and ה25: a sample contact (reserved, ours, a placeholder) stops the public build and the deploy check, and is a
 *   warning behind the flag; every address and phone of the site's tests, fixtures and docs is a sample.
 * - ת71: `.join(sep)` and `.concat()` are read as the text they make.
 * - The cards (the manager's addendum, 2026-11-12): no site product comes from a rejected card, and every product the
 *   story and the houses name resolves.
 */
import { describe, expect, it } from 'vitest';
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, relative } from 'node:path';
import { contactSampleIssues, nationalDigits, sampleEmailReason, samplePhoneReason } from '@hd/shared/contact-samples';
import { codeStrings } from '../lib/promise-scan';
import { STATES, copyIssues, impliedCapabilities, loadCopy, promiseFindings, selectCopy, type CopySource } from '../lib/promises';
import { repoPath, sitePath } from '../lib/paths';

const TSX = sitePath('node_modules/tsx/dist/cli.mjs');
const tmp = (name: string) => mkdtempSync(join(tmpdir(), `hd-s22-${name}-`));
const run = (args: string[], env: Record<string, string> = {}, cwd = sitePath()) =>
  spawnSync(process.execPath, [TSX, ...args], { cwd, encoding: 'utf8', timeout: 90_000, env: { ...process.env, HD_PUBLIC: '', HD_WRANGLER: '', ...env } });

type Line = { id: string; tier: 'A' | 'B'; text: string };
const list = (f: string) =>
  JSON.parse(readFileSync(sitePath(`tools/test/external/${f}.json`), 'utf8')) as { promises: Line[]; honest: Line[]; in_fixture?: string[] };
const caught = (t: string) => promiseFindings(t).length > 0;

describe('S22 ת67: the definition generalises (external lists, not the fixture)', () => {
  const fixture = readFileSync(sitePath('tools/test/fixtures/promise-phrases.json'), 'utf8');
  for (const [name, minB] of [
    ['qa-s20-fresh', 15],
    ['s22-fresh', 7],
  ] as const)
    it(`${name}: every tier-A promise caught, no honest line flagged, tier B at least ${minB}`, () => {
      const l = list(name);
      expect(l.promises).toHaveLength(40);
      expect(l.honest).toHaveLength(40);
      expect(l.promises.filter((p) => p.tier === 'A' && !caught(p.text)).map((p) => p.id)).toEqual([]);
      expect(l.honest.filter((p) => caught(p.text)).map((p) => `${p.id} ${p.text}`)).toEqual([]);
      expect(l.promises.filter((p) => p.tier === 'B' && caught(p.text)).length).toBeGreaterThanOrEqual(minB);
      // external: its lines are not in the fixture the definition was built on (but the ones its note declares)
      const inFixture = [...l.promises, ...l.honest].filter((p) => fixture.includes(JSON.stringify(p.text))).map((p) => p.id);
      expect(inFixture).toEqual(l.in_fixture ?? []);
    });
  it('the forms the brief names', () => {
    for (const t of [
      'עם יציאת החבילה יישלח מספר מעקב.',
      'תקבלו את מספר המעקב ברגע שהחבילה יוצאת.',
      'נשמור אתכם מעודכנים.',
      'נשאיר אתכם מעודכנים.',
      'תזכורת תשלח יום לפני המסירה.',
      'חשבונית במייל',
      'עדכונים ב-SMS',
      'אישור במייל',
      'התראות בוואטסאפ',
    ])
      expect(promiseFindings(t), t).not.toEqual([]);
  });
  it('a heading before a negation is a label; English negates too; a field label of two words passes', () => {
    for (const t of [
      'דיוור שיווקי: האתר לא שולח דיוור.',
      'מדיניות הדיוור: האתר אינו שולח מיילים שיווקיים.',
      'We do not have a newsletter.',
      'No newsletter here.',
      'כתובת אימייל',
      'אימייל וטלפון',
      'שם ומייל',
      'אימייל: shop@example.com',
      'אם תשלח לנו הודעה, נבדוק.',
      'האתר לא שולח דיוור שיווקי.',
    ])
      expect(promiseFindings(t), t).toEqual([]);
  });
  it('"don’t forget" asks the reader to look: it negates nothing', () => {
    expect(caught("Don't forget to check your inbox.")).toBe(true);
    expect(caught('לא לשכוח לבדוק גם בתיקיית הספאם.')).toBe(true);
    expect(caught('אין ספאם ואין ניוזלטר.')).toBe(false);
  });
  it('the site’s own copy: no line shown without a provider promises, and the copy file is clean', () => {
    expect(copyIssues(loadCopy())).toEqual([]);
  });
});

describe('S22 ת68: the needs check', () => {
  const src = () => JSON.parse(readFileSync(sitePath('copy/promises.he.json'), 'utf8')) as CopySource & { strings: Record<string, Record<string, unknown>> };
  it('128 states: every set of capabilities, with and without contact details', () => {
    expect(STATES).toHaveLength(128);
    expect(new Set(STATES.map((s) => `${s.capabilities.join('+')}|${s.contact}`)).size).toBe(128);
  });
  it('"any" only for a line that implies no capability (N7); the privacy line names processors, not promises', () => {
    const s = src();
    s.strings['checkout.total_note']!.needs = 'any';
    expect(copyIssues(s).join('\n')).toMatch(/checkout\.total_note: "needs" is "any", but the email line promises invoice_email/);
    expect(impliedCapabilities((loadCopy().strings['privacy.processors'] as { email: string }).email)).toEqual([]);
  });
  for (const [id, line, cap] of [
    ['N2', 'את פרטי ההזמנה שלחנו לאימייל שלכם, ונעדכן אתכם אם המסירה תתאחר.', 'delay_notice'],
    ['N4', 'את פרטי ההזמנה ואת הקבלה שלחנו לאימייל שלכם.', 'invoice_email'],
    ['N5', 'את פרטי ההזמנה שלחנו לאימייל שלכם. נודיע לכם כשיהיה שוב במלאי.', 'back_in_stock'],
    ['N6', 'את פרטי ההזמנה שלחנו לאימייל שלכם. נשלח לכם גם הטבות והנחות במייל.', 'marketing'],
    ['N3', 'את פרטי ההזמנה שלחנו לאימייל שלכם, ומספר המעקב יישלח במייל.', 'shipping_update'],
  ] as const)
    it(`${id}: an email line that promises ${cap} outside its needs stops`, () => {
      const s = src();
      s.strings['order.no_access']!.email = line;
      expect(copyIssues(s).join('\n')).toMatch(new RegExp(`order\\.no_access: the email line promises ${cap}`));
    });
  it('N8b: a group split only by pairs is caught (offer and why need one pair, the rest another)', () => {
    const s = src();
    for (const k of ['waitlist.offer', 'waitlist.why']) s.strings[k]!.needs = ['back_in_stock', 'marketing'];
    for (const k of ['waitlist.submit', 'waitlist.done', 'story.unavailable_note']) s.strings[k]!.needs = ['back_in_stock', 'order_confirmation'];
    expect(copyIssues(s).join('\n')).toMatch(/group waitlist: its lines are shown or hidden together/);
  });
  it('in every state, every line shown promises only what that state sends', () => {
    const copy = loadCopy();
    for (const st of STATES) {
      const lines = selectCopy(copy, st);
      for (const [k, l] of Object.entries(lines)) {
        if (typeof l !== 'string') continue;
        const e = copy.strings[k]!;
        if ('email' in e && l === e.email)
          expect(
            impliedCapabilities(l).filter((c) => !st.capabilities.includes(c)),
            `${k} ${st.capabilities}`,
          ).toEqual([]);
        else expect(promiseFindings(l), `${k}`).toEqual([]);
      }
    }
  });
});

describe('S22 ת69, ה25: sample contact values', () => {
  const dir = tmp('contact');
  const out = join(dir, 'copy.he.json');
  /** a wrangler config whose top level and production carry these contact details */
  const wrangler = (email: string, phone = 'UNDECIDED') => {
    const f = join(dir, `w-${Math.random().toString(36).slice(2)}.jsonc`);
    const v = (env: string) => `"ENVIRONMENT": "${env}", "EMAIL_PROVIDER": "UNDECIDED", "CONTACT_EMAIL": "${email}", "CONTACT_PHONE": "${phone}"`;
    writeFileSync(f, `{ "vars": { ${v('development')} }, "env": { "production": { "vars": { ${v('production')} } } } }`);
    return f;
  };
  /** the one address and phone that pass: made at run time, so no good value is ever written in the repo */
  const stamp = Date.now().toString(36);
  const good = { email: `info@hd${stamp}z.co.il`, phone: `04-6${String(Date.now()).slice(-6)}` };
  const SAMPLES: [string, string][] = [
    ['shop@example.com', 'UNDECIDED'],
    ['shop@example.co.il', 'UNDECIDED'],
    ['info@mail.example.org', 'UNDECIDED'],
    ['a@shop.test', 'UNDECIDED'],
    ['shop@hd-test.co.il', 'UNDECIDED'],
    ['info@hd-qa.co.il', 'UNDECIDED'],
    ['email@domain.com', 'UNDECIDED'],
    ['info@yourdomain.co.il', 'UNDECIDED'],
    ['test@test.co.il', 'UNDECIDED'],
    [`test@hd${stamp}z.co.il`, 'UNDECIDED'],
    [good.email, '03-1234567'],
    [good.email, '050-0000000'],
    [good.email, '052-7654321'],
    [good.email, '+972 50-123-4567'],
    [good.email, '1-800-123-456'],
    [good.email, '*1234'],
    [good.email, '04-8123456'],
  ];
  it('each sample stops the public build, and is a warning behind the flag', () => {
    for (const [email, phone] of SAMPLES) {
      const w = wrangler(email, phone);
      const pub = run(['tools/build-copy.ts', `--wrangler=${w}`, `--out=${out}`], { HD_PUBLIC: '1' });
      expect(pub.status, `${email} ${phone} public`).toBe(1);
      expect(pub.stderr).toMatch(/production: CONTACT_(?:EMAIL|PHONE)=.+ is a sample/);
      const flag = run(['tools/build-copy.ts', `--wrangler=${w}`, `--out=${out}`]);
      expect(flag.status, `${email} ${phone} flag: ${flag.stderr}`).toBe(0);
      expect(flag.stderr).toMatch(/warning \(top level\): CONTACT_(?:EMAIL|PHONE)=.+ is a sample/);
    }
  }, 240_000);
  it('a value made at run time passes both builds without a warning', () => {
    const w = wrangler(good.email, good.phone);
    for (const env of [{ HD_PUBLIC: '1' }, { HD_PUBLIC: '0' }]) {
      const r = run(['tools/build-copy.ts', `--wrangler=${w}`, `--out=${out}`], env);
      expect(r.status, r.stderr).toBe(0);
      expect(r.stderr).not.toMatch(/sample/);
    }
  });
  /** the repo's own config, with these contact details in every environment (check-config wants the providers too) */
  const deployConfig = (email: string, phone = 'UNDECIDED') => {
    const f = join(dir, `d-${Math.random().toString(36).slice(2)}.jsonc`);
    writeFileSync(
      f,
      readFileSync(sitePath('api/wrangler.jsonc'), 'utf8')
        .replaceAll('"CONTACT_EMAIL": "UNDECIDED"', `"CONTACT_EMAIL": "${email}"`)
        .replaceAll('"CONTACT_PHONE": "UNDECIDED"', `"CONTACT_PHONE": "${phone}"`),
    );
    return f;
  };
  it('ה25: check-config fails production on a sample, and warns in another environment', () => {
    const prod = run(['api/scripts/check-config.ts', deployConfig('shop@example.co.il')]);
    expect(prod.status).toBe(1);
    expect(prod.stderr).toMatch(/production: CONTACT_EMAIL=shop@example\.co\.il is a sample address/);
    expect(prod.stderr).toMatch(/warning \(\(top level\)\): CONTACT_EMAIL=shop@example\.co\.il/);
    expect(prod.stderr).toMatch(/warning \(preview\): CONTACT_EMAIL=shop@example\.co\.il/);
    const phone = run(['api/scripts/check-config.ts', deployConfig(good.email, '050-0000000')]);
    expect(phone.status).toBe(1);
    expect(phone.stderr).toMatch(/production: CONTACT_PHONE=050-0000000 is a sample number/);
    const ok = run(['api/scripts/check-config.ts', deployConfig(good.email, good.phone)]);
    expect(ok.status, ok.stderr).toBe(0);
    expect(ok.stderr).not.toMatch(/sample/);
    // the repo's own config: UNDECIDED everywhere, so nothing is a sample
    expect(run(['api/scripts/check-config.ts']).status).toBe(0);
  });
  it('the rules: reserved, ours, placeholders; a real-looking value is not touched', () => {
    expect(contactSampleIssues({ CONTACT_EMAIL: 'UNDECIDED', CONTACT_PHONE: 'UNDECIDED' })).toEqual([]);
    expect(sampleEmailReason('SHOP@EXAMPLE.CO.IL')).toMatch(/reserved/);
    expect(sampleEmailReason('x@sub.hd-qa.co.il')).toMatch(/test domain/);
    expect(sampleEmailReason('john.doe@hd' + stamp + 'z.co.il')).toMatch(/name before the @/);
    expect(sampleEmailReason(good.email)).toBeNull();
    expect(samplePhoneReason(good.phone)).toBeNull();
    expect(nationalDigits('+972 54-771-6204')).toBe('0547716204');
    expect(samplePhoneReason('052-555-1234')).toMatch(/555/);
  });
  it('every address and phone in the site’s tests, fixtures and docs, the briefs and docs/ops is a sample', () => {
    const SKIP =
      /(^|\/)(node_modules|dist|dist-artifact|\.generated|\.ssr|\.wrangler-state|\.wrangler|test-results|playwright-report|media|\.cache|prototype|screens)(\/|$)|^web\/story\/|^web\/test\/story\//;
    const TEXT = /\.(?:ts|tsx|mts|mjs|js|json|jsonc|md|html|sh|txt|css)$/;
    const EMAIL = /(?<![:\w.%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g;
    const PHONE = /(?<![\d.\w-])(?:\+972[-\s]?|0)(?:[2-489]|5\d|7\d)[-\s]?\d{3}[-\s]?\d{4}(?![\d-])/g;
    const files = (root: string, base = root): string[] =>
      existsSync(root)
        ? readdirSync(root).flatMap((e) => {
            const p = join(root, e);
            const r = relative(base, p).split('\\').join('/');
            if (SKIP.test(r)) return [];
            return statSync(p).isDirectory() ? files(p, base) : TEXT.test(e) ? [p] : [];
          })
        : [];
    const notSample: string[] = [];
    let n = 0;
    for (const f of [...files(sitePath()), ...files(repoPath('briefs')), ...files(repoPath('docs/ops'))]) {
      const t = readFileSync(f, 'utf8');
      for (const m of t.matchAll(EMAIL)) {
        n++;
        // a code string, not an address: a scoped package or a decorator never has a dot-TLD after a slash-free host
        if (!sampleEmailReason(m[0].replace(/^[-.]+/, ''))) notSample.push(`${relative(repoPath(), f)}: ${m[0]}`);
      }
      for (const m of t.matchAll(PHONE)) {
        n++;
        if (!samplePhoneReason(m[0])) notSample.push(`${relative(repoPath(), f)}: ${m[0]}`);
      }
    }
    expect(n).toBeGreaterThan(50);
    expect(notSample).toEqual([]);
  }, 60_000);
});

describe('S22 ת71: joins in code are read joined', () => {
  const found = (code: string) => codeStrings(code, 'x.js').filter((t) => promiseFindings(t).length);
  it('QA X15: an array’s join(" "), and any fixed separator; X16: concat', () => {
    expect(found('export const x=["אישור ההזמנה","יישלח","במייל"].join(" ");')).toContain('אישור ההזמנה יישלח במייל');
    expect(found('export const x=["נעדכן","אתכם"].join("\\u0020");')).toContain('נעדכן אתכם');
    expect(found('export const x=["נעדכן","אתכם"].join(sep);')).toContain('נעדכן אתכם');
    expect(found('export const x="האישור ".concat("יגיע ","לתיבת הדואר");')).toContain('האישור יגיע לתיבת הדואר');
    expect(found('export const x=`${a}`.concat("נשלח לכם ", "אישור");')).toContain('נשלח לכם אישור');
    expect(found('export const x=["המלאי","אינו","זמין"].join(" ");')).toEqual([]);
  });
  it('the gate stops a chunk with either (a scratch dist)', () => {
    for (const code of ['export const x=["אישור ההזמנה","יישלח","במייל"].join(" ");', 'export const x="האישור ".concat("יגיע ","לתיבת הדואר");']) {
      const d = tmp('dist');
      mkdirSync(join(d, 'assets'));
      writeFileSync(
        join(d, 'index.html'),
        '<!doctype html><html lang="he"><head><script type="module" src="/assets/main-a1.js"></script></head><body><p>הבית</p></body></html>',
      );
      writeFileSync(join(d, 'assets/main-a1.js'), `const e=()=>import("./Order-b2.js");export{e};`);
      writeFileSync(join(d, 'assets/Order-b2.js'), code);
      const r = run(['tools/check-promises.ts', `--dist=${d}`, '--worker-bundle=none', `--json=${join(d, '..', `${relative(tmpdir(), d)}.json`)}`]);
      expect(r.status, r.stdout + r.stderr).toBe(1);
      expect(r.stdout + r.stderr).toMatch(/Order-b2\.js/);
    }
  }, 120_000);
});

describe('S22 addendum: the cards behind the catalogs', () => {
  const gen = (f: string) => sitePath('.generated', f);
  const built = existsSync(gen('catalog.full.json')) && existsSync(gen('catalog.story.full.json'));
  it.skipIf(!built)('no product in a site catalog comes from a rejected card (the floor-lamp duplicate is SUPERSEDED)', () => {
    const cards = new Map<string, { status?: string }>();
    const walk = (d: string): void => {
      for (const e of readdirSync(d)) {
        const p = join(d, e);
        if (statSync(p).isDirectory()) walk(p);
        else if (e.endsWith('.json'))
          try {
            const c = JSON.parse(readFileSync(p, 'utf8')) as { id?: string; status?: string };
            if (c.id) cards.set(c.id, c);
          } catch {
            /* not a card */
          }
      }
    };
    walk(repoPath('data/products'));
    for (const f of ['catalog.full.json', 'catalog.story.full.json', 'catalog.test-page.full.json']) {
      if (!existsSync(gen(f))) continue;
      const c = JSON.parse(readFileSync(gen(f), 'utf8')) as { products: { card_id: string }[] };
      for (const p of c.products) expect(cards.get(p.card_id)?.status, `${f}: ${p.card_id}`).not.toBe('rejected');
    }
  });
  it.skipIf(!built)('every product the story and the warm-modern house name is built, or hidden with a reason', () => {
    const story = JSON.parse(readFileSync(gen('catalog.story.full.json'), 'utf8')) as {
      products: { card_id: string }[];
      hidden: { id: string; reason: string }[];
    };
    const known = new Set([...story.products.map((p) => p.card_id), ...story.hidden.map((h) => h.id)]);
    const named = new Set<string>();
    const collect = (x: unknown): void => {
      if (Array.isArray(x)) x.forEach(collect);
      else if (x && typeof x === 'object')
        for (const [k, v] of Object.entries(x)) {
          if (k === 'points' && Array.isArray(v))
            for (const p of v) if (typeof (p as { product?: unknown }).product === 'string') named.add((p as { product: string }).product);
          collect(v);
        }
    };
    collect(JSON.parse(readFileSync(repoPath('data/story/story.json'), 'utf8')));
    collect(JSON.parse(readFileSync(sitePath('tools/house/living-room.warm-modern.json'), 'utf8')));
    expect(named.size).toBeGreaterThan(20);
    expect([...named].filter((id) => !known.has(id))).toEqual([]);
    for (const h of story.hidden) expect(h.reason, h.id).toBeTruthy();
  });
});
