/**
 * QA S20, ת57, on a live server (wrangler dev of a copy, its own D1): the waiting list refuses and stores nothing; a
 * checkout that says yes to marketing records no consent, and the order goes on (paid through the mock payment page).
 * The D1 is read with tools/d1-exec.sh (the copy's own state). No network beyond 127.0.0.1.
 *   node api-t57.mjs --base=http://127.0.0.1:8820 --copy=<copy>/site --label=flag [--want-waitlist=409] [--want-consent=0] --out=<json>
 */
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const arg = (n, d) => process.argv.find((a) => a.startsWith(`--${n}=`))?.slice(n.length + 3) ?? d;
const BASE = arg('base');
const COPY = arg('copy');
const LABEL = arg('label', '');
const WANT_W = Number(arg('want-waitlist', '409'));
const WANT_C = Number(arg('want-consent', '0'));
const OUT = arg('out');
const TOOLS = dirname(fileURLToPath(import.meta.url));
const d1 = (sql) => JSON.parse(execFileSync('bash', [join(TOOLS, 'd1-exec.sh'), sql], { env: { ...process.env, QA_COPY: COPY }, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }))[0].results;
const rows = [];
const check = (id, what, ok, detail) => {
  rows.push({ id, what, ok, detail });
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${id} ${what}  | ${typeof detail === 'string' ? detail : JSON.stringify(detail)}`);
};
const ip = (n) => ({ 'cf-connecting-ip': `10.57.${LABEL.length}.${n}` });
const post = (path, body, headers = {}, raw = false) =>
  fetch(BASE + path, { method: 'POST', headers: { ...(raw ? {} : { 'content-type': 'application/json' }), ...headers }, body: raw ? body : JSON.stringify(body) });

const catalog = JSON.parse(readFileSync(join(COPY, '.generated/catalog.public.json'), 'utf8'));
const held = catalog.products.find((p) => p.availability.status !== 'available');
const sold = catalog.products.find((p) => p.price_agorot && p.availability.status === 'available');
console.log(`${LABEL}: ${BASE}; a product on hold: ${held.id}; one for sale: ${sold.id}`);

// ---------- the waiting list ----------
const before = d1('SELECT COUNT(*) AS n FROM waitlist')[0].n;
const cases = [
  ['W1', 'a product on hold', post('/api/waitlist', { email: 'qa57@example.com', product_id: held.id }, ip(1))],
  ['W2', 'a room and a slot', post('/api/waitlist', { email: 'qa57@example.com', room: 'living-room', slot: held.slot }, ip(2))],
  ['W3', 'malformed JSON (refused before the body is read)', post('/api/waitlist', '{"email": "qa57@', { 'content-type': 'application/json', ...ip(3) }, true)],
  ['W4', 'text/plain', post('/api/waitlist', 'email=qa57@example.com', { 'content-type': 'text/plain', ...ip(4) }, true)],
  ['W5', 'an empty body', post('/api/waitlist', '', { ...ip(5) }, true)],
  ['W6', 'a trailing slash', post('/api/waitlist/', { email: 'qa57@example.com', product_id: held.id }, ip(6))],
];
for (const [id, what, p] of cases) {
  const r = await p;
  const b = await r.text();
  let j = null;
  try { j = JSON.parse(b); } catch {}
  const ok = id === 'W6' ? r.status === WANT_W || r.status === 404 : r.status === WANT_W && (WANT_W !== 409 || j?.error === 'waitlist_closed');
  check(id, `POST /api/waitlist, ${what}`, ok, `${r.status} ${b.slice(0, 140)}`);
}
// 40 in a row from one address: all refused the same way, never a rate limit (the refusal comes first)
const burst = await Promise.all(Array.from({ length: 40 }, () => post('/api/waitlist', { email: 'qa57b@example.com', product_id: held.id }, ip(7)).then((r) => r.status)));
const tally = burst.reduce((m, s) => ((m[s] = (m[s] ?? 0) + 1), m), {});
check('W7', '40 requests from one address', WANT_W === 409 ? tally[409] === 40 : true, tally);
const g = await fetch(BASE + '/api/waitlist');
check('W8', 'GET /api/waitlist (no reader)', g.status === 404 || g.status === 405, `${g.status}`);
const after = d1('SELECT COUNT(*) AS n FROM waitlist')[0].n;
const total = d1('SELECT COUNT(*) AS n, COUNT(DISTINCT email) AS e FROM waitlist')[0];
check('W9', 'rows in waitlist, before and after', WANT_W === 409 ? after === before : after > before, { before, after, table: total });

// ---------- the checkout ----------
async function checkout(n, marketing) {
  const h = ip(20 + n);
  const cart = await (await post('/api/cart', {}, h)).json();
  const put = await fetch(`${BASE}/api/cart/${cart.id}/items`, { method: 'PUT', headers: { 'content-type': 'application/json', ...h }, body: JSON.stringify({ variant_id: sold.variants[0].id, qty: 1 }) });
  if (put.status !== 200) return { status: `cart ${put.status}` };
  const consents = { terms: true };
  if (marketing !== undefined) consents.marketing = marketing;
  const r = await post('/api/checkout', { cart_id: cart.id, customer: { full_name: 'בודקת שבע', email: `qa57.${n}@example.com`, phone: '050-1234567' }, address: { city: 'חיפה', street: 'הנמל', house: '12' }, shipping_method: 'express', consents }, h);
  const body = await r.json().catch(() => null);
  return { status: r.status, body, h };
}
const consentOf = (id) => d1(`SELECT c.marketing_consent AS c, c.marketing_consent_at AS at, o.status AS s FROM orders o JOIN customers c ON c.id = o.customer_id WHERE o.id = '${id}'`)[0];
const c1 = await checkout(1, true);
check('C1', 'checkout, marketing: true → 201, the order goes on', c1.status === 201 && !!c1.body?.redirect_url, `${c1.status} order ${c1.body?.order_id}`);
if (c1.status === 201) {
  const r1 = consentOf(c1.body.order_id);
  check('C2', `the consent stored (want ${WANT_C})`, r1.c === WANT_C && (WANT_C ? !!r1.at : r1.at === null), r1);
  const session = new URL(c1.body.redirect_url).pathname.split('/').pop();
  const done = await fetch(`${BASE}/mock-pay/${session}/complete`, { method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded', ...c1.h }, body: 'outcome=success', redirect: 'manual' });
  let st = null;
  for (let i = 0; i < 20; i++) {
    st = (await (await fetch(`${BASE}/api/orders/${c1.body.order_id}`, { headers: { 'x-order-token': c1.body.order_token } })).json()).status;
    if (st !== 'pending_payment') break;
    await new Promise((r) => setTimeout(r, 500));
  }
  const r2 = consentOf(c1.body.order_id);
  check('C3', 'after the payment: paid, the consent unchanged', done.status === 303 && st !== 'pending_payment' && r2.c === r1.c && r2.at === r1.at, { pay: done.status, status: st, row: r2 });
}
const c4 = await checkout(4, undefined);
check('C4', 'checkout without marketing → 201, 0', c4.status === 201 && consentOf(c4.body.order_id).c === 0, `${c4.status}`);
const c5 = await checkout(5, 'true');
check('C5', 'marketing: "true" (a string) → refused by the schema', c5.status === 422 || c5.status === 400, `${c5.status} ${JSON.stringify(c5.body)?.slice(0, 120)}`);
const c6 = await checkout(6, 1);
check('C6', 'marketing: 1 → refused by the schema', c6.status === 422 || c6.status === 400, `${c6.status}`);
const all = d1('SELECT COUNT(*) AS n, SUM(marketing_consent) AS yes, COUNT(marketing_consent_at) AS at FROM customers')[0];
check('C7', `every customer row in this D1: consent ${WANT_C ? 'kept where asked' : '0, no time'}`, WANT_C ? true : all.yes === 0 && all.at === 0, all);
const fails = rows.filter((r) => !r.ok).length;
console.log(`${LABEL}: ${rows.length - fails}/${rows.length}`);
if (OUT) writeFileSync(OUT, JSON.stringify({ label: LABEL, base: BASE, rows }, null, 1) + '\n');
