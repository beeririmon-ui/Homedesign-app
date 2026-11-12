/**
 * QA S22, ת71: NEW code mutations for the scanner's joins (site/tools/lib/promise-scan.ts at 9b6c6746, `codeStrings`),
 * beyond my S20 X15/X16. Each line is a chunk of minified-looking JS that renders a promise ("אישור ההזמנה יישלח במייל",
 * split so that no single literal is a promise by itself), or a control. Read through codeStrings, then promiseFindings.
 * With --dist, the stopping ones and two of the missed ones are also run through tools/check-promises.ts on a scratch
 * dist (the gate as the build runs it).
 *   cd <copy>/site && node node_modules/tsx/dist/cli.mjs <this> <copy>/site [--json=<out>] [--dist=<scratch dir>]
 */
import { spawnSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const SITE = process.argv[2]!;
const arg = (k: string) => process.argv.find((a) => a.startsWith(`--${k}=`))?.slice(k.length + 3);
const { codeStrings } = (await import(pathToFileURL(join(SITE, 'tools/lib/promise-scan.ts')).href)) as { codeStrings: (c: string, f: string) => string[] };
const { promiseFindings } = (await import(pathToFileURL(join(SITE, 'tools/lib/promises.ts')).href)) as { promiseFindings: (t: string) => unknown[] };
const P = '"אישור ההזמנה","יישלח","במייל"';
type M = { id: string; want: 'stop' | 'pass'; code: string; what: string };
const MUTS: M[] = [
  { id: 'J1', want: 'stop', code: `export const x=[${P}].join(" ").trim();`, what: 'join(" ") then .trim()' },
  { id: 'J2', want: 'stop', code: `export const x=[${P}].join(\` \`);`, what: 'join with a template-literal no-break space' },
  { id: 'J3', want: 'stop', code: `const p=[${P}];export const x=p.join(" ");`, what: 'the array in a variable, then p.join(" ") (minifiers keep it)' },
  { id: 'J4', want: 'stop', code: `export const x=[${P}].filter(Boolean).join(" ");`, what: '.filter(Boolean).join(" ") (the common idiom)' },
  { id: 'J5', want: 'stop', code: `export const x=[${P}].map(s=>s).join(" ");`, what: '.map(…).join(" ")' },
  { id: 'J6', want: 'stop', code: `export const x=Array.of(${P}).join(" ");`, what: 'Array.of(…).join(" ")' },
  { id: 'J7', want: 'stop', code: `export const x=new Array(${P}).join(" ");`, what: 'new Array(…).join(" ")' },
  { id: 'J8', want: 'stop', code: `export const x=[...[${P}]].join(" ");`, what: 'a spread inside the array' },
  { id: 'J9', want: 'stop', code: `export const x=[${P}].reduce((a,b)=>a+" "+b);`, what: '.reduce((a,b)=>a+" "+b)' },
  { id: 'J10', want: 'stop', code: `export const x="אישור ההזמנה ".concat("יישלח ").concat("במייל");`, what: 'chained .concat().concat()' },
  { id: 'J11', want: 'stop', code: `export const x=String.prototype.concat.call("אישור ההזמנה ","יישלח ","במייל");`, what: 'String.prototype.concat.call' },
  { id: 'J12', want: 'stop', code: `export const x=["אישור ההזמנה",["יישלח","במייל"].join(" ")].join(" ");`, what: 'a join inside a join' },
  { id: 'J13', want: 'stop', code: `export const x=[${P}].join(sep);`, what: 'join with a variable separator (read as a space)' },
  { id: 'J14', want: 'stop', code: `export const x=\`\${["אישור ההזמנה","יישלח"].join(" ")} במייל\`;`, what: 'a join inside a template literal' },
  { id: 'J15', want: 'pass', code: `export const x=[${P}].join("");`, what: 'control: join("") renders the words run together (that is what the reader sees)' },
  { id: 'J16', want: 'pass', code: `export const x=["המלאי","אינו","זמין","כעת"].join(" ");`, what: 'control: an honest line' },
  { id: 'J17', want: 'pass', code: `export const x=["אישור","ההזמנה"].join(" ")+" מופיע בדף";`, what: 'control: honest, joined' },
  { id: 'J18', want: 'pass', code: `export const x=["האתר","לא","שולח","מיילים"].join(" ");`, what: 'control: a negation, joined' },
];
const rows: unknown[] = [];
let ok = 0;
for (const m of MUTS) {
  const texts = codeStrings(m.code, 'assets/x-a1.js');
  const hit = texts.filter((t) => promiseFindings(t).length);
  const got = hit.length ? 'stop' : 'pass';
  if (got === m.want) ok++;
  console.log(`${got === m.want ? 'ok  ' : 'GAP '} ${m.id.padEnd(4)} want ${m.want} got ${got}  ${m.what}${hit.length ? `  ← "${hit[0]}"` : ''}`);
  rows.push({ ...m, got, texts });
}
console.log(`\n${ok}/${MUTS.length} as expected`);
const dist = arg('dist');
const gate: unknown[] = [];
if (dist) {
  for (const id of ['J1', 'J10', 'J12', 'J14', 'J3', 'J4']) {
    const m = MUTS.find((x) => x.id === id)!;
    const d = join(dist, id);
    mkdirSync(join(d, 'assets'), { recursive: true });
    writeFileSync(join(d, 'index.html'), '<!doctype html><html lang="he"><head><script type="module" src="/assets/main-a1.js"></script></head><body><p>הבית</p></body></html>');
    writeFileSync(join(d, 'assets/main-a1.js'), `const e=()=>import("./Order-b2.js");export{e};`);
    writeFileSync(join(d, 'assets/Order-b2.js'), m.code);
    const r = spawnSync(process.execPath, ['node_modules/tsx/dist/cli.mjs', 'tools/check-promises.ts', `--dist=${d}`, '--worker-bundle=none', `--json=${d}.json`], { cwd: SITE, encoding: 'utf8' });
    const line = `${r.stdout}${r.stderr}`.split('\n').find((l) => /check-promises/.test(l)) ?? '';
    console.log(`gate ${id}: exit ${r.status} (${m.want === 'stop' ? 'want 1' : 'want 0'})  ${line.slice(0, 160)}`);
    gate.push({ id, exit: r.status, line });
  }
}
const out = arg('json');
if (out) writeFileSync(out, JSON.stringify({ ok, total: MUTS.length, rows, gate }, null, 1) + '\n');
