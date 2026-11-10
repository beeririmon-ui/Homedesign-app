/**
 * qa-agent, 2026-11-10 (S6-S7): POST /api/checkout attacked directly, on QA's private server.
 *  empty cart; forged shipping; extra total fields; a second checkout of an ordered cart; two checkouts of one cart at
 *  the same moment (a double click); a PUT into an ordered cart; the order view of each order (lines, total, ids)
 *   QA_BASE=http://127.0.0.1:8799 node api-checkout.mjs out.json
 */
import { writeFileSync } from 'node:fs';
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const res = { base: BASE, run_at: new Date().toISOString() };
let ip = 20;
async function call(method, path, body, key) {
  for (let i = 0; i < 8; i++) {
    const r = await fetch(BASE + path, { method, headers: { 'content-type': 'application/json', 'cf-connecting-ip': key ?? `10.9.8.${ip}` }, body: body === undefined ? undefined : JSON.stringify(body) });
    const text = await r.text();
    if (r.status === 429) { await sleep(12000); continue; }
    let json = null;
    try { json = JSON.parse(text); } catch {}
    return { status: r.status, json, text };
  }
  return { status: 429 };
}
const GOOD = 'cushions-washed-cotton-frayed-ws8a6:50x50+rust-orange';
const newCart = async (items = [[GOOD, 2]]) => {
  ip++;
  const id = (await call('POST', '/api/cart', {})).json.id;
  for (const [v, q] of items) await call('PUT', `/api/cart/${id}/items`, { variant_id: v, qty: q });
  return id;
};
const body = (cart_id, extra = {}) => ({
  cart_id,
  customer: { full_name: 'דנה בדיקה', email: 'qa@example.com', phone: '050-1234567' },
  address: { city: 'חיפה', street: 'הרצל', house: '12' },
  shipping_method: 'economy',
  consents: { terms: true, marketing: false },
  ...extra,
});
const co = (cart_id, extra, key) => call('POST', '/api/checkout', body(cart_id, extra), key);
const brief = (r) => ({ status: r.status, error: r.json?.error ?? null, order: r.json?.order_id ?? null });

res.valid_body_sanity = brief(await co(await newCart()));
const empty = await (async () => { ip++; return (await call('POST', '/api/cart', {})).json.id; })();
res.empty_cart = brief(await co(empty));
res.forged_shipping = brief(await co(await newCart(), { shipping_method: 'free' }));
const c1 = await newCart();
const first = await co(c1, { total_agorot: 1, subtotal_agorot: 1, shipping_agorot: 0 });
res.extra_total_fields = brief(first);
if (first.json?.order_id) {
  const v = await call('GET', `/api/orders/${first.json.order_id}?token=${encodeURIComponent(first.json.order_token)}`);
  res.extra_total_fields.order_view = v.json;
}
res.second_checkout_same_cart = brief(await co(c1));
res.put_into_ordered_cart = (await call('PUT', `/api/cart/${c1}/items`, { variant_id: GOOD, qty: 3 })).status;
res.get_ordered_cart = (await call('GET', `/api/cart/${c1}`)).status;
// a double click: two checkouts of one cart in flight together
const c2 = await newCart();
const [a, b] = await Promise.all([co(c2, {}, '10.7.7.1'), co(c2, {}, '10.7.7.2')]);
res.double_submit = { a: brief(a), b: brief(b), orders_created: [a, b].filter((x) => x.status === 201).length };
// five at once
const c3 = await newCart();
const many = await Promise.all([1, 2, 3, 4, 5].map((k) => co(c3, {}, `10.7.6.${k}`)));
res.five_at_once = { statuses: many.map((x) => x.status), orders_created: many.filter((x) => x.status === 201).length, ids: many.map((x) => x.json?.order_id ?? null) };
// the order view without / with a wrong token
if (first.json?.order_id) {
  res.order_no_token = (await call('GET', `/api/orders/${first.json.order_id}`)).status;
  res.order_bad_token = (await call('GET', `/api/orders/${first.json.order_id}?token=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)).status;
}
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(res, null, 1));
console.log(JSON.stringify(res, null, 1));
