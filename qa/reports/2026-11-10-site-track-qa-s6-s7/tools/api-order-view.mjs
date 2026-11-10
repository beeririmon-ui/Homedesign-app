/** qa-agent, 2026-11-10 (S6-S7): a checkout that sends its own totals, then the order view (x-order-token): the total
 * is the server's; nothing in the view names a supplier or a card id. */
import { writeFileSync } from 'node:fs';
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const h = { 'content-type': 'application/json', 'cf-connecting-ip': '10.6.6.6' };
const j = async (m, p, b, extra = {}) => { const r = await fetch(BASE + p, { method: m, headers: { ...h, ...extra }, body: b && JSON.stringify(b) }); return { status: r.status, text: await r.text() }; };
const cart = JSON.parse((await j('POST', '/api/cart', {})).text).id;
await j('PUT', `/api/cart/${cart}/items`, { variant_id: 'cushions-washed-cotton-frayed-ws8a6:50x50+rust-orange', qty: 2 });
await j('PUT', `/api/cart/${cart}/items`, { variant_id: 'framed-art-minimal-geometric-triptych-prints-4ue7k:1+50x70-unframed', pack: 'unit', qty: 1 });
const co = JSON.parse((await j('POST', '/api/checkout', { cart_id: cart, customer: { full_name: 'דנה בדיקה', email: 'qa@example.com', phone: '050-1234567' }, address: { city: 'חיפה', street: 'הרצל', house: '12' }, shipping_method: 'economy', consents: { terms: true }, total_agorot: 1, subtotal_agorot: 1, shipping_agorot: 0 })).text);
const view = await j('GET', `/api/orders/${co.order_id}`, undefined, { 'x-order-token': co.order_token });
const pay = await fetch(co.redirect_url.replace(/^https?:\/\/[^/]+/, BASE)).then(async (r) => ({ status: r.status, text: await r.text() }));
const SUP = /aliexpress|zendrop|cjdropshipping|alibaba|alicdn|(^|[-/"'_.\s])cj([-/"'_.]|$)|supplier|card_id|cost_usd/i;
const res = { order: co.order_id, view_status: view.status, view: JSON.parse(view.text), view_supplier_hit: SUP.exec(view.text)?.[0] ?? null, mock_pay_status: pay.status, mock_pay_supplier_hit: SUP.exec(pay.text)?.[0] ?? null };
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(res, null, 1));
console.log(JSON.stringify(res, null, 1));
