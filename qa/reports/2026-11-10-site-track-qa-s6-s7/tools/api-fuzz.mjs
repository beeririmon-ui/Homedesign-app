/**
 * qa-agent, 2026-11-10 (S6-S7): the cart and checkout API, attacked directly (no browser). QA's private server only.
 *  - PUT /api/cart/:id/items with bad quantities, packs, variants (PRE1, unknown, another product's key, case, spaces,
 *    a card id, too long), bad JSON and types
 *  - every variant the story's "המראה כולו לסל" buttons carry: does the server sell it?
 *  - checkout: an empty cart, a closed (ordered) cart, a forged shipping method, the price from the server only
 *  - public responses scanned for supplier names, card ids and supplier columns
 *   QA_BASE=http://127.0.0.1:8799 node api-fuzz.mjs <dist> out.json
 */
import { readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const DIST = process.argv[2];
const OUT = process.argv[3] ?? '/dev/stdout';
const res = { base: BASE, run_at: new Date().toISOString(), qty: [], variants: [], look_variants: [], checkout: {}, scan: [] };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const SUPPLIER = /aliexpress|zendrop|cjdropshipping|alibaba|alicdn|(^|[-/"'_.\s])cj([-/"'_.]|$)|supplier_(url|name|sku)|name_supplier|source_path|card_id|cost_usd|landed_|no_loss/i;
async function call(method, path, body, raw) {
  for (let i = 0; i < 6; i++) {
    const r = await fetch(BASE + path, { method, headers: { 'content-type': 'application/json', 'cf-connecting-ip': '10.9.9.9' }, body: raw ?? (body === undefined ? undefined : JSON.stringify(body)) });
    const text = await r.text();
    if (r.status === 429) {
      await sleep(15000);
      continue;
    }
    let json = null;
    try {
      json = JSON.parse(text);
    } catch {}
    const hit = SUPPLIER.exec(text);
    res.scan.push({ method, path: path.replace(/cart\/[^/]+/, 'cart/:id'), status: r.status, supplier_or_internal: hit ? text.slice(Math.max(0, hit.index - 40), hit.index + 40) : null });
    return { status: r.status, json, text };
  }
  return { status: 429, json: null, text: '' };
}
const newCart = async () => (await call('POST', '/api/cart', {})).json.id;
const put = (id, b, raw) => call('PUT', `/api/cart/${id}/items`, b, raw);

const GOOD = 'cushions-washed-cotton-frayed-ws8a6:50x50+rust-orange';
const cart = await newCart();
// sanity: the good variant
const ok = await put(cart, { variant_id: GOOD, qty: 1 });
res.good_variant = { status: ok.status, line: ok.json?.lines?.[0] ?? null, error: ok.json?.error ?? null };
// quantities (raw JSON so -0, 1e1, 1e400 and friends reach the server as written)
for (const q of ['-2', '2.5', '"3"', '21', '999', '-0', '0', '1e1', '2e1', '2.0', '20.0000000000000001', '1e400', '9007199254740993', '-1e-9', 'null', 'true', '[]', '{}', '"1"', '""', 'NaN']) {
  const r = await put(cart, null, `{"variant_id":"${GOOD}","qty":${q}}`);
  const c = await call('GET', `/api/cart/${cart}`);
  res.qty.push({ qty: q, status: r.status, error: r.json?.error?.code ?? r.json?.error ?? null, cart_qty_after: c.json?.lines?.find((l) => l.variant_id === GOOD)?.qty ?? 0 });
  await put(cart, { variant_id: GOOD, qty: 1 });
}
// variants and packs
const tri = 'framed-art-minimal-geometric-triptych-prints-4ue7k:1+50x70-unframed';
for (const [label, body] of [
  ['PRE1 rug (not sold)', { variant_id: 'rug-braided-wool-natural-jzzjv:200x300+square', qty: 1 }],
  ['PRE1 pouf (not sold)', { variant_id: 'pouf-cotton-knit-ball-cover-mlo5s:original-cotton-color', qty: 1 }],
  ['missing variant', { variant_id: 'no-such-product-abcde:default', qty: 1 }],
  ['product id without a key', { variant_id: 'cushions-washed-cotton-frayed-ws8a6', qty: 1 }],
  ["another product's key", { variant_id: 'cushions-washed-cotton-frayed-ws8a6:200x300+square', qty: 1 }],
  ['upper case', { variant_id: GOOD.toUpperCase(), qty: 1 }],
  ['trailing space', { variant_id: `${GOOD} `, qty: 1 }],
  ['the old card id', { variant_id: 'cushions-cj-washed-cotton-frayed:50x50+rust-orange', qty: 1 }],
  ['SQL quote', { variant_id: "x' OR '1'='1", qty: 1 }],
  ['161 chars', { variant_id: 'a'.repeat(161), qty: 1 }],
  ['empty', { variant_id: '', qty: 1 }],
  ['pack unit on a single product', { variant_id: GOOD, pack: 'unit', qty: 1 }],
  ['pack bogus', { variant_id: GOOD, pack: 'pair', qty: 1 }],
  ['triptych as a set', { variant_id: tri, pack: 'set', qty: 1 }],
  ['triptych as a single print (SET1: set only?)', { variant_id: tri, pack: 'unit', qty: 1 }],
  ['extra price field', { variant_id: GOOD, qty: 1, price_agorot: 1, unit_price_agorot: 1 }],
]) {
  const c2 = await newCart();
  const r = await put(c2, body);
  const c = await call('GET', `/api/cart/${c2}`);
  res.variants.push({ case: label, status: r.status, error: r.json?.error?.code ?? r.json?.error ?? null, lines_after: (c.json?.lines ?? []).map((l) => `${l.variant_id} ${l.pack} x${l.qty} ${l.line_total_agorot}`) });
}
// bad JSON and an unknown cart
res.bad_json = (await put(cart, null, '{"variant_id":')).status;
res.unknown_cart = (await call('PUT', '/api/cart/does-not-exist-000000000000/items', { variant_id: GOOD, qty: 1 })).status;
// every variant the story's look buttons carry
const walk = (d, f) => { for (const n of readdirSync(d)) { const p = join(d, n); statSync(p).isDirectory() ? walk(p, f) : f(p); } };
const looks = [];
walk(join(DIST, 'story'), (p) => {
  if (!p.endsWith('index.html')) return;
  const t = readFileSync(p, 'utf8');
  for (const m of t.matchAll(/data-variants="([^"]+)"/g)) looks.push({ page: p.replace(DIST, ''), variants: m[1].split(' ') });
});
for (const l of looks) {
  const c3 = await newCart();
  for (const v of l.variants) {
    const [vid, n] = v.split('*');
    const r = await put(c3, { variant_id: vid, qty: Number(n ?? 1) });
    res.look_variants.push({ page: l.page, variant: v, status: r.status, error: r.json?.error?.code ?? null });
  }
}
// checkout
const customer = { full_name: 'דנה בדיקה', email: 'qa@example.com', phone: '0501234567', city: 'חיפה', street: 'הרצל', house: '12' };
const empty = await newCart();
const co = (cart_id, extra = {}) => call('POST', '/api/checkout', { cart_id, customer, shipping_method: 'economy', consents: { terms: true, marketing: false }, ...extra });
res.checkout.empty_cart = (await co(empty)).status;
const c4 = await newCart();
await put(c4, { variant_id: GOOD, qty: 2 });
res.checkout.forged_shipping = (await co(c4, { shipping_method: 'free' })).status;
res.checkout.forged_total_field = await co(c4, { total_agorot: 1, shipping_agorot: 0 }).then((r) => ({ status: r.status, keys: r.json ? Object.keys(r.json) : null }));
res.checkout.second_on_same_cart = await co(c4).then((r) => ({ status: r.status, error: r.json?.error?.code ?? r.json?.error ?? null }));
res.checkout.cart_after = await call('GET', `/api/cart/${c4}`).then((r) => r.status);
res.checkout.put_after_order = await put(c4, { variant_id: GOOD, qty: 1 }).then((r) => r.status);
// admin without credentials
for (const p of ['/api/admin/overview', '/api/admin/products', '/api/admin/orders', '/api/admin/economics']) res.scan.push({ method: 'GET', path: p, status: (await fetch(BASE + p)).status, supplier_or_internal: 'admin: status only' });
// other public reads
await call('GET', '/api/health');
await call('GET', '/api/catalog/rooms/living-room');
await call('GET', `/api/catalog/prices?ids=${encodeURIComponent('cushions-washed-cotton-frayed-ws8a6,rug-braided-wool-natural-jzzjv,framed-art-minimal-geometric-triptych-prints-4ue7k')}`);
await call('GET', '/api/catalog/prices?ids=cushions-cj-washed-cotton-frayed');
writeFileSync(OUT, JSON.stringify(res, null, 1));
console.log(JSON.stringify({ good: res.good_variant, qty: res.qty, variants: res.variants, bad_json: res.bad_json, unknown_cart: res.unknown_cart, look_refused: res.look_variants.filter((x) => x.status !== 200), looks: res.look_variants.length, checkout: res.checkout, scan_hits: res.scan.filter((s) => s.supplier_or_internal && !s.supplier_or_internal.startsWith('admin')), admin: res.scan.filter((s) => s.path.includes('admin')).map((s) => `${s.path} ${s.status}`) }, null, 1));
