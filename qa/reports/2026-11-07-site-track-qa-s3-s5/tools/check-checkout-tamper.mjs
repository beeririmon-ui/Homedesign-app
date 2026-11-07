/**
 * qa-agent, 2026-11-07 (S3-S5): the strict test checkout against a hand-edited cart in storage.
 *  1. a sold variant with a forged snapshot price (₪1)       -> the table's price should win
 *  2. an unknown variant id with a snapshot that says "available"  -> held
 *  3. a sold variant with qty -2, then 999, then 2.5        -> should be refused or clamped to 1..20
 *   QA_BASE=http://127.0.0.1:8799 node check-checkout-tamper.mjs out.json
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const res = {};
const ctx = await browser.newContext({ locale: 'he-IL' });
const p = await ctx.newPage();
await p.goto(`${BASE}/story/living-room/nordic/`, { waitUntil: 'load' });
await p.waitForTimeout(500);
await p.evaluate(() => window.__story.openSheet('A-5'));
await p.waitForTimeout(300);
await p.locator('#st-add').click();
await p.waitForTimeout(300);
const base = await p.evaluate(() => localStorage.getItem('hd.story.cart'));
const read = () =>
  p.evaluate(() => ({
    lines: [...document.querySelectorAll('#co-lines li')].map((l) => l.textContent),
    subtotal: document.getElementById('co-subtotal')?.textContent,
    total: document.getElementById('co-total')?.textContent,
    held: document.getElementById('co-held')?.hidden ? null : document.getElementById('co-held')?.textContent,
  }));
const run = async (label, mutate) => {
  await p.evaluate(([b, m]) => {
    const s = JSON.parse(b);
    new Function('s', m)(s);
    localStorage.setItem('hd.story.cart', JSON.stringify(s));
  }, [base, mutate]);
  await p.goto(`${BASE}/story/checkout/`, { waitUntil: 'load' });
  await p.waitForTimeout(600);
  res[label] = await read();
};
await run('as_added', '');
await run('forged_price_1', 's.items[0].v = { ...s.items[0].v, price_agorot: 100 };');
await run('unknown_variant_available', "s.items.push({ variant_id: 'qa-fake:default', pack: 'set', qty: 1, v: { variant_id: 'qa-fake:default', product_id: 'qa-fake', name_he: 'מוצר מזויף', option_he: null, price_agorot: 100, set_qty: 1, available: true } });");
await run('qty_minus_2', 's.items[0].qty = -2;');
await run('qty_999', 's.items[0].qty = 999;');
await run('qty_2_5', 's.items[0].qty = 2.5;');
await run('qty_string', "s.items[0].qty = '3';");
await run('pack_unit_on_set_only', "s.items[0].pack = 'unit';");
res.stored_variant = JSON.parse(base).items[0].variant_id;
await browser.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(res, null, 1));
console.log(JSON.stringify(res, null, 1));
