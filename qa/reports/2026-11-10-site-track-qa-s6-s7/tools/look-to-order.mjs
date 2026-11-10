/**
 * qa-agent, 2026-11-10 (S6-S7): the real path, in the browser, at 1280 and 400. Boho "המראה כולו לסל" -> the story cart
 * (the site's cart: hd.cart, the API) -> "לתשלום" -> /checkout/ (empty submit first: the error summary and its targets) ->
 * a valid form -> the mock hosted page -> pay -> /order/<id>/. Then: the order's lines and total vs the look, the
 * story's count after the order, the shop's /cart/ after the order, and /story/checkout/ + /story/order/ redirects.
 *   QA_BASE=http://127.0.0.1:8799 node look-to-order.mjs out.json
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OV = '/home/user/homedesign-app/qa/reports/2026-11-10-site-track-qa-s6-s7/overlays';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const res = [];
for (const [w, h] of [[1280, 900], [400, 860]]) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: w, height: h }, isMobile: w < 500, hasTouch: w < 500 });
  const p = await ctx.newPage();
  const api = [];
  p.on('request', (q) => { if (q.url().includes('/api/')) api.push(`${q.method()} ${q.url().replace(BASE, '').replace(/cart\/[^/?]+/, 'cart/:id')}`); });
  const r = { width: w };
  await p.goto(`${BASE}/story/living-room/boho/`, { waitUntil: 'load' });
  await p.waitForTimeout(700);
  r.look_button = (await p.locator('#look-A').textContent()).trim();
  r.look_variants = await p.locator('#look-A').getAttribute('data-variants');
  await p.locator('#look-A').click();
  await p.waitForTimeout(1500);
  r.after_look_button = (await p.locator('#look-A').textContent()).trim();
  r.count_after_look = (await p.locator('#st-cart-open').textContent()).replace(/\s+/g, ' ').trim();
  r.storage = await p.evaluate(() => Object.keys(localStorage).map((k) => `${k}=${(localStorage.getItem(k) ?? '').slice(0, 60)}`));
  await p.locator('#st-cart-open').click();
  await p.waitForTimeout(800);
  r.story_cart_lines = await p.evaluate(() => [...document.querySelectorAll('#st-cart-lines .st-cart-line')].map((l) => l.textContent.replace(/\s+/g, ' ').trim().slice(0, 90)));
  r.story_cart_total = (await p.locator('#st-cart-total').textContent()).trim();
  await p.screenshot({ path: `${OV}/boho-story-cart-${w}.png` });
  const pay = p.locator('#st-cart-pay');
  r.pay_href = await pay.getAttribute('href').catch(() => null);
  await Promise.all([p.waitForURL(/\/checkout\//), pay.click()]);
  await p.waitForTimeout(1000);
  r.checkout_url = p.url().replace(BASE, '');
  r.checkout_lines = await p.evaluate(() => [...document.querySelectorAll('main li, main tr')].map((x) => x.textContent.replace(/\s+/g, ' ').trim()).filter((t) => /₪/.test(t)).slice(0, 12));
  // an empty submit: the summary and its links
  await p.locator('form button[type="submit"]').first().click();
  await p.waitForTimeout(700);
  r.error_summary = await p.evaluate(() => {
    const links = [...document.querySelectorAll('main a[href^="#"]')].filter((a) => a.offsetParent !== null);
    return links.map((a) => { const b = a.getBoundingClientRect(); return `${a.textContent.trim().slice(0, 28)} ${Math.round(b.width)}x${Math.round(b.height)}`; });
  });
  await p.screenshot({ path: `${OV}/site-checkout-errors-${w}.png`, fullPage: true });
  // a valid form
  const fill = async (sel, v) => { const l = p.locator(sel).first(); if (await l.count()) await l.fill(v); };
  await fill('input[name="full_name"]', 'דנה בדיקה');
  await fill('input[name="email"]', 'qa@example.com');
  await fill('input[name="phone"]', '050-1234567');
  await fill('input[name="city"]', 'חיפה');
  await fill('input[name="street"]', 'הרצל');
  await fill('input[name="house"]', '12');
  await p.locator('#f-terms').check({ force: true });
  await Promise.all([p.waitForURL(/mock-pay/, { timeout: 15000 }), p.locator('form button[type="submit"]').first().click()]);
  r.mock_pay = p.url().replace(BASE, '').replace(/mock-pay\/[^/?]+/, 'mock-pay/:session');
  await Promise.all([p.waitForURL(/\/order\//, { timeout: 15000 }), p.getByRole('button', { name: /אישור תשלום|תשלום \(מדומה\)|שלם/ }).first().click()]);
  await p.waitForTimeout(1500);
  r.order_url = p.url().replace(BASE, '').replace(/#.*/, '');
  r.order_text = (await p.locator('main').textContent()).replace(/\s+/g, ' ').trim().slice(0, 700);
  await p.screenshot({ path: `${OV}/order-from-boho-look-${w}.png`, fullPage: true });
  // back to the story: the count; the shop's cart
  await p.goto(`${BASE}/story/living-room/boho/`, { waitUntil: 'load' });
  await p.waitForTimeout(1000);
  r.story_count_after_order = (await p.locator('#st-cart-open').textContent()).replace(/\s+/g, ' ').trim();
  await p.goto(`${BASE}/cart/`, { waitUntil: 'load' });
  await p.waitForTimeout(800);
  r.shop_cart_after_order = (await p.locator('main').textContent()).replace(/\s+/g, ' ').trim().slice(0, 80);
  r.api_calls = [...new Set(api)];
  res.push(r);
  await ctx.close();
}
await browser.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(res, null, 1));
console.log(JSON.stringify(res, null, 1));
