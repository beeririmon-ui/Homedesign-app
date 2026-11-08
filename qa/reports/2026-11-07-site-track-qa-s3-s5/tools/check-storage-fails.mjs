/** qa-agent, 2026-11-07 (S3-S5): the test cart when storage refuses writes (a private window): add, the look, the count,
 * the cart lines, the checkout. Two variants: setItem throws; setItem silently drops. */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const out = {};
for (const mode of ['throws', 'drops']) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: 1280, height: 900 } });
  await ctx.addInitScript((mode) => {
    const orig = Storage.prototype.setItem;
    Storage.prototype.setItem = function (k, v) {
      if (String(k).startsWith('hd.story')) { if (mode === 'throws') throw new DOMException('QuotaExceededError', 'QuotaExceededError'); return; }
      return orig.call(this, k, v);
    };
  }, mode);
  const p = await ctx.newPage();
  const errors = [];
  p.on('pageerror', (e) => errors.push(String(e).slice(0, 120)));
  await p.goto(`${BASE}/story/living-room/boho/`, { waitUntil: 'load' });
  await p.waitForTimeout(500);
  await p.locator('#look-A').click();
  await p.waitForTimeout(500);
  const count = await p.locator('#st-cart-open').textContent();
  await p.locator('#st-cart-open').click();
  await p.waitForTimeout(500);
  const lines = await p.locator('#st-cart-lines .st-cart-line').count();
  const again = await (async () => { await p.keyboard.press('Escape'); await p.locator('#look-A').click(); await p.waitForTimeout(400); return p.locator('#look-A').textContent(); })();
  await p.goto(`${BASE}/story/checkout/`, { waitUntil: 'load' });
  await p.waitForTimeout(500);
  const checkout = await p.evaluate(() => ({ lines: document.querySelectorAll('#co-lines li').length, empty: document.body.textContent.includes('הסל ריק') }));
  out[mode] = { count: count.replace(/\s+/g, ' ').trim(), cart_lines: lines, second_press: again.trim(), checkout_on_next_page: checkout, page_errors: errors };
  await ctx.close();
}
await browser.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(out, null, 1));
console.log(JSON.stringify(out, null, 1));
