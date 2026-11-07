/**
 * qa-agent, 2026-11-07 (S4, rerun in S3-S5): two cart edge cases, on QA's snapshot.
 *  A. a PRE1 line (a snapshot taken while the rug was for sale) straight into /story/checkout/ and a test order: is it
 *     in the lines, the total and the order?
 *  B. two tabs: tab 1 has a cart; tab 2 places a test order (the cart is cleared); tab 1 then adds a product: do the
 *     ordered lines come back?
 *   QA_BASE=http://127.0.0.1:8799 node …/check-pre1-checkout.mjs out.json
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8788';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const res = {};
const fill = async (p) => {
  for (const [k, v] of Object.entries({ full_name: 'דנה בדיקה', email: 'qa@example.com', phone: '050-1234567', city: 'חיפה', street: 'הרצל', house: '12' })) await p.locator(`#f-${k}`).fill(v);
  await p.locator('#f-terms').check();
};
{
  const ctx = await browser.newContext({ locale: 'he-IL' });
  const p = await ctx.newPage();
  await p.goto(`${BASE}/story/living-room/nordic/`, { waitUntil: 'load' });
  await p.waitForTimeout(600);
  // one cushion for sale, and the rug as a snapshot taken while it was for sale
  await p.evaluate(() => window.__story.openSheet('A-5'));
  await p.waitForTimeout(300);
  await p.locator('#st-add').click();
  await p.waitForTimeout(300);
  await p.evaluate(() => {
    const s = JSON.parse(localStorage.getItem('hd.story.cart'));
    const v = { variant_id: 'rug-cj-braided-wool-natural:200x300+square', product_id: 'rug-cj-braided-wool-natural', name_he: 'שטיח צמר קלוע, טבעי', option_he: null, price_agorot: 129900, set_qty: 1, available: true };
    s.items.push({ variant_id: v.variant_id, pack: 'set', qty: 1, v });
    localStorage.setItem('hd.story.cart', JSON.stringify(s));
  });
  await p.reload({ waitUntil: 'load' });
  await p.waitForTimeout(600);
  await p.locator('#st-cart-open').click();
  await p.waitForTimeout(400);
  res.A_cart_on_the_nordic_page = await p.evaluate(() => ({ total: document.getElementById('st-cart-total').textContent, held: document.getElementById('st-cart-held').hidden ? null : document.getElementById('st-cart-held').textContent.trim() }));
  await p.goto(`${BASE}/story/checkout/`, { waitUntil: 'load' });
  await p.waitForTimeout(800);
  res.A_checkout = await p.evaluate(() => ({ lines: [...document.querySelectorAll('#co-lines li')].map((l) => l.textContent), subtotal: document.getElementById('co-subtotal').textContent, total: document.getElementById('co-total').textContent, held: document.getElementById('co-held').hidden ? null : document.getElementById('co-held').textContent }));
  await p.screenshot({ path: '/home/user/homedesign-app/qa/reports/2026-11-07-site-track-qa-s3-s5/overlays/pre1-in-checkout-1280.png', fullPage: true });
  await fill(p);
  await Promise.all([p.waitForURL(/\/story\/order\//), p.locator('#co-form button[type="submit"]').click()]);
  await p.waitForTimeout(800);
  res.A_order = await p.evaluate(() => ({ sum: document.getElementById('or-sum').textContent, lines: [...document.querySelectorAll('#or-lines li')].map((l) => l.textContent) }));
  await ctx.close();
}
{
  const ctx = await browser.newContext({ locale: 'he-IL' });
  const t1 = await ctx.newPage();
  await t1.goto(`${BASE}/story/living-room/nordic/`, { waitUntil: 'load' });
  await t1.waitForTimeout(600);
  await t1.evaluate(() => window.__story.openSheet('A-5'));
  await t1.waitForTimeout(300);
  await t1.locator('#st-add').click();
  await t1.waitForTimeout(300);
  await t1.keyboard.press('Escape');
  const t2 = await ctx.newPage();
  await t2.goto(`${BASE}/story/checkout/`, { waitUntil: 'load' });
  await t2.waitForTimeout(600);
  await fill(t2);
  await Promise.all([t2.waitForURL(/\/story\/order\//), t2.locator('#co-form button[type="submit"]').click()]);
  await t2.waitForTimeout(600);
  const afterOrder = await t1.evaluate(() => localStorage.getItem('hd.story.cart'));
  await t1.bringToFront();
  await t1.evaluate(() => window.__story.openSheet('A-6'));
  await t1.waitForTimeout(400);
  await t1.locator('#st-add').click();
  await t1.waitForTimeout(300);
  const s = await t1.evaluate(() => JSON.parse(localStorage.getItem('hd.story.cart')));
  res.B_two_tabs = { storage_after_order_in_tab2: afterOrder, cart_after_next_add_in_tab1: s.items.map((i) => ({ variant_id: i.variant_id, qty: i.qty })) };
  await ctx.close();
}
await browser.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(res, null, 1));
console.log(JSON.stringify(res, null, 1));
