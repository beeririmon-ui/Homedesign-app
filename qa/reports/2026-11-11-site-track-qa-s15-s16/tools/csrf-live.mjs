/**
 * qa-agent, S16 ת34 live (2026-11-11): the A4 request made by a real browser on another site, against the copy's Worker.
 *
 * - An Access stand-in on 127.0.0.1:8798 forwards everything to the Worker (8799) and, for /admin and /api/admin, adds the
 *   local dev token: the worst case of Access in front (the owner's Access cookie rides along with any request, as with
 *   SameSite=None), so the Worker's own guard is the only thing in the way. It records the headers the browser sent.
 * - An "evil" page on http://localhost:8797 (another site) makes, in Chromium: a fetch POST with
 *   `text/plain; charset=application/json` (no preflight, credentials included) to cancel, and to refund; and a hidden
 *   HTML form POST to the screen's cancel.
 * - The positive control: the same fetch with application/json from the admin's own origin (a page on 8798) → 200.
 * Every outcome is read back from the copy's D1 (QA_D1_EXEC) and through the admin API.
 *   QA_TOKEN=… QA_D1_EXEC=… node csrf-live.mjs <out.json>
 */
import http from 'node:http';
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
const { chromium } = createRequire(process.env.QA_COPY + '/package.json')('playwright-core');

const WORKER = 'http://127.0.0.1:8799';
const TOKEN = process.env.QA_TOKEN;
const OUT = process.argv[2];
const seen = [];

// the Access stand-in
const proxy = http.createServer((req, res) => {
  const path = req.url ?? '/';
  const headers = { ...req.headers };
  if (/^\/(api\/)?admin/.test(path)) {
    headers['x-hd-dev-admin'] = TOKEN;
    seen.push({ method: req.method, path, origin: req.headers.origin ?? null, 'sec-fetch-site': req.headers['sec-fetch-site'] ?? null, 'content-type': req.headers['content-type'] ?? null, cookie: !!req.headers.cookie });
  }
  const up = http.request(`${WORKER}${path}`, { method: req.method, headers }, (r) => {
    res.writeHead(r.statusCode ?? 502, r.headers);
    r.pipe(res);
  });
  req.pipe(up);
  up.on('error', (e) => {
    res.writeHead(502);
    res.end(String(e));
  });
});
// the other site
let evilHtml = '';
const evil = http.createServer((req, res) => {
  res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
  res.end(evilHtml);
});
await new Promise((r) => proxy.listen(8798, '127.0.0.1', r));
await new Promise((r) => evil.listen(8797, '127.0.0.1', r));

const api = async (path, init = {}) => {
  const r = await fetch(`${WORKER}${path}`, { ...init, headers: { 'x-hd-dev-admin': TOKEN, ...(init.headers ?? {}) } });
  return { status: r.status, body: await r.json().catch(() => null) };
};
const d1 = (sql) => execFileSync(process.env.QA_D1_EXEC, [sql], { encoding: 'utf8' });
const countOf = (sql) => Number(/"n":\s*(\d+)/.exec(d1(sql))?.[1] ?? NaN);

// paid orders as the e2e helper places them (e2e/ops.ts placeOrder): the public API, then the mock payment page's form
const CATALOG = JSON.parse(readFileSync(process.env.QA_COPY + '/.generated/catalog.public.json', 'utf8'));
let ipn = 0;
async function paidOrder() {
  const h = { 'cf-connecting-ip': `10.15.16.${++ipn}` };
  const p = CATALOG.products.find((x) => x.slot === 'vase' && x.price_agorot && x.availability.status === 'available');
  const cart = (await (await fetch(`${WORKER}/api/cart`, { method: 'POST', headers: h })).json()).id;
  const put = await fetch(`${WORKER}/api/cart/${cart}/items`, { method: 'PUT', headers: { ...h, 'content-type': 'application/json' }, body: JSON.stringify({ variant_id: p.variants[0].id, qty: 1 }) });
  if (put.status !== 200) throw new Error(`cart ${put.status} ${await put.text()}`);
  const co = await fetch(`${WORKER}/api/checkout`, {
    method: 'POST',
    headers: { ...h, 'content-type': 'application/json' },
    body: JSON.stringify({
      cart_id: cart,
      customer: { full_name: 'בודקת חוצת אתרים', email: 'csrf.qa1516@example.invalid', phone: '050-1234567' },
      address: { city: 'חיפה', street: 'הנמל', house: '12' },
      shipping_method: 'express',
      consents: { terms: true, marketing: false },
    }),
  });
  const c = await co.json();
  if (co.status !== 201) throw new Error(`checkout ${co.status} ${JSON.stringify(c)}`);
  const session = new URL(c.redirect_url).pathname.split('/').pop();
  const done = await fetch(`${WORKER}/mock-pay/${session}/complete`, { method: 'POST', headers: { ...h, 'content-type': 'application/x-www-form-urlencoded' }, body: 'outcome=success', redirect: 'manual' });
  return { id: c.order_id, token: c.order_token, pay: done.status };
}

const result = { proxy_seen: seen };
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader'] });
try {
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  const orders = [];
  for (let i = 0; i < 3; i++) orders.push(await paidOrder());
  result.orders = orders.map((o) => ({ id: o.id, pay: o.pay }));
  await new Promise((r) => setTimeout(r, 3000)); // the local queue sends them to the mock supplier
  const st = async (id) => (await api(`/api/admin/orders/${id}`)).body?.order?.status ?? (await api(`/api/admin/orders/${id}`)).body?.status;
  result.before = await Promise.all(orders.map((o) => st(o.id)));

  const [a, b, f] = orders;
  evilHtml = `<!doctype html><meta charset=utf-8><title>elsewhere</title>
<form id=f method=POST action="http://127.0.0.1:8798/admin/orders/${f.id}/cancel"><input name=reason value="csrf probe"></form>
<script>
window.results = {};
(async () => {
  const send = (path, body) => fetch('http://127.0.0.1:8798' + path, { method: 'POST', credentials: 'include', mode: 'no-cors', headers: { 'content-type': 'text/plain; charset=application/json' }, body: JSON.stringify(body) })
    .then((r) => 'sent (' + r.type + ')').catch((e) => 'blocked: ' + e.message);
  window.results.cancel = await send('/api/admin/orders/${a.id}/cancel', { reason: 'csrf probe' });
  window.results.refund = await send('/api/admin/orders/${b.id}/refund', { amount_agorot: 'rest', reason: 'csrf probe', key: 'qa1516_live_csrf_01' });
  window.results.done = true;
})();
</script>`;
  await page.goto('http://localhost:8797/');
  await page.waitForFunction(() => window.results?.done === true, undefined, { timeout: 15_000 });
  result.page = await page.evaluate(() => window.results);
  await Promise.all([page.waitForLoadState('load'), page.evaluate(() => document.getElementById('f').submit())]);
  await page.waitForTimeout(800);
  result.form_landed = page.url().replace(/\d{10}/, ':id');
  result.after = await Promise.all(orders.map((o) => st(o.id)));
  result.refunds = orders.map((o) => countOf(`SELECT COUNT(*) AS n FROM refunds WHERE order_id = '${o.id}'`));
  result.cross_site_rows = countOf(`SELECT COUNT(*) AS n FROM audit_log WHERE subject IN ('${a.id}','${b.id}','${f.id}')  AND action IN ('order.canceled','refund.requested','order.cancel_requested')`);

  // positive control: the admin's own origin (a page served through 8798), application/json
  await page.goto('http://127.0.0.1:8798/accessibility/');
  result.control = await page.evaluate(async (id) => {
    const r = await fetch(`/api/admin/orders/${id}/cancel`, { method: 'POST', credentials: 'include', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ reason: 'בדיקת QA מאותו אתר' }) });
    return { status: r.status, body: (await r.text()).slice(0, 200) };
  }, a.id);
  result.control_after = await st(a.id);
} finally {
  await browser.close();
  proxy.close();
  evil.close();
}
writeFileSync(OUT, JSON.stringify(result, null, 1));
console.log(JSON.stringify(result, null, 1));
