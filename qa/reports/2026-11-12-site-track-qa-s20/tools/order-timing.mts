/**
 * QA S20: the order page (changed in S20) until its line under the total is on screen, delivered order, 1280 and 400,
 * 7 loads each after one warm-up, median and max (performance.now() at the line's first paint, polled per frame).
 *   cd <copy>/site && node node_modules/tsx/dist/cli.mjs <this> --base=… --site=<copy>/site --label=… --out=<json>
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { chromium } from '@playwright/test';
const arg = (n: string) => process.argv.find((a) => a.startsWith(`--${n}=`))?.slice(n.length + 3);
const BASE = arg('base')!, SITE = arg('site')!, OUT = arg('out')!, LABEL = arg('label')!;
const token = /^ADMIN_DEV_TOKEN=(.+)$/m.exec(readFileSync(join(SITE, 'api/.dev.vars'), 'utf8'))![1]!.trim();
const catalog = JSON.parse(readFileSync(join(SITE, '.generated/catalog.public.json'), 'utf8'));
const h = { 'cf-connecting-ip': '10.20.99.1', 'content-type': 'application/json' };
const api = (p: string, i: RequestInit = {}) => fetch(BASE + p, { ...i, headers: { ...h, ...(i.headers ?? {}) } });
const sold = catalog.products.find((p: { price_agorot: number | null; availability: { status: string } }) => p.price_agorot && p.availability.status === 'available');
const cart = await (await api('/api/cart', { method: 'POST', body: '{}' })).json();
await api(`/api/cart/${cart.id}/items`, { method: 'PUT', body: JSON.stringify({ variant_id: sold.variants[0].id, qty: 1 }) });
const co = await (await api('/api/checkout', { method: 'POST', body: JSON.stringify({ cart_id: cart.id, customer: { full_name: 'בודק זמנים', email: 'qa20t@example.com', phone: '050-1234567' }, address: { city: 'חיפה', street: 'הנמל', house: '12' }, shipping_method: 'express', consents: { terms: true } }) })).json();
await fetch(`${BASE}/mock-pay/${new URL(co.redirect_url).pathname.split('/').pop()}/complete`, { method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded', 'cf-connecting-ip': h['cf-connecting-ip'] }, body: 'outcome=success', redirect: 'manual' });
const st = async () => (await (await fetch(`${BASE}/api/orders/${co.order_id}`, { headers: { 'x-order-token': co.order_token } })).json()).status;
for (let i = 0; i < 60 && (await st()) !== 'sent_to_supplier'; i++) await new Promise((r) => setTimeout(r, 500));
for (const ev of ['shipped', 'delivered']) {
  await api(`/api/admin/orders/${co.order_id}/mock-supplier`, { method: 'POST', headers: { 'x-hd-dev-admin': token }, body: JSON.stringify({ event: ev }) });
  for (let i = 0; i < 60 && (await st()) !== ev; i++) await new Promise((r) => setTimeout(r, 500));
}
const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM ?? '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const out: Record<string, unknown> = { label: LABEL, order: co.order_id };
for (const w of [1280, 400]) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: w, height: 900 } });
  await ctx.addInitScript({ content: 'window.__name = (f) => f;' });
  await ctx.addInitScript(([id, t]) => {
    localStorage.setItem(`hd.order.${id}`, t!);
    (window as unknown as { __t: number }).__t = 0;
    const tick = () => {
      if (!(window as unknown as { __t: number }).__t && document.querySelector('.order-sheet > p.small.muted')) (window as unknown as { __t: number }).__t = performance.now();
      else requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [co.order_id, co.order_token]);
  const page = await ctx.newPage();
  const times: number[] = [];
  for (let i = 0; i < 8; i++) {
    await page.goto(`${BASE}/order/${co.order_id}/`);
    await page.waitForFunction(() => (window as unknown as { __t: number }).__t > 0, null, { timeout: 15_000 });
    const t = await page.evaluate(() => (window as unknown as { __t: number }).__t);
    if (i) times.push(Math.round(t));
  }
  times.sort((a, b) => a - b);
  out[`w${w}`] = { median: times[Math.floor(times.length / 2)], max: times[times.length - 1], all: times };
  await ctx.close();
}
await browser.close();
writeFileSync(OUT, JSON.stringify(out, null, 1) + '\n');
console.log(JSON.stringify(out));
