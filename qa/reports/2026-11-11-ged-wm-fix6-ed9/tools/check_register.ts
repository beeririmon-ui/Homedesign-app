/**
 * qa-agent 2026-11-11: the format check with the site's own reader (site/tools/lib/qa-frames.ts, unchanged): it must pick r13 as the
 * highest version, pass its own checkRegister, read warm-modern-A-ed9 with its rows and dots, and report ed8 (and older) as
 * superseded by ed9. The master section is not read by the site (by design), so it is checked in build.py only.
 * Usage (from anywhere): /home/user/homedesign-app/site/node_modules/.bin/tsx check_register.ts
 */
import { registerReader, rowOf } from '/home/user/homedesign-app/site/tools/lib/qa-frames.ts';

const r = registerReader();
const ed9 = r.read('warm-modern-A-ed9');
const out = {
  path: r.path,
  version: r.version,
  ed9: ed9 && { state: ed9.state, rows: ed9.rows.length, dots: ed9.rows.map((x) => `${x.card.split(' ')[0]}:${x.faithful}/${x.dot}`) },
  bowl: ed9 && rowOf(ed9, 'bowl-cj-matte-black-bowl-20', null, true)?.dot,
  camel: ed9 && rowOf(ed9, 'cushions-cj-wide-stripe-corduroy-light-green', { color: 'camel' })?.faithful,
  ed8_superseded_by: r.supersededBy('warm-modern-A-ed8'),
  ed7_superseded_by: r.supersededBy('warm-modern-A-ed7'),
  ed8_still_readable: r.read('warm-modern-A-ed8')?.state ?? null,
  others: Object.fromEntries(
    ['nordic-A-ed4', 'nordic-B-fin', 'boho-A-fin7', 'mediterranean-A-ed7', 'modern-country-A-fix4', 'japandi-A-ed5'].map((k) => [k, r.read(k)?.state ?? null]),
  ),
};
console.log(JSON.stringify(out, null, 1));
if (r.version !== 13 || !ed9 || ed9.state !== 'final_test' || out.ed8_superseded_by !== 'warm-modern-A-ed9') process.exit(1);
