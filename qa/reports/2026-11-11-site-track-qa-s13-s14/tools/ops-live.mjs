/**
 * qa-agent, 2026-11-11 (S13 at a8104956): the operations, live, against the copy's Worker (wrangler dev, its own D1, the
 * queue consumer running), as the shop would run them. Every server console line written during the run is read back
 * from the server's log (QA_SRVLOG, from the byte offset at the start) and searched for the buyer's details.
 *
 *  1  an order with distinct personal details, paid on the mock page; the jobs (supplier, invoice, alert) run by the queue
 *  2  the admin (the local dev token, the stand-in for Access): the order page; the mock supplier: shipped, delivered
 *  3  the customer's order page (API, token): the statuses, the number, the link; no supplier in it
 *  4  refunds: partial with a key, the same key again, the same key twice at once, then the rest; above paid
 *  5  cancel before the supplier (a fresh order, cancel before the queue sends it if it can) and after it (request,
 *     then the mock supplier confirms); the audit log's actors
 *  6  a crash: a malformed supplier link written into the copy's D1 (QA_D1_EXEC), then the customer's order page
 *  7  the JSON Admin API with a cross-site-sendable content type and a foreign Origin (ת34)
 *
 *   QA_BASE=http://127.0.0.1:8799 QA_SRVLOG=<srv log> QA_TOKEN=<dev token> QA_OUT=<qa folder> QA_D1_EXEC=<script> node ops-live.mjs
 */
import { readFileSync, statSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join } from 'node:path';

const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const LOG = process.env.QA_SRVLOG;
const TOKEN = process.env.QA_TOKEN;
const OUT = process.env.QA_OUT;
const D1 = process.env.QA_D1_EXEC;
const start = statSync(LOG).size;
const PII = { full_name: 'אורנית בדיקוביץ־לייב', email: 'ornit.live1314@example.invalid', phone: '054-6173829', city: 'גבעת־בדיקה־חיה', street: 'שביל־הבודקים', house: '19', apartment: '4', zip: '7766554', notes: 'הדלת עם הפעמון הירוק' };
const NEEDLES = [PII.full_name, 'בדיקוביץ', 'אורנית', PII.email, 'ornit.live', PII.phone, '6173829', '0546173829', PII.city, PII.street, PII.notes, PII.zip];
const res = { base: BASE, steps: {} };
let ip = 50;
async function call(path, init = {}, h = {}) {
  const r = await fetch(`${BASE}${path}`, { ...init, redirect: 'manual', headers: { 'cf-connecting-ip': `203.0.113.${ip++ % 200}`, ...(init.body && typeof init.body === 'string' ? { 'content-type': 'application/json' } : {}), ...h, ...(init.headers ?? {}) } });
  const text = await r.text();
  let body = text;
  try {
    body = JSON.parse(text);
  } catch {
    /* text */
  }
  return { status: r.status, body, location: r.headers.get('location') };
}
const admin = { 'x-hd-dev-admin': TOKEN };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const catalog = JSON.parse(readFileSync(join(process.env.QA_COPY, '.generated/catalog.public.json'), 'utf8'));
const prod = catalog.products.find((p) => p.price_agorot && p.availability.status === 'available' && p.slot === 'vase') ?? catalog.products.find((p) => p.price_agorot && p.availability.status === 'available');

async function order() {
  const cart = (await call('/api/cart', { method: 'POST' })).body.id;
  await call(`/api/cart/${cart}/items`, { method: 'PUT', body: JSON.stringify({ variant_id: prod.variants[0].id, qty: 2 }) });
  const c = await call('/api/checkout', {
    method: 'POST',
    body: JSON.stringify({ cart_id: cart, customer: { full_name: PII.full_name, email: PII.email, phone: PII.phone }, address: { city: PII.city, street: PII.street, house: PII.house, apartment: PII.apartment, zip: PII.zip, notes: PII.notes }, shipping_method: 'express', consents: { terms: true, marketing: false } }),
  });
  const session = new URL(c.body.redirect_url).pathname.split('/').pop();
  const pay = await fetch(`${BASE}/mock-pay/${session}/complete`, { method: 'POST', redirect: 'manual', headers: { 'cf-connecting-ip': '203.0.113.9' }, body: new URLSearchParams({ outcome: 'success' }) });
  return { id: c.body.order_id, token: c.body.order_token, paid: pay.status };
}
const view = async (o) => (await call(`/api/orders/${o.id}`, {}, { 'x-order-token': o.token })).body;
async function waitFor(o, pred, ms = 30000) {
  const t = Date.now();
  let v;
  while (Date.now() - t < ms) {
    v = await call(`/api/admin/orders/${o.id}`, {}, admin);
    if (pred(v.body)) return v.body;
    await sleep(700);
  }
  return v?.body;
}

// 1–3
const o = await order();
const d1 = await waitFor(o, (b) => b?.order?.status === 'sent_to_supplier' && (b?.invoice?.state === 'issued' || (b?.audit ?? []).some((a) => a.action === 'order.invoiced')));
const seen = [ (await view(o)).status_he ];
const ms1 = await call(`/api/admin/orders/${o.id}/mock-supplier`, { method: 'POST', body: JSON.stringify({ event: 'shipped' }) }, admin);
const vShip = await view(o);
seen.push(vShip.status_he);
await call(`/api/admin/orders/${o.id}/mock-supplier`, { method: 'POST', body: JSON.stringify({ event: 'delivered' }) }, admin);
const vDel = await view(o);
seen.push(vDel.status_he);
res.steps.flow = { order: o.id, order_token_local_copy: o.token, canceled_order: null, total: vDel.total_agorot, admin_status_after_jobs: d1?.order?.status, mock_shipped: ms1.status, customer_statuses: seen, shipments: vDel.shipments, view_keys: Object.keys(vDel), supplier_word: /\b(cj|mock|aliexpress|zendrop|MOCK-)\b/i.exec(JSON.stringify(vDel))?.[0] ?? null, no_token: (await call(`/api/orders/${o.id}`)).status };
console.log('flow', JSON.stringify(res.steps.flow));

// 4 refunds
const total = vDel.total_agorot;
const k1 = `qa_live_${Date.now()}`;
const r1 = await call(`/api/admin/orders/${o.id}/refund`, { method: 'POST', body: JSON.stringify({ amount_agorot: 1000, reason: 'החזר חלקי לבדיקה', key: k1 }) }, admin);
const r1b = await call(`/api/admin/orders/${o.id}/refund`, { method: 'POST', body: JSON.stringify({ amount_agorot: 1000, reason: 'החזר חלקי לבדיקה', key: k1 }) }, admin);
const k2 = `qa_live2_${Date.now()}`;
const conc = await Promise.all(Array.from({ length: 5 }, () => call(`/api/admin/orders/${o.id}/refund`, { method: 'POST', body: JSON.stringify({ amount_agorot: 700, reason: 'במקביל', key: k2 }) }, admin)));
const over = await call(`/api/admin/orders/${o.id}/refund`, { method: 'POST', body: JSON.stringify({ amount_agorot: total, reason: 'מעל ששולם', key: `qa_over_${Date.now()}` }) }, admin);
const rest = await call(`/api/admin/orders/${o.id}/refund`, { method: 'POST', body: JSON.stringify({ amount_agorot: 'rest', reason: 'היתרה', key: `qa_rest_${Date.now()}` }) }, admin);
await sleep(4000);
const det = (await call(`/api/admin/orders/${o.id}`, {}, admin)).body;
res.steps.refunds = {
  total,
  partial: r1.status,
  same_key_again: [r1b.status, r1b.body?.duplicate],
  same_key_x5: conc.map((c) => `${c.status}${c.body?.duplicate ? '/dup' : ''}`),
  over: [over.status, over.body?.error],
  rest: [rest.status, rest.body?.amount_agorot],
  rows: (det.refunds ?? []).map((r) => `${r.amount_agorot}:${r.state}:${r.credit_state ?? ''}`),
  sum_refunded: (det.refunds ?? []).filter((r) => r.state === 'refunded').reduce((s, r) => s + r.amount_agorot, 0),
  order_status: det.order?.status,
  customer_refunded: (await view(o)).refunded_agorot,
};
console.log('refunds', JSON.stringify(res.steps.refunds));

// 5 cancellations: before the supplier (as soon as it is paid), and after it
const c1 = await order();
const cancel1 = await call(`/api/admin/orders/${c1.id}/cancel`, { method: 'POST', body: JSON.stringify({ reason: 'הלקוח ביקש לבטל' }) }, admin);
const c2 = await order();
await waitFor(c2, (b) => b?.order?.status === 'sent_to_supplier');
const cancel2 = await call(`/api/admin/orders/${c2.id}/cancel`, { method: 'POST', body: JSON.stringify({ reason: 'הלקוח ביקש לבטל' }) }, admin);
const c2wait = (await view(c2)).status_he;
const cancel2b = await call(`/api/admin/orders/${c2.id}/cancel`, { method: 'POST', body: JSON.stringify({ reason: 'שוב' }) }, admin);
const conf = await call(`/api/admin/orders/${c2.id}/mock-supplier`, { method: 'POST', body: JSON.stringify({ event: 'cancel_confirmed' }) }, admin);
await sleep(1500);
const a1 = (await call(`/api/admin/orders/${c1.id}`, {}, admin)).body;
const a2 = (await call(`/api/admin/orders/${c2.id}`, {}, admin)).body;
const acts = (d) => (d.audit ?? []).map((a) => `${a.actor}:${a.action}`);
res.steps.flow.canceled_order = { id: c2.id, token: c2.token };
res.steps.cancel = {
  before: { cancel: [cancel1.status, cancel1.body?.outcome, cancel1.body?.stage], status: a1.order?.status, refunds: (a1.refunds ?? []).map((r) => `${r.amount_agorot}:${r.state}`), audit: acts(a1), customer: (await view(c1)).status_he },
  after: { cancel: [cancel2.status, cancel2.body?.outcome, cancel2.body?.stage], customer_while_waiting: c2wait, again: [cancel2b.status, cancel2b.body?.outcome], confirm: conf.status, status: a2.order?.status, refunds: (a2.refunds ?? []).map((r) => `${r.amount_agorot}:${r.state}`), audit: acts(a2), customer: (await view(c2)).status_he },
};
console.log('cancel', JSON.stringify(res.steps.cancel));

// 6 a crash: a malformed supplier link in the copy's D1, then the customer's order page
if (D1) {
  execFileSync(D1, [`UPDATE supplier_shipments SET tracking_url = 'https://parcelsapp.com/he/tracking/%E0%A4%A' WHERE order_id = '${o.id}'`], { stdio: 'ignore' });
  const crash = await call(`/api/orders/${o.id}`, {}, { 'x-order-token': o.token });
  res.steps.crash = { status: crash.status, body: crash.body };
  console.log('crash', JSON.stringify(res.steps.crash));
}

// 7 the JSON Admin API, a CORS-safelisted content type, a foreign Origin
const c3 = await order();
const csrf = await call(`/api/admin/orders/${c3.id}/cancel`, { method: 'POST', body: JSON.stringify({ reason: 'csrf probe' }) }, { ...admin, 'content-type': 'text/plain; charset=application/json', origin: 'https://evil.example', 'sec-fetch-site': 'cross-site' });
const form = await call(`/admin/orders/${c3.id}/cancel`, { method: 'POST', body: new URLSearchParams({ reason: 'csrf probe form' }) }, { ...admin, origin: 'https://evil.example' });
res.steps.csrf = { json_api_text_plain_foreign_origin: [csrf.status, csrf.body?.outcome ?? csrf.body?.error], screen_form_foreign_origin: [form.status, form.location], order_after: (await call(`/api/admin/orders/${c3.id}`, {}, admin)).body?.order?.status };
console.log('csrf', JSON.stringify(res.steps.csrf));

// the server's console lines written during the run
await sleep(3000);
const all = readFileSync(LOG).subarray(start).toString('utf8');
const lines = all.split('\n').filter((l) => l.trim());
const structured = lines.filter((l) => /\{.*(level|event)/.test(l) || /level:|event:/.test(l));
const leaks = NEEDLES.filter((n) => all.includes(n)).map((n) => ({ needle: n, lines: lines.filter((l) => l.includes(n)).map((l) => l.slice(0, 200)).slice(0, 3) }));
res.log = { lines: lines.length, structured_rows: structured.length, leaks, events: [...new Set([...all.matchAll(/event: '([^']+)'|"event":"([^"]+)"/g)].map((m) => m[1] ?? m[2]))], sample: structured.slice(0, 6).map((l) => l.slice(0, 220)) };
console.log('log', JSON.stringify({ lines: res.log.lines, structured: res.log.structured_rows, events: res.log.events, leaks: leaks.map((l) => l.needle) }));
writeFileSync(join(OUT, 'data/ops-live.json'), JSON.stringify(res, null, 1));
writeFileSync(join(OUT, 'data/ops-live-server-log.txt'), all);
