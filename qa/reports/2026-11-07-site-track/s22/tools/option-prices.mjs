// every price a public catalog shows: the product's, and each option's (the compact options.p), by option values
import { readFileSync } from 'node:fs';
const [A, B, ...files] = process.argv.slice(2);
const prices = (f) => {
  const c = JSON.parse(readFileSync(f, 'utf8'));
  const m = new Map();
  for (const p of c.products) {
    m.set(`${p.id} (product)`, p.price_agorot);
    const o = p.options;
    if (!o?.v) continue;
    o.v.forEach((combo, i) => m.set(`${p.id} ${combo.map((vi, ai) => o.axes[ai].values[vi][0]).join('+')}${o.room === i ? ' [room]' : ''}`, o.p[i]));
  }
  return m;
};
for (const f of files) {
  const a = prices(`${A}/${f}`), b = prices(`${B}/${f}`);
  const rows = [];
  for (const [k, v] of b) if (a.get(k) !== v) rows.push(`  ${k}: ${a.has(k) ? a.get(k) / 100 : '(none)'} → ${v / 100}`);
  for (const [k, v] of a) if (!b.has(k)) rows.push(`  ${k}: ${v / 100} → (gone)`);
  console.log(`${f}: ${b.size} prices, ${rows.length} changed\n${rows.join('\n')}`);
}
