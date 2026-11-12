// compare two .generated snapshots: products, prices, hidden, room options, story items
import { readFileSync, existsSync } from 'node:fs';
const [A, B] = process.argv.slice(2);
const j = (d, f) => existsSync(`${d}/${f}`) ? JSON.parse(readFileSync(`${d}/${f}`, 'utf8')) : null;
for (const f of ['catalog.full.json', 'catalog.public.json', 'catalog.story.full.json', 'catalog.story.public.json', 'catalog.test-page.full.json', 'catalog.test-page.public.json']) {
  const a = j(A, f), b = j(B, f);
  if (!a || !b) { console.log(`${f}: missing in ${a ? 'new' : 'base'}`); continue; }
  const pa = new Map(a.products.map((p) => [p.id, p])), pb = new Map(b.products.map((p) => [p.id, p]));
  const lines = [];
  for (const id of pa.keys()) if (!pb.has(id)) lines.push(`  - removed product ${id} (${pa.get(id).card_id ?? ''})`);
  for (const id of pb.keys()) if (!pa.has(id)) lines.push(`  + added product ${id} (${pb.get(id).card_id ?? ''})`);
  for (const [id, p] of pb) {
    const q = pa.get(id); if (!q) continue;
    const va = new Map(q.variants.map((v) => [v.id, v])), vb = new Map(p.variants.map((v) => [v.id, v]));
    for (const k of va.keys()) if (!vb.has(k)) lines.push(`  ${id}: variant removed ${k}`);
    for (const k of vb.keys()) if (!va.has(k)) lines.push(`  ${id}: variant added ${k}`);
    for (const [k, v] of vb) { const w = va.get(k); if (w && JSON.stringify({ p: w.price_agorot, s: w.status ?? w.available }) !== JSON.stringify({ p: v.price_agorot, s: v.status ?? v.available })) lines.push(`  ${id}: ${k} price ${w.price_agorot} → ${v.price_agorot}, status ${w.status ?? w.available} → ${v.status ?? v.available}`); }
    if ((q.default_variant_id ?? null) !== (p.default_variant_id ?? null)) lines.push(`  ${id}: default variant ${q.default_variant_id} → ${p.default_variant_id}`);
    const keys = ['price_agorot', 'price_from_agorot', 'name_he', 'status', 'compare_at_agorot'];
    for (const k of keys) if (k in p || k in q) if (JSON.stringify(q[k]) !== JSON.stringify(p[k])) lines.push(`  ${id}: ${k} ${JSON.stringify(q[k])} → ${JSON.stringify(p[k])}`);
  }
  const ha = JSON.stringify(a.hidden ?? []), hb = JSON.stringify(b.hidden ?? []);
  if (ha !== hb) lines.push(`  hidden: ${JSON.stringify((a.hidden ?? []).map((h) => h.id))} → ${JSON.stringify((b.hidden ?? []).map((h) => h.id))}`);
  const ra = JSON.stringify((a.rooms ?? []).map((r) => [r.id, (r.slots ?? []).map((s) => [s.id, (s.options ?? []).map((o) => o.product_id)])]));
  const rb = JSON.stringify((b.rooms ?? []).map((r) => [r.id, (r.slots ?? []).map((s) => [s.id, (s.options ?? []).map((o) => o.product_id)])]));
  if (ra !== rb) lines.push(`  room options changed`);
  console.log(`${f}: ${a.products.length} → ${b.products.length} products${lines.length ? '\n' + lines.join('\n') : ', no change'}`);
}
