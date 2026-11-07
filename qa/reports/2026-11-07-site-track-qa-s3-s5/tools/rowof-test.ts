/**
 * qa-agent, 2026-11-07 (S3-S5): rowOf after the S4 fix, on hand-made frames (no repo file is read or written).
 *   cd site && npx tsx ../qa/reports/2026-11-07-site-track-qa-s3-s5/tools/rowof-test.ts
 */
import { rowOf } from '../../../../site/tools/lib/qa-frames.ts';
const frame = (rows: unknown[]) => ({ rows }) as never;
const cases: [string, unknown[], Record<string, string> | null, string | null][] = [
  ['rows per option, the point option has its own row', [{ card: 'c', option: { color: 'red' }, dot: 'yes' }, { card: 'c', option: { color: 'blue' }, dot: 'no' }], { color: 'blue' }, 'no'],
  ['rows per option, none for the point option', [{ card: 'c', option: { color: 'red' }, dot: 'yes' }], { color: 'green' }, null],
  ['rows per option, the point has no values', [{ card: 'c', option: { color: 'red' }, dot: 'yes' }], null, null],
  ['one row without option ids', [{ card: 'c', option: null, dot: 'yes' }], { color: 'green' }, 'yes'],
  ['two rows without option ids (ambiguous)', [{ card: 'c', option: null, dot: 'yes' }, { card: 'c', option: null, dot: 'no' }], null, null],
  ['no row at all', [{ card: 'other', option: null, dot: 'yes' }], null, null],
];
let bad = 0;
for (const [label, rows, values, want] of cases) {
  const r = rowOf(frame(rows), 'c', values) as { dot?: string } | null;
  const got = r ? (r.dot ?? '?') : null;
  const ok = got === want;
  if (!ok) bad++;
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${label}: ${got} (want ${want})`);
}
console.log(bad ? `${bad} failed` : 'all ok');
