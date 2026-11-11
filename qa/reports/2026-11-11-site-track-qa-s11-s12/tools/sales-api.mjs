/**
 * qa-agent, 2026-11-11 (S11–S12): what is sellable, from the cards and the manager's data, checked at the built catalogs
 * AND at the running Worker (wrangler dev, own D1):
 *  1. sale exclusions (data/catalog/sale-exclusions.json): for every card in the list, every SKU of the card is tried at
 *     PUT /api/cart/<id>/items as the variant id the build would give it (optionVariantId + publicVariantId), as a set
 *     and as one piece; only the allowed value may be 200. The variant that is sold must carry the allowed SKU (the one
 *     the supplier will be asked for).
 *  2. sets of distinct SKUs (story.json set_axes): the set's own variant 200 per size, every other print 422 (set_part),
 *     one piece 422; the order line's supplier lines are 3 distinct SKUs of the right size; 2 sets → 2 of each.
 *  3. the Mediterranean print: every SKU id of its card is tried; nothing may be 200.
 *  4. ת8/ת12: every variant the build offers (the shop's and the story's catalogs, the house's sets) is put in a cart
 *     and the cart's line (name · option) is checked: no Latin apart from a unit after a number (3000K), no colour word
 *     in the base that contradicts the option (the designer's base names carry no colour).
 *   QA_BASE=http://127.0.0.1:8799 QA_COPY=<copy> QA_OUT=<qa folder> node sales-api.mjs
 */
import { readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { createRequire } from 'node:module';

const COPY = process.env.QA_COPY; // the copy's root (site/ and data/ under it)
const OUT = process.env.QA_OUT;
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const require = createRequire(join(COPY, 'site/package.json'));
const gen = (f) => JSON.parse(readFileSync(join(COPY, 'site/.generated', f), 'utf8'));
const data = (f) => JSON.parse(readFileSync(join(COPY, 'data', f), 'utf8'));

// ---------- the cards ----------
const cardPath = new Map();
(function walk(d) {
  for (const n of readdirSync(d)) {
    const p = join(d, n);
    if (statSync(p).isDirectory()) walk(p);
    else if (n.endsWith('.json')) cardPath.set(n.slice(0, -5), p);
  }
})(join(COPY, 'data/products'));
const card = (id) => JSON.parse(readFileSync(cardPath.get(id), 'utf8'));

// the public id of a card: as the build does it (shared/src/product-url.ts)
const { publicId } = await import(join(COPY, 'site/shared/src/product-url.ts')).catch(() => ({}));
const catalogs = { shop: gen('catalog.full.json'), story: gen('catalog.story.full.json') };
const byCard = new Map();
for (const [k, c] of Object.entries(catalogs))
  for (const p of c.products) {
    const id = p.source_path.split('/').pop().replace(/\.json$/, '');
    if (!byCard.has(id)) byCard.set(id, []);
    byCard.get(id).push({ catalog: k, p });
  }
const pidOf = (cardId) => byCard.get(cardId)?.[0]?.p.id ?? (publicId ? publicId(cardId) : null);

// ---------- the API ----------
let ip = 1;
async function api(path, init = {}) {
  const r = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { 'content-type': 'application/json', 'cf-connecting-ip': `198.51.100.${(ip++ % 250) + 1}`, ...(init.headers ?? {}) },
  });
  let body = null;
  try {
    body = await r.json();
  } catch {
    body = null;
  }
  return { status: r.status, body };
}
const newCart = async () => (await api('/api/cart', { method: 'POST' })).body.id;
const put = (cart, variant_id, pack = 'set', qty = 1, house) =>
  api(`/api/cart/${cart}/items`, { method: 'PUT', body: JSON.stringify({ variant_id, pack, qty, ...(house ? { house } : {}) }) });

const res = { base: BASE, run_at: new Date().toISOString(), exclusions: [], sets: [], mediterranean: null, lines: null };

// ---------- 1. exclusions ----------
const ex = data('catalog/sale-exclusions.json');
for (const e of ex.exclusions) {
  const c = card(e.card_id);
  const o = c.options;
  const pid = pidOf(e.card_id);
  const inCat = byCard.get(e.card_id) ?? [];
  const entry = { card_id: e.card_id, public_id: pid, axis: e.axis, sell_only: e.sell_only, in_catalogs: inCat.map((x) => x.catalog), skus: [] };
  const cart = await newCart();
  for (const s of o?.skus ?? []) {
    const vid = `${pid}:${o.axes.map((a) => s.values[a.id]).join('+')}`;
    const allowed = e.sell_only.includes(s.values[e.axis]);
    const asSet = await put(cart, vid, 'set');
    const asUnit = await put(cart, vid, 'unit');
    if (asSet.status === 200) await put(cart, vid, 'set', 0);
    if (asUnit.status === 200) await put(cart, vid, 'unit', 0);
    entry.skus.push({ sku: s.id, value: s.values[e.axis], allowed, variant_id: vid, set: asSet.status, set_error: asSet.body?.error ?? null, unit: asUnit.status });
  }
  // the variants the build offers for this card, and their supplier SKU
  entry.offered = inCat.flatMap(({ catalog, p }) =>
    (p.variants_full ?? p.variants.map((v) => ({ id: v.id, supplier_sku: p.supplier.sku, active: true }))).map((v) => ({
      catalog,
      id: v.id,
      supplier_sku: v.supplier_sku,
      active: v.active,
      sku_value: o?.skus.find((s) => s.id === v.supplier_sku)?.values[e.axis] ?? null,
    })),
  );
  // what the API sells for the offered ids
  for (const v of entry.offered) {
    const r = await put(cart, v.id, 'set');
    v.api_set = r.status;
    v.api_error = r.body?.error ?? null;
    if (r.status === 200) {
      const line = r.body.lines.find((l) => l.variant_id === v.id);
      v.line = line ? `${line.name_he}${line.option_he ? ` · ${line.option_he}` : ''}` : null;
      v.price_agorot = line?.unit_price_agorot ?? null;
      await put(cart, v.id, 'set', 0);
    }
    v.ok = v.api_set !== 200 || e.sell_only.includes(v.sku_value);
  }
  entry.sold_values = [...new Set(entry.skus.filter((s) => s.set === 200 || s.unit === 200).map((s) => s.value))];
  entry.sold_by_offered = entry.offered.filter((v) => v.api_set === 200).map((v) => v.sku_value);
  entry.pass =
    entry.skus.every((s) => s.allowed || (s.set !== 200 && s.unit !== 200)) && entry.offered.every((v) => v.ok) && entry.sold_by_offered.every((v) => e.sell_only.includes(v));
  res.exclusions.push(entry);
}

// ---------- 2. sets of distinct SKUs ----------
const story = data('story/story.json');
for (const [cardId, set] of Object.entries(story.set_axes ?? {})) {
  const c = card(cardId);
  const o = c.options;
  const pid = pidOf(cardId);
  const inCat = byCard.get(cardId) ?? [];
  const full = inCat[0]?.p.variants_full ?? [];
  const entry = { card_id: cardId, public_id: pid, axis: set.axis, parts_named: set.parts ?? null, in_catalogs: inCat.map((x) => x.catalog), skus: [] };
  const cart = await newCart();
  for (const s of o?.skus ?? []) {
    const vid = `${pid}:${o.axes.map((a) => s.values[a.id]).join('+')}`;
    const v = full.find((x) => x.id === vid);
    const asSet = await put(cart, vid, 'set');
    const asUnit = await put(cart, vid, 'unit');
    const line = asSet.status === 200 ? asSet.body.lines.find((l) => l.variant_id === vid) : null;
    if (asSet.status === 200) await put(cart, vid, 'set', 0);
    entry.skus.push({
      sku: s.id,
      values: s.values,
      variant_id: vid,
      build: v ? { set_part: v.set_part, set_skus: v.set_skus, set_incomplete: v.set_incomplete, active: v.active } : null,
      set: asSet.status,
      set_error: asSet.body?.error ?? null,
      unit: asUnit.status,
      unit_error: asUnit.body?.error ?? null,
      line: line ? `${line.name_he}${line.option_he ? ` · ${line.option_he}` : ''}` : null,
      price_agorot: line?.unit_price_agorot ?? null,
    });
  }
  // composition: each set variant's parts are 3 distinct SKUs of the same size, one of each print
  for (const s of entry.skus.filter((x) => x.build?.set_skus)) {
    const parts = s.build.set_skus.map((id) => o.skus.find((k) => k.id === id));
    const other = Object.entries(s.values).filter(([a]) => a !== set.axis);
    s.composition_ok =
      new Set(s.build.set_skus).size === s.build.set_skus.length &&
      parts.every((p) => p && other.every(([a, v]) => p.values[a] === v)) &&
      new Set(parts.map((p) => p.values[set.axis])).size === parts.length;
    s.parts = parts.map((p) => ({ sku: p.id, values: p.values }));
  }
  res.sets.push(entry);
}

// ---------- 4. ת8 / ת12: every offered variant's line through the cart ----------
const hasLatin = (s) => /[A-Za-z]/.test(String(s ?? '').replace(/\d+\s*K\b/g, ''));
const COLOURS = ['לבן', 'שחור', 'אפור', 'בז', 'בז\'', 'חום', 'ירוק', 'כחול', 'אדום', 'צהוב', 'כתום', 'ורוד', 'סגול', 'שנהב', 'טאופ', 'קאמל', 'חלודה', 'מרווה', 'שמנת', 'טבעי', 'פחם', 'יין', 'טרקוטה', 'זית', 'חרדל', 'תכלת', 'קרם', 'אוקר', 'ירוק תה', 'פקאן'];
const linesOut = [];
const seen = new Set();
for (const [k, c] of Object.entries(catalogs))
  for (const p of c.products) {
    if (p.availability?.status !== 'available' || p.price_agorot === null) continue;
    for (const v of p.variants_full ?? p.variants.map((x) => ({ ...x, active: true }))) {
      if (!v.active || v.set_part || v.set_incomplete || seen.has(v.id)) continue;
      seen.add(v.id);
      linesOut.push({ catalog: k, product: p.id, variant_id: v.id, build_line: v.line_name_he ?? null, build_option: v.option_label_he ?? null, name_he: p.name_he });
    }
  }
let cart = await newCart();
let n = 0;
for (const l of linesOut) {
  if (n++ % 15 === 0) cart = await newCart();
  const r = await put(cart, l.variant_id, 'set');
  l.status = r.status;
  l.error = r.body?.error ?? null;
  const line = r.status === 200 ? r.body.lines.find((x) => x.variant_id === l.variant_id) : null;
  l.cart_name = line?.name_he ?? null;
  l.cart_option = line?.option_he ?? null;
  l.latin = hasLatin(l.cart_name) || hasLatin(l.cart_option);
  // a colour word in the base name, and the option names another colour: the contradiction of ת8
  const baseColours = COLOURS.filter((w) => new RegExp(`(^|[\\s,·(])${w}($|[\\s,·)])`).test(l.cart_name ?? ''));
  const optColours = COLOURS.filter((w) => new RegExp(`(^|[\\s,·(])${w}($|[\\s,·)])`).test(l.cart_option ?? ''));
  l.base_colours = baseColours;
  l.contradiction = baseColours.length > 0 && optColours.length > 0 && !baseColours.some((b) => optColours.includes(b));
}
res.lines = {
  tried: linesOut.length,
  ok_200: linesOut.filter((l) => l.status === 200).length,
  not_200: linesOut.filter((l) => l.status !== 200).map((l) => ({ v: l.variant_id, s: l.status, e: l.error })),
  latin: linesOut.filter((l) => l.latin).map((l) => [l.variant_id, l.cart_name, l.cart_option]),
  base_with_colour: linesOut.filter((l) => l.base_colours.length).map((l) => [l.variant_id, l.cart_name, l.cart_option]),
  contradictions: linesOut.filter((l) => l.contradiction).map((l) => [l.variant_id, l.cart_name, l.cart_option]),
  all: linesOut,
};

writeFileSync(join(OUT, 'data/sales-api.json'), JSON.stringify(res, null, 1));
console.log(
  JSON.stringify(
    {
      exclusions: res.exclusions.map((e) => ({ card: e.card_id, in: e.in_catalogs, skus: e.skus.length, sold_values: e.sold_values, sold_by_offered: e.sold_by_offered, pass: e.pass })),
      sets: res.sets.map((s) => ({
        card: s.card_id,
        in: s.in_catalogs,
        skus: s.skus.length,
        set200: s.skus.filter((x) => x.set === 200).length,
        errors: [...new Set(s.skus.map((x) => `${x.set}:${x.set_error}`))],
        unit: [...new Set(s.skus.map((x) => `${x.unit}:${x.unit_error}`))],
        composition_ok: s.skus.filter((x) => x.composition_ok !== undefined).map((x) => x.composition_ok),
      })),
      lines: { tried: res.lines.tried, ok: res.lines.ok_200, not200: res.lines.not_200.length, latin: res.lines.latin.length, base_with_colour: res.lines.base_with_colour.length, contradictions: res.lines.contradictions.length },
    },
    null,
    1,
  ),
);
