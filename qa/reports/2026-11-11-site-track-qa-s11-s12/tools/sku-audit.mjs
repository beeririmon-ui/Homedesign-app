/**
 * qa-agent, 2026-11-11: does every variant the build sells carry a supplier SKU that is a variant of its card (the SKU the
 * supplier is asked for)? For a card with options: the variant's supplier_sku must be one of the card's option SKUs, and
 * for a product left with one variant (`:default`, options collapsed) it must be the card's room SKU (default_sku).
 *   node sku-audit.mjs <copy root> <out json>
 */
import { readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
const [ROOT, OUTF] = process.argv.slice(2);
const cards = new Map();
(function walk(d) { for (const n of readdirSync(d)) { const p = join(d, n); if (statSync(p).isDirectory()) walk(p); else if (n.endsWith('.json')) cards.set(n.slice(0, -5), p); } })(join(ROOT, 'data/products'));
const out = [];
for (const f of ['catalog.full.json', 'catalog.story.full.json']) {
  const c = JSON.parse(readFileSync(join(ROOT, 'site/.generated', f), 'utf8'));
  for (const p of c.products) {
    const cid = p.source_path.split('/').pop().replace(/\.json$/, '');
    const card = JSON.parse(readFileSync(cards.get(cid), 'utf8'));
    const skus = card.options?.skus?.map((s) => s.id) ?? [];
    for (const v of p.variants_full ?? []) {
      if (!skus.length) continue;
      const ok = skus.includes(v.supplier_sku);
      const collapsed = v.id.endsWith(':default');
      if (!ok || (collapsed && v.supplier_sku !== card.options.default_sku))
        out.push({ catalog: f, card: cid, variant: v.id, supplier_sku: v.supplier_sku, card_supplier_sku: card.supplier?.sku, default_sku: card.options.default_sku, is_option_sku: ok, collapsed, active: v.active, sold: p.availability.status === 'available' && p.price_agorot !== null });
    }
  }
}
writeFileSync(OUTF, JSON.stringify(out, null, 1));
console.log(JSON.stringify(out, null, 1));
