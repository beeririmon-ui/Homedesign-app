/**
 * S22 (frontend-dev): QA S20's contact gate with the S22 expectations (QA ת69): every sample (reserved, our own test
 * values, a placeholder) stops the public build and WARNS behind the flag; QA's own info@hd-qa.co.il is a test value of
 * the repo, so it is a sample too. G24–G33 are new. The one address that must pass is made at run time, so no good
 * address is ever written in the repo.
 * QA S20, ת61, the build check: tools/build-copy.ts of the copy (8828cab9) against variants of api/wrangler.jsonc, each
 * once as the public build (HD_PUBLIC=1, production's vars) and once behind the flag (the top level's vars). The variants
 * are written to a scratch dir as plain JSON (valid JSONC); build-copy writes its choice to --out in the scratch dir, so
 * the copy's .generated is never touched. Row: exit code, the first problem or warning, and the contact it chose.
 *   node contact-gate.mjs --site=<copy>/site --tmp=<scratch> --out=<json>
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
const GOOD = `info@hd${Date.now().toString(36)}x.co.il`;
const V = [
  ['G1', 'UNDECIDED', 'UNDECIDED', 'the repo as it is (CONTACT1 open)', 'fail', 'warn'],
  ['G2', '', 'UNDECIDED', 'empty', 'fail', 'warn'],
  ['G3', UNSET, UNSET, 'the keys missing', 'fail', 'fail'],
  ['G4', null, null, 'null', 'fail', 'warn'],
  ['G5', 'shop@example.com', 'UNDECIDED', 'example.com', 'fail', 'warn'],
  ['G6', 'SHOP@EXAMPLE.COM', 'UNDECIDED', 'EXAMPLE.COM, capitals', 'fail', 'warn'],
  ['G7', 'info@mail.example.org', 'UNDECIDED', 'a subdomain of example.org', 'fail', 'warn'],
  ['G8', 'a@shop.test', 'UNDECIDED', '.test', 'fail', 'warn'],
  ['G9', 'x@shop.invalid', 'UNDECIDED', '.invalid', 'fail', 'warn'],
  ['G10', 'x@shop.example', 'UNDECIDED', '.example', 'fail', 'warn'],
  ['G11', 'undecided', 'UNDECIDED', 'lower case undecided', 'fail', 'fail'],
  ['G12', ' UNDECIDED', 'UNDECIDED', 'a leading space', 'fail', 'fail'],
  ['G13', 'shop@example.co.il', 'UNDECIDED', 'example.co.il', 'fail', 'warn'],
  ['G14', 'shop@hd-test.co.il', '03-1234567', "frontend-dev's S20 test address, the error message's phone", 'fail', 'warn'],
  ['G15', 'email@domain.com', 'UNDECIDED', "a template's placeholder", 'fail', 'warn'],
  ['G16', 'info@yourdomain.co.il', 'UNDECIDED', "a template's placeholder", 'fail', 'warn'],
  ['G17', 'test@test.co.il', 'UNDECIDED', 'test@test', 'fail', 'warn'],
  ['G18', 'info@hd-qa.co.il', 'UNDECIDED', "QA's own address: a test value of the repo (S22)", 'fail', 'warn'],
  ['G19', 'info@hd-qa.co.il', '04-8123456', "QA's own, with QA's phone", 'fail', 'warn'],
  ['G20', 'UNDECIDED', '04-8123456', 'a phone without an email', 'fail', 'fail'],
  ['G21', GOOD, '12345', 'a malformed phone', 'fail', 'fail'],
  ['G22', `mailto:${GOOD}`, 'UNDECIDED', 'a mailto: prefix', 'fail', 'fail'],
  ['G23', `${GOOD} `, 'UNDECIDED', 'an address made at run time, a trailing space', 'pass', 'pass'],
  ['G24', GOOD, 'UNDECIDED', 'an address made at run time (never in the repo)', 'pass', 'pass'],
  ['G25', GOOD, '050-0000000', 'a good address, phone 050-0000000', 'fail', 'warn'],
  ['G26', GOOD, '052-7654321', 'a good address, a descending phone', 'fail', 'warn'],
  ['G27', GOOD, '+972 50-123-4567', 'a good address, +972 and an ascending phone', 'fail', 'warn'],
  ['G28', GOOD, '1-800-123-456', 'a good address, 1-800-123-456', 'fail', 'warn'],
  ['G29', GOOD, '*1234', 'a good address, *1234', 'fail', 'warn'],
  ['G30', GOOD, '052-555-1234', 'a good address, a 555 phone (shared/test)', 'fail', 'warn'],
  ['G31', 'name@yourcompany.com', 'UNDECIDED', 'yourcompany.com', 'fail', 'warn'],
  ['G32', `test@hd${Date.now().toString(36)}y.co.il`, 'UNDECIDED', 'test@ at any domain', 'fail', 'warn'],
  ['G33', 'shop@sub.hd-test.co.il', 'UNDECIDED', 'a subdomain of our test domain', 'fail', 'warn'],
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
    rows.push({ id, mode, what, email: email === UNSET ? '(missing)' : email, phone: phone === UNSET ? '(missing)' : phone, want, got, exit: r.status, contact: chosen, first });
    console.log(`${ok ? 'ok  ' : 'GAP '} ${id.padEnd(4)} ${mode.padEnd(6)} want ${want.padEnd(4)} got ${got.padEnd(4)} ${JSON.stringify(email === UNSET ? '(missing)' : String(email).replace(/hd[0-9a-z]+[xy]\.co\.il/, '<run-time>.co.il'))} ${what}${chosen ? ` → block: ${chosen.email}${chosen.phone ? ' / ' + chosen.phone + ' (' + chosen.phone_href + ')' : ''}` : ''} | ${first}`);
  }
}
writeFileSync(OUT, JSON.stringify(rows, null, 1) + '\n');
console.log(`rows as wanted: ${rows.filter((r) => r.want === r.got).length}/${rows.length}`);
