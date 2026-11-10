/**
 * qa-agent, 2026-11-10: /checkout/ with an empty cart (a fresh browser), at 400 and 1280: the "חזרה לסלון" link's box
 * against the site's own G7.7 gate (targets ≥ 44 × 44), the other links on the page, and a screenshot.
 *   QA_BASE=http://127.0.0.1:8799 QA_COPY=<copy>/site QA_OUT=<qa folder> node empty-checkout.mjs
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
const require = createRequire(join(process.env.QA_COPY, 'package.json'));
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OUT = process.env.QA_OUT;
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--disable-background-networking'] });
const res = [];
for (const [w, h] of [[400, 860], [1280, 800]]) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: w, height: h } });
  const p = await ctx.newPage();
  await p.goto(`${BASE}/checkout/`, { waitUntil: 'load' });
  await p.waitForTimeout(1500);
  const r = await p.evaluate(() => [...document.querySelectorAll('main a, .page a')].filter((a) => a.offsetParent).map((a) => { const b = a.getBoundingClientRect(); return { text: a.textContent.trim(), w: Math.round(b.width), h: Math.round(b.height), inline: getComputedStyle(a).display === 'inline' }; }));
  await p.screenshot({ path: join(OUT, 'overlays', `empty-checkout-${w}.png`) });
  res.push({ width: w, links: r, empty_notice: await p.locator('.notice', { hasText: 'הסל ריק' }).count() });
  await ctx.close();
}
await browser.close();
writeFileSync(join(OUT, 'data/empty-checkout.json'), JSON.stringify(res, null, 1));
console.log(JSON.stringify(res, null, 1));
