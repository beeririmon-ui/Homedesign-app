/** S11 (QA S6–S7 ת9 and the manager's sale decisions): every product sold as more than one piece, and whether a single
 * piece is offered; every set of distinct SKUs and its parts; every variant not offered. From the build's full catalogs.
 *   node qa/reports/2026-11-07-site-track/s11/tools/sales-audit.mjs > qa/reports/2026-11-07-site-track/s11/sales-audit.json */
import { readFileSync } from 'node:fs';
const G = new URL('../../../../../site/.generated/', import.meta.url);
const read = (f) => JSON.parse(readFileSync(new URL(f, G), 'utf8'));
const out = { sets_of_pieces: [], sets_of_distinct_skus: [], not_offered: [] };
const seen = new Set();
for (const f of ['catalog.full.json', 'catalog.story.full.json']) {
  for (const p of read(f).products) {
    if (seen.has(p.card_id)) continue;
    seen.add(p.card_id);
    const parts = (p.variants_full ?? []).filter((v) => v.set_part);
    if (parts.length)
      out.sets_of_distinct_skus.push({
        card: p.card_id,
        sell_qty: p.sell_qty,
        single_piece_offered: !!p.pack,
        the_set: (p.variants_full ?? []).filter((v) => !v.set_part && v.active).map((v) => v.id),
        parts_never_sold_alone: parts.map((v) => v.id),
      });
    else if (p.sell_qty > 1) out.sets_of_pieces.push({ card: p.card_id, sell_qty: p.sell_qty, single_piece_offered: !!p.pack, unit_price_agorot: p.pack?.unit_price_agorot ?? null });
    for (const v of p.variants_full ?? []) if (v.sale_excluded) out.not_offered.push({ card: p.card_id, variant: v.id, why: v.sale_excluded.slice(0, 90) });
  }
  for (const h of read(f).hidden) seen.add(h.id);
}
// the manager's exclusions: what the build sells of each card (a card left with one SKU sells it as its one variant)
const ex = JSON.parse(readFileSync(new URL('../../../../../data/catalog/sale-exclusions.json', import.meta.url), 'utf8')).exclusions;
out.exclusions = ex.map((e) => {
  const sold = [];
  let hidden = null;
  for (const f of ['catalog.full.json', 'catalog.story.full.json']) {
    const c = read(f);
    const p = c.products.find((x) => x.card_id === e.card_id);
    if (p) sold.push(...(p.variants_full ?? []).filter((v) => v.active && !v.sale_excluded).map((v) => `${f.replace('.full.json', '')}: ${v.id} · ${v.line_name_he}${v.option_label_he ? ` · ${v.option_label_he}` : ''}`));
    else hidden ??= c.hidden.find((h) => h.id === e.card_id)?.reason ?? null;
  }
  return { card: e.card_id, axis: e.axis, sell_only: e.sell_only, sold: [...new Set(sold)], hidden_today: sold.length ? null : hidden };
});
console.log(JSON.stringify(out, null, 1));
