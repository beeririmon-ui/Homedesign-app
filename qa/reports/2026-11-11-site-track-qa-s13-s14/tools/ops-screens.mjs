/**
 * qa-agent, 2026-11-11 (S13 at a8104956): screens of what ops-live.mjs made. The admin at 1280 (the local dev token as
 * the stand-in for Access), the customer's order page at 400 (the order's token in localStorage, as the checkout leaves
 * it), and the admin without a token (403). The customer page's visible text is searched for a supplier's name.
 *   QA_BASE=… QA_COPY=… QA_OUT=… QA_TOKEN=<dev token> node ops-screens.mjs
 */
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
const COPY = process.env.QA_COPY;
const OUT = process.env.QA_OUT;
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const require = createRequire(join(COPY, 'package.json'));
const { chromium } = require('playwright-core');
const live = JSON.parse(readFileSync(join(OUT, 'data/ops-live.json'), 'utf8'));
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--disable-background-networking'] });
const out = {};
const shot = async (name, url, vp, headers = {}, init) => {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: vp, isMobile: vp.width < 600, hasTouch: vp.width < 600, extraHTTPHeaders: { 'cf-connecting-ip': '203.0.113.250', ...headers } });
  const p = await ctx.newPage();
  if (init) await p.addInitScript(init.fn, init.arg);
  const r = await p.goto(`${BASE}${url}`, { waitUntil: 'load' });
  await p.waitForTimeout(1500);
  const text = await p.evaluate(() => document.body.innerText);
  await p.screenshot({ path: join(OUT, 'overlays', `${name}.png`), fullPage: true });
  out[name] = { status: r.status(), dir: await p.evaluate(() => document.documentElement.dir), lang: await p.evaluate(() => document.documentElement.lang), supplier_word: /\b(cj|cjpacket|aliexpress|zendrop|mock|MOCK-)\b/i.exec(text)?.[0] ?? null, text: text.replace(/\s+/g, ' ').slice(0, 400) };
  await ctx.close();
};
const T = { 'x-hd-dev-admin': process.env.QA_TOKEN };
const o = live.steps.flow.order;
await shot('admin-list-1280', '/admin/', { width: 1280, height: 900 }, T);
await shot('admin-order-refunded-1280', `/admin/orders/${o}`, { width: 1280, height: 900 }, T);
await shot('admin-403-1280', '/admin/', { width: 1280, height: 900 });
// the customer's page: the order's token where the checkout leaves it (these are my copy's test orders)
const tok = (id, t) => ({ fn: ([i, tk]) => localStorage.setItem(`hd.order.${i}`, tk), arg: [id, t] });
await shot('order-delivered-refunded-400', `/order/${o}/`, { width: 400, height: 860 }, {}, tok(o, live.steps.flow.order_token_local_copy));
const c = live.steps.flow.canceled_order;
if (c) await shot('order-canceled-after-supplier-400', `/order/${c.id}/`, { width: 400, height: 860 }, {}, tok(c.id, c.token));
writeFileSync(join(OUT, 'data/ops-screens.json'), JSON.stringify(out, null, 1));
console.log(JSON.stringify(Object.fromEntries(Object.entries(out).map(([k, v]) => [k, { status: v.status, dir: v.dir, supplier_word: v.supplier_word }]))));
await browser.close();
