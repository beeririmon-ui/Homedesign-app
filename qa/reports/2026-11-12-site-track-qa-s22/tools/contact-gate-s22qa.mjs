/**
 * QA S22, ת69 and ה25: my S20 contact-gate harness (tools/build-copy.ts against variants of api/wrangler.jsonc, once as
 * the public build, HD_PUBLIC=1, and once behind the flag) with NEW values: dummies S22 should know (placeholders,
 * capitals, sub-addresses, our test domains), dummies its rules may not know (the Hebrew "John Doe", template names),
 * and real-looking values that must pass (made at run time with a random part, so no good value is written anywhere,
 * and printed only as their shape). Then check-config (ה25) on a production config with a few of them.
 * Want: public fail + flag warn for a dummy; pass + pass for a real-looking value.
 *   node contact-gate-s22qa.mjs --site=<copy>/site --tmp=<scratch> --out=<json>
 */
import { execFileSync, spawnSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const arg = (n) => process.argv.find((a) => a.startsWith(`--${n}=`))?.slice(n.length + 3);
const SITE = arg('site');
const TMP = arg('tmp');
const OUT = arg('out');
mkdirSync(TMP, { recursive: true });
// the repo's config, comments and trailing commas out (strings untouched)
const text = readFileSync(join(SITE, 'api/wrangler.jsonc'), 'utf8');
let out = '', inStr = false;
for (let i = 0; i < text.length; i++) {
  const ch = text[i];
  if (inStr) { out += ch; if (ch === '\\') out += text[++i] ?? ''; else if (ch === '"') inStr = false; }
  else if (ch === '"') { inStr = true; out += ch; }
  else if (ch === '/' && text[i + 1] === '/') { while (i < text.length && text[i] !== '\n') i++; out += '\n'; }
  else if (ch === '/' && text[i + 1] === '*') { i = text.indexOf('*/', i + 2) + 1; }
  else out += ch;
}
const base = JSON.parse(out.replace(/,(\s*[}\]])/g, '$1'));
const UNSET = Symbol('unset');
// [id, email, phone, what, want public, want flag]  want: fail | pass | warn
const R = () => Math.random().toString(36).slice(2, 7).replace(/\d/g, 'q');
const DIG = () => {
  for (;;) {
    const d = String(2000000 + Math.floor(Math.random() * 7000000));
    if (!/(\d)\1\1/.test(d) && !d.startsWith('555')) return d;
  }
};
const realMail = (local) => `${local}@beit-${R()}-studio.co.il`;
const GOODMAIL = realMail('hello');
const realPhone = (p) => `${p}-${DIG()}`;
const V = [
  // dummies S22's rules name
  ['Q1', 'info@example.net', 'UNDECIDED', 'example.net', 'fail', 'warn'],
  ['Q2', 'Info@Example.Co.IL ', 'UNDECIDED', 'example.co.il, capitals, a trailing space', 'fail', 'warn'],
  ['Q3', 'contact@your-domain.co.il', 'UNDECIDED', 'your-domain', 'fail', 'warn'],
  ['Q4', 'hello@yourstore.com', 'UNDECIDED', 'yourstore', 'fail', 'warn'],
  ['Q5', 'name@company.com', 'UNDECIDED', 'name@', 'fail', 'warn'],
  ['Q6', 'shop+orders@hd-test.co.il', 'UNDECIDED', 'a sub-address at our test domain', 'fail', 'warn'],
  ['Q7', 'info@mail.hd-qa.co.il', 'UNDECIDED', 'a subdomain of our QA domain', 'fail', 'warn'],
  ['Q8', 'noreply@' + GOODMAIL.split('@')[1], 'UNDECIDED', 'noreply@ (not a contact)', 'fail', 'warn'],
  ['Q9', 'JOHN.DOE@gmail.com', 'UNDECIDED', 'john.doe, capitals', 'fail', 'warn'],
  // dummies S22's rules may not name
  ['Q10', 'israel.israeli@gmail.com', 'UNDECIDED', 'ישראל ישראלי, the Hebrew John Doe', 'fail', 'warn'],
  ['Q11', 'israel@israeli.co.il', 'UNDECIDED', 'ישראל ישראלי as the domain', 'fail', 'warn'],
  ['Q12', 'your@email.com', 'UNDECIDED', 'your@email.com, a common template', 'fail', 'warn'],
  ['Q13', 'info@mysite.co.il', 'UNDECIDED', 'mysite, a common template', 'fail', 'warn'],
  ['Q14', 'office@mycompany.co.il', 'UNDECIDED', 'mycompany, a common template', 'fail', 'warn'],
  ['Q15', 'test.user@gmail.com', 'UNDECIDED', 'test.user@', 'fail', 'warn'],
  ['Q16', 'info@ex\u0430mple.com', 'UNDECIDED', 'example with a Cyrillic а (a homograph)', 'fail', 'fail'],
  // dummy phones, with a real-looking address
  ['Q17', GOODMAIL, '050-1234567', 'a run', 'fail', 'warn'],
  ['Q18', GOODMAIL, '+972-3-7654321', 'a run down, +972', 'fail', 'warn'],
  ['Q19', GOODMAIL, '054-111-1111', 'one digit repeated', 'fail', 'warn'],
  ['Q20', GOODMAIL, '1-800-000-000', '1-800, zeros', 'fail', 'warn'],
  ['Q21', GOODMAIL, '050-000-0001', 'zeros and a one (a placeholder S22 does not name)', 'fail', 'warn'],
  // real-looking values: must pass both (a 555 or a short run inside a real Israeli number is not a placeholder)
  ['Q22', GOODMAIL, realPhone('03'), 'a landline, made at run time', 'pass', 'pass'],
  ['Q23', realMail('office'), realPhone('054'), 'a mobile, made at run time', 'pass', 'pass'],
  ['Q24', `office@testa-${R()}.co.il`, 'UNDECIDED', '"testa-…" is not "test"', 'pass', 'pass'],
  ['Q25', `samples@linen-${R()}.co.il`, 'UNDECIDED', '"samples@" is not "sample@"', 'pass', 'pass'],
  ['Q26', `user.care@${R()}-home.co.il`, 'UNDECIDED', '"user.care@" is not "user@"', 'pass', 'pass'],
  ['Q27', `hello@${R()}-domain-studio.co.il`, 'UNDECIDED', '"…-domain-studio" is not "domain"', 'pass', 'pass'],
  ['Q28', GOODMAIL, '03-555' + String(1000 + Math.floor(Math.random() * 8000)), 'a Gush Dan landline 03-555xxxx (real range, not the US 555)', 'pass', 'pass'],
  ['Q29', GOODMAIL, '050-555' + String(1000 + Math.floor(Math.random() * 8000)), 'a mobile 050-555xxxx', 'pass', 'pass'],
  ['Q30', GOODMAIL, '*2345', 'a star number that is a run (*2345)', 'pass', 'pass'],
];
const rows = [];
for (const [id, email, phone, what, wantPub, wantFlag] of V) {
  const cfg = JSON.parse(JSON.stringify(base));
  for (const vars of [cfg.vars, cfg.env.production.vars]) {
    if (email === UNSET) delete vars.CONTACT_EMAIL; else vars.CONTACT_EMAIL = email;
    if (phone === UNSET) delete vars.CONTACT_PHONE; else vars.CONTACT_PHONE = phone;
  }
  const f = join(TMP, `wrangler-${id}.json`);
  writeFileSync(f, JSON.stringify(cfg, null, 1));
  for (const [mode, want] of [['public', wantPub], ['flag', wantFlag]]) {
    const o = join(TMP, `copy-${id}-${mode}.json`);
    const env = { ...process.env, HD_PUBLIC: mode === 'public' ? '1' : '0' };
    const r = spawnSync('node', ['node_modules/tsx/dist/cli.mjs', 'tools/build-copy.ts', `--wrangler=${f}`, `--out=${o}`], { cwd: SITE, env, encoding: 'utf8' });
    const all = `${r.stdout}\n${r.stderr}`;
    const warn = /warning \(/.test(all);
    const got = r.status !== 0 ? 'fail' : warn ? 'warn' : 'pass';
    const chosen = r.status === 0 && existsSync(o) ? JSON.parse(readFileSync(o, 'utf8')).contact : null;
    const first = (all.split('\n').find((l) => /^\s{2}\S|warning/.test(l)) ?? '').trim().slice(0, 200);
    const ok = got === want;
    const hide = (s) => (typeof s === 'string' && wantPub === 'pass' ? s.replace(/[a-z0-9]/gi, (c) => (/\d/.test(c) ? '9' : 'x')) : s);
    rows.push({ id, mode, what, email: hide(email), phone: hide(phone), want, got, exit: r.status, first: wantPub === 'pass' ? '(hidden: a value made at run time)' : first });
    const shape = (s) => (typeof s === 'string' && wantPub === 'pass' ? s.replace(/[a-z0-9]/gi, (c) => (/\d/.test(c) ? '9' : 'x')) : s);
    console.log(`${ok ? 'ok  ' : 'GAP '} ${id.padEnd(4)} ${mode.padEnd(6)} want ${want.padEnd(4)} got ${got.padEnd(4)} ${JSON.stringify(shape(email))} ${JSON.stringify(shape(phone))} ${what} | ${(wantPub === 'pass' ? first.replace(/[a-z0-9]/gi, '·') : first)}`);
  }
}
writeFileSync(OUT, JSON.stringify(rows, null, 1) + '\n');
console.log(`rows as wanted: ${rows.filter((r) => r.want === r.got).length}/${rows.length}`);

// ה25: check-config on a production config with a few of the values (the repo's file, production's two contact vars set)
const cc = [];
for (const id of ['Q1', 'Q10', 'Q12', 'Q17', 'Q22', 'Q28']) {
  const v = V.find((x) => x[0] === id);
  const cfg = JSON.parse(JSON.stringify(base));
  cfg.env.production.vars.CONTACT_EMAIL = v[1];
  cfg.env.production.vars.CONTACT_PHONE = v[2];
  const f = join(TMP, `deploy-${id}.json`);
  writeFileSync(f, JSON.stringify(cfg, null, 1));
  const r = spawnSync('node', ['node_modules/tsx/dist/cli.mjs', 'api/scripts/check-config.ts', f], { cwd: SITE, encoding: 'utf8' });
  const line = `${r.stdout}\n${r.stderr}`.split('\n').find((l) => /production: CONTACT|sample|is not/.test(l)) ?? '';
  const want = v[4] === 'fail' ? 1 : 0;
  cc.push({ id, want_exit: want, exit: r.status, line: v[4] === 'pass' ? '(hidden)' : line.trim().slice(0, 200) });
  console.log(`${r.status === want ? 'ok  ' : 'GAP '} check-config production ${id} want exit ${want} got ${r.status} ${v[4] === 'pass' ? '' : line.trim().slice(0, 160)}`);
}
writeFileSync(OUT.replace(/\.json$/, '-check-config.json'), JSON.stringify(cc, null, 1) + '\n');
