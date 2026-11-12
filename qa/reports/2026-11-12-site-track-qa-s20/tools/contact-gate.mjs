/**
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
const V = [
  ['G1', 'UNDECIDED', 'UNDECIDED', 'the repo as it is (CONTACT1 open)', 'fail', 'warn'],
  ['G2', '', 'UNDECIDED', 'empty', 'fail', 'warn'],
  ['G3', UNSET, UNSET, 'the keys missing', 'fail', 'fail'],
  ['G4', null, null, 'null', 'fail', 'warn'],
  ['G5', 'shop@example.com', 'UNDECIDED', 'example.com', 'fail', 'pass'],
  ['G6', 'SHOP@EXAMPLE.COM', 'UNDECIDED', 'EXAMPLE.COM, capitals', 'fail', 'pass'],
  ['G7', 'info@mail.example.org', 'UNDECIDED', 'a subdomain of example.org', 'fail', 'pass'],
  ['G8', 'a@shop.test', 'UNDECIDED', '.test', 'fail', 'pass'],
  ['G9', 'x@shop.invalid', 'UNDECIDED', '.invalid', 'fail', 'pass'],
  ['G10', 'x@shop.example', 'UNDECIDED', '.example', 'fail', 'pass'],
  ['G11', 'undecided', 'UNDECIDED', 'lower case undecided', 'fail', 'fail'],
  ['G12', ' UNDECIDED', 'UNDECIDED', 'a leading space', 'fail', 'fail'],
  ['G13', 'shop@example.co.il', 'UNDECIDED', 'example.co.il (an Israeli placeholder; a registered domain, not RFC 2606)', 'fail', 'pass'],
  ['G14', 'shop@hd-test.co.il', '03-1234567', 'frontend-dev\'s own S20 test address and the phone of the error message\'s example', 'fail', 'pass'],
  ['G15', 'email@domain.com', 'UNDECIDED', 'a template\'s placeholder', 'fail', 'pass'],
  ['G16', 'info@yourdomain.co.il', 'UNDECIDED', 'a template\'s placeholder', 'fail', 'pass'],
  ['G17', 'test@test.co.il', 'UNDECIDED', 'test@test', 'fail', 'pass'],
  ['G18', 'info@hd-qa.co.il', 'UNDECIDED', 'a well-formed address (QA\'s own, local only)', 'pass', 'pass'],
  ['G19', 'info@hd-qa.co.il', '04-8123456', 'with a phone', 'pass', 'pass'],
  ['G20', 'UNDECIDED', '04-8123456', 'a phone without an email', 'fail', 'fail'],
  ['G21', 'info@hd-qa.co.il', '12345', 'a malformed phone', 'fail', 'fail'],
  ['G22', 'mailto:info@hd-qa.co.il', 'UNDECIDED', 'a mailto: prefix', 'fail', 'fail'],
  ['G23', 'info@hd-qa.co.il ', 'UNDECIDED', 'a trailing space', 'pass', 'pass'],
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
    console.log(`${ok ? 'ok  ' : 'GAP '} ${id.padEnd(4)} ${mode.padEnd(6)} want ${want.padEnd(4)} got ${got.padEnd(4)} ${JSON.stringify(email === UNSET ? '(missing)' : email)} ${what}${chosen ? ` → block: ${chosen.email}${chosen.phone ? ' / ' + chosen.phone + ' (' + chosen.phone_href + ')' : ''}` : ''} | ${first}`);
  }
}
writeFileSync(OUT, JSON.stringify(rows, null, 1) + '\n');
console.log(`rows as wanted: ${rows.filter((r) => r.want === r.got).length}/${rows.length}`);
