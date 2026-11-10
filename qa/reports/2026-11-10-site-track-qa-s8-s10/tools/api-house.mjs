/**
 * qa-agent, 2026-11-10 (S8-S10), on the isolated copy of b0a71cd2 served on 127.0.0.1:8799. The warm-modern house at the
 * API, with no browser:
 *  1. every piece of the three sets (B, A, C) through PUT /api/cart/:id/items, as 'set' and as 'unit': the Oatmeal 50×50
 *     must be refused (PRE1/MED1: "המלאי אינו זמין כעת", never sold), every other piece sold; Oatmeal 45×45 as a control
 *  2. set B's sellable pieces to an order: checkout, the mock hosted page (the dummy secret), the order view
 *  3. the order's lines in D1 (read-only SELECT through wrangler d1 execute on the copy's state): the lumbar's supplier SKU
 *     must be CJZT113551675WD (the filled cushion), and no line for the Oatmeal 50×50
 * Its own rate-limit bucket (cf-connecting-ip from TEST-NET-3), so it never eats the e2e suite's.
 *   QA_BASE=http://127.0.0.1:8799 QA_COPY=<copy>/site node api-house.mjs out.json
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join } from 'node:path';

const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const COPY = process.env.QA_COPY;
const out = process.argv[2];
const IP = '203.0.113.81';
const house = JSON.parse(readFileSync(join(COPY, '.generated/house.living-room.warm-modern.json'), 'utf8'));
const H = { 'content-type': 'application/json', 'cf-connecting-ip': IP };
const j = async (method, path, body, extra = {}) => {
  const r = await fetch(BASE + path, { method, headers: { ...H, ...extra }, body: body ? JSON.stringify(body) : undefined, redirect: 'manual' });
  const t = await r.text();
  let b;
  try {
    b = JSON.parse(t);
  } catch {
    b = t.slice(0, 200);
  }
  return { status: r.status, body: b, location: r.headers.get('location') };
};
const res = { base: BASE, run_at: new Date().toISOString(), pieces: [] };

// 1. every piece, as a set and as a unit
const cart = (await j('POST', '/api/cart')).body.id;
const OAT50 = 'cushions-textured-boucle-throw-pillow-7ryhq:50x50+oatmeal';
const OAT45 = 'cushions-textured-boucle-throw-pillow-7ryhq:45x45+oatmeal';
for (const s of house.sets)
  for (const it of s.items) {
    for (const pack of ['set', 'unit']) {
      const r = await j('PUT', `/api/cart/${cart}/items`, { variant_id: it.variant_id, pack, qty: 1 });
      res.pieces.push({ set: s.id, variant_id: it.variant_id, pack, status: r.status, error: r.status >= 400 ? r.body.error : null, in_cart_after: r.status === 200 ? r.body.lines.some((l) => l.variant_id === it.variant_id) : null });
      // leave the cart as it was
      if (r.status === 200) await j('PUT', `/api/cart/${cart}/items`, { variant_id: it.variant_id, pack, qty: 0 });
    }
  }
for (const [label, v] of [['oatmeal 45×45 (control, in stock)', OAT45], ['oatmeal 50×50 qty 2', OAT50]]) {
  const r = await j('PUT', `/api/cart/${cart}/items`, { variant_id: v, pack: 'set', qty: label.includes('qty 2') ? 2 : 1 });
  res.pieces.push({ set: 'control', label, variant_id: v, pack: 'set', status: r.status, error: r.status >= 400 ? r.body.error : null });
  if (r.status === 200) await j('PUT', `/api/cart/${cart}/items`, { variant_id: v, pack: 'set', qty: 0 });
}
res.oatmeal_50_refused = res.pieces.filter((p) => p.variant_id === OAT50).every((p) => p.status >= 400);
res.others_sold_as_set = res.pieces.filter((p) => p.set !== 'control' && p.variant_id !== OAT50 && p.pack === 'set').every((p) => p.status === 200);

// 2. set B's sellable pieces to an order
const B = house.sets.find((s) => s.id === 'B');
const cart2 = (await j('POST', '/api/cart')).body.id;
for (const it of B.items) if (it.variant_id !== OAT50) await j('PUT', `/api/cart/${cart2}/items`, { variant_id: it.variant_id, pack: 'set', qty: 1 });
res.set_b_cart = (await j('GET', `/api/cart/${cart2}`)).body;
const co = await j('POST', '/api/checkout', {
  cart_id: cart2,
  customer: { full_name: 'בדיקת איכות', email: 'qa@example.com', phone: '050-1234567' },
  address: { city: 'חיפה', street: 'הרצל', house: '12' },
  shipping_method: 'economy',
  consents: { terms: true },
});
res.checkout = { status: co.status, order_id: co.body.order_id ?? null, redirect: co.body.redirect_url ?? null, error: co.body.error ?? null };
if (co.status === 200 || co.status === 201) {
  const session = co.body.redirect_url.split('/mock-pay/')[1].replace(/\/.*$/, '');
  const pay = await fetch(`${BASE}/mock-pay/${session}/complete`, { method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded', 'cf-connecting-ip': IP }, body: 'outcome=success', redirect: 'manual' });
  res.mock_pay = { status: pay.status, location: pay.headers.get('location') };
  const ov = await j('GET', `/api/orders/${co.body.order_id}`, undefined, { 'x-order-token': co.body.order_token });
  res.order_view = ov.body;
  // 3. the lines in D1 (read-only)
  const sql = `SELECT line, variant_id, supplier_sku, pack, qty, unit_sell_qty, unit_price_agorot, name_he FROM order_items WHERE order_id = '${co.body.order_id.replace(/'/g, '')}' ORDER BY line`;
  const raw = execFileSync('npx', ['wrangler', 'd1', 'execute', 'DB', '--local', '--persist-to', '../.wrangler-state', '--json', '--command', sql], { cwd: join(COPY, 'api'), encoding: 'utf8' });
  res.d1_order_items = JSON.parse(raw)[0].results;
  const lumbar = res.d1_order_items.find((r) => r.variant_id.startsWith('cushions-linen-look-charcoal'));
  res.lumbar_sku = lumbar?.supplier_sku ?? null;
  res.lumbar_ok = res.lumbar_sku === 'CJZT113551675WD';
  res.oatmeal_50_in_order = res.d1_order_items.some((r) => r.variant_id === OAT50);
}
writeFileSync(out, JSON.stringify(res, null, 1));
console.log(
  JSON.stringify(
    {
      oatmeal_50_refused: res.oatmeal_50_refused,
      oatmeal_50: res.pieces.filter((p) => p.variant_id === OAT50).map((p) => `${p.pack}:${p.status} ${p.error}`),
      control_45: res.pieces.find((p) => p.variant_id === OAT45)?.status,
      others_sold_as_set: res.others_sold_as_set,
      unit_statuses: [...new Set(res.pieces.filter((p) => p.pack === 'unit').map((p) => `${p.status} ${p.error}`))],
      checkout: res.checkout,
      mock_pay: res.mock_pay,
      lumbar_sku: res.lumbar_sku,
      oatmeal_50_in_order: res.oatmeal_50_in_order,
      order_lines: res.order_view?.lines?.map((l) => `${l.name_he} ×${l.qty} ${l.line_total_agorot}`),
    },
    null,
    1,
  ),
);
