/**
 * S22, t67: an external list (QA S20's fresh list, or frontend-dev's own S22 list) against a definition of a promise.
 *   cd site && npx --no-install tsx <this> tools/lib/promises.ts tools/test/external/<list>.json [--json=<out>]
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

const [lib, list] = process.argv.slice(2);
const jsonOut = process.argv.find((a) => a.startsWith('--json='))?.slice(7);
const { promiseFindings } = (await import(pathToFileURL(resolve(lib!)).href)) as {
  promiseFindings: (t: string) => { rule: string; match: string }[];
};
type P = { id: string; tier: 'A' | 'B'; text: string; why: string };
const L = JSON.parse(readFileSync(list!, 'utf8')) as { promises: P[]; honest: P[] };
const rows: unknown[] = [];
const said = (t: string) => promiseFindings(t).map((f) => `${f.rule}:${f.match}`);
for (const p of L.promises) {
  const f = said(p.text);
  rows.push({ ...p, kind: 'promise', caught: f.length > 0, rules: f });
  console.log(`${f.length ? 'caught' : 'MISSED'}  ${p.id} [${p.tier}] ${p.text}${f.length ? `  ← ${f.join(', ')}` : `   (${p.why})`}`);
}
for (const p of L.honest) {
  const f = said(p.text);
  rows.push({ ...p, kind: 'honest', flagged: f.length > 0, rules: f });
  console.log(`${f.length ? 'FALSE+' : 'ok    '}  ${p.id} [${p.tier}] ${p.text}${f.length ? `  ← ${f.join(', ')}` : ''}`);
}
const miss = (t: 'A' | 'B') => L.promises.filter((p) => p.tier === t && !said(p.text).length).map((p) => p.id);
const summary = {
  promises: L.promises.length,
  caught: L.promises.filter((p) => said(p.text).length).length,
  tier_a: `${L.promises.filter((p) => p.tier === 'A').length - miss('A').length}/${L.promises.filter((p) => p.tier === 'A').length}`,
  tier_b: `${L.promises.filter((p) => p.tier === 'B').length - miss('B').length}/${L.promises.filter((p) => p.tier === 'B').length}`,
  missed_tier_a: miss('A'),
  missed_tier_b: miss('B'),
  honest: L.honest.length,
  false_positives: L.honest.filter((p) => said(p.text).length).map((p) => p.id),
};
console.log('\n' + JSON.stringify(summary));
if (jsonOut) writeFileSync(jsonOut, JSON.stringify({ summary, rows }, null, 1) + '\n');
