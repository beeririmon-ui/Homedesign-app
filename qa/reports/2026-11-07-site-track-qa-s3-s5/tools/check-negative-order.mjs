/** qa-agent, 2026-11-07 (S3-S5): does the test checkout place an order whose quantity is -2 (a hand-edited cart)? */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const ctx = await browser.newContext({ locale: 'he-IL' });
const p = await ctx.newPage();
await p.goto(`${BASE}/story/living-room/nordic/`, { waitUntil: 'load' });
await p.waitForTimeout(500);
await p.evaluate(() => window.__story.openSheet('A-5'));
await p.waitForTimeout(300);
await p.locator('#st-add').click();
await p.waitForTimeout(300);
await p.evaluate(() => {
  const s = JSON.parse(localStorage.getItem('hd.story.cart'));
  s.items[0].qty = -2;
  localStorage.setItem('hd.story.cart', JSON.stringify(s));
});
await p.goto(`${BASE}/story/checkout/`, { waitUntil: 'load' });
await p.waitForTimeout(600);
for (const [k, v] of Object.entries({ full_name: 'דנה בדיקה', email: 'qa@example.com', phone: '050-1234567', city: 'חיפה', street: 'הרצל', house: '12' })) await p.locator(`#f-${k}`).fill(v);
await p.locator('#f-terms').check();
await p.locator('#co-form button[type="submit"]').click();
await p.waitForTimeout(1500);
const res = {
  url: p.url(),
  errors: await p.evaluate(() => document.getElementById('co-errors')?.textContent ?? null),
  order_sum: await p.evaluate(() => document.getElementById('or-sum')?.textContent ?? null),
  stored_orders: await p.evaluate(() => localStorage.getItem('hd.story.orders')),
};
await p.screenshot({ path: '/home/user/homedesign-app/qa/reports/2026-11-07-site-track-qa-s3-s5/overlays/negative-qty-order-1280.png', fullPage: true });
await browser.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(res, null, 1));
console.log(JSON.stringify(res, null, 1));
