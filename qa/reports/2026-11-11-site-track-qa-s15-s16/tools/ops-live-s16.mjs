/**
 * qa-agent, S16 (2026-11-11), on the copy's live Worker (8799, wrangler dev, its own D1):
 * - ת39: a paid order failing at the supplier: its shipment failed since 29 and 31 minutes ago (set in the copy's D1, as
 *   the queue would leave it), /healthz each time; the customer's order API and page ("מתעכבת" and its line, no supplier).
 * - ת37: the order page's own error message with its code (a wrong token) in the browser.
 * The order is then canceled in D1 so the server is healthy again for the next checks.
 *   QA_BASE=… QA_COPY=<copy>/site QA_OUT=<folder> QA_D1_EXEC=… node ops-live-s16.mjs
 */
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
const COPY = process.env.QA_COPY;
const { chromium } = createRequire(join(COPY, 'package.json'))('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OUT = process.env.QA_OUT;
const d1 = (sql) => execFileSync(process.env.QA_D1_EXEC, [sql], { encoding: 'utf8' });
const pub = JSON.parse(readFileSync(join(COPY, '.generated/catalog.public.json'), 'utf8'));
const h = { 'cf-connecting-ip': '192.0.2.77' };
const j = { ...h, 'content-type': 'application/json' };

const p = pub.products.find((x) => x.slot === 'vase' && x.price_agorot && x.availability.status === 'available');
const cart = (await (await fetch(`${BASE}/api/cart`, { method: 'POST', headers: h })).json()).id;
await fetch(`${BASE}/api/cart/${cart}/items`, { method: 'PUT', headers: j, body: JSON.stringify({ variant_id: p.variants[0].id, qty: 1 }) });
const co = await (
  await fetch(`${BASE}/api/checkout`, {
    method: 'POST',
    headers: j,
    body: JSON.stringify({ cart_id: cart, customer: { full_name: 'בודקת עיכוב', email: 'delay.qa1516@example.invalid', phone: '050-7654321' }, address: { city: 'חיפה', street: 'הנמל', house: '3' }, shipping_method: 'express', consents: { terms: true, marketing: false } }),
  })
).json();
await fetch(`${BASE}/mock-pay/${new URL(co.redirect_url).pathname.split('/').pop()}/complete`, { method: 'POST', headers: { ...h, 'content-type': 'application/x-www-form-urlencoded' }, body: 'outcome=success', redirect: 'manual' });
await new Promise((r) => setTimeout(r, 3000));
const id = co.order_id;
const res = { order: id };
const health = async () => {
  const r = await fetch(`${BASE}/healthz`);
  return `${r.status} ${await r.text()}`;
};
res.healthz_before = await health();
const ago = (min) => new Date(Date.now() - min * 60_000).toISOString();
d1(`UPDATE orders SET status = 'supplier_error' WHERE id = '${id}'`);
d1(`UPDATE supplier_shipments SET status = 'failed', supplier_order_id = NULL, reach = 'maybe', last_error = 'qa: upstream 502', failing_since = '${ago(29)}' WHERE order_id = '${id}'`);
res.healthz_29min = await health();
d1(`UPDATE supplier_shipments SET failing_since = '${ago(31)}' WHERE order_id = '${id}'`);
res.healthz_31min = await health();
const view = await (await fetch(`${BASE}/api/orders/${id}`, { headers: { 'x-order-token': co.order_token } })).text();
res.customer_api = JSON.parse(view);
res.supplier_word_in_view = /\b(cj|cjpacket|aliexpress|zendrop|mock|qa: upstream)\b/i.exec(view)?.[0] ?? null;
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader'] });
for (const w of [1280, 400]) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: w, height: 900 } });
  const page = await ctx.newPage();
  await page.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' });
  await page.evaluate(([i, t]) => localStorage.setItem(`hd.order.${i}`, t), [id, co.order_token]);
  await page.goto(`${BASE}/order/${id}/`, { waitUntil: 'load' });
  await page.locator('.order-sheet').waitFor({ timeout: 30_000 });
  await page.waitForTimeout(1200);
  res[`page_${w}`] = await page.evaluate(() => ({
    pill: document.querySelector('.status-pill')?.textContent?.trim(),
    steps_label: document.querySelector('.order-steps')?.getAttribute('aria-label'),
    delay_line: [...document.querySelectorAll('.order-sheet p')].map((x) => x.textContent.trim()).find((t) => t.includes('עיכוב')) ?? null,
  }));
  await page.locator('.order-sheet').screenshot({ path: join(OUT, 'overlays', `t39-order-delayed-${w}.png`) });
  // ת37: a wrong token: the server's own message and its code
  await page.evaluate(([i]) => localStorage.setItem(`hd.order.${i}`, 'x'.repeat(40)), [id]);
  await page.goto(`${BASE}/order/${id}/`, { waitUntil: 'load' });
  await page.waitForTimeout(1500);
  res[`wrong_token_${w}`] = await page.evaluate(() => document.querySelector('main')?.innerText.replace(/\s+/g, ' ').slice(0, 200));
  await ctx.close();
}
await browser.close();
d1(`UPDATE orders SET status = 'canceled' WHERE id = '${id}'`);
res.healthz_after_cancel = await health();
writeFileSync(join(OUT, 'data/ops-live-s16.json'), JSON.stringify(res, null, 1));
console.log(JSON.stringify(res, null, 1));
