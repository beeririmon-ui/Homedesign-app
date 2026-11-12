/**
 * qa-agent, S23 (ה30, a brief check): the cart and the checkout with JavaScript off (javaScriptEnabled: false), phone and
 * desktop: the noscript line is visible, "הסל ריק." is not, and the loading region is still there. A screenshot each.
 *   QA_COPY=<copy>/site node h30-s23qa.mjs <base> <out.json> <screens-dir>
 */
import { createRequire } from 'node:module';
import { writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
const { chromium } = createRequire(join(process.env.QA_COPY, 'package.json'))('playwright-core');
const [BASE, OUT, SHOTS] = process.argv.slice(2);
mkdirSync(SHOTS, { recursive: true });
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const out = {};
for (const [view, o] of [
  ['phone', { viewport: { width: 400, height: 860 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true }],
  ['desktop', { viewport: { width: 1280, height: 800 } }],
])
  for (const p of ['/cart/', '/checkout/']) {
    const ctx = await browser.newContext({ locale: 'he-IL', javaScriptEnabled: false, ...o });
    const page = await ctx.newPage();
    await page.goto(`${BASE}${p}`, { waitUntil: 'load' });
    const r = await page.evaluate(() => {
      const t = document.body.innerText;
      const ns = document.querySelector('.cart-noscript');
      const box = ns ? ns.getBoundingClientRect() : null;
      return { noscript_text: ns ? ns.textContent : null, noscript_visible: !!box && box.height > 0, noscript_top: box ? Math.round(box.top) : null, empty: /הסל ריק\./.test(t), pay_empty: /הסל ריק, אין מה לשלם/.test(t), loading: !!document.querySelector('.cart-loading'), h1: document.querySelector('h1')?.textContent ?? null };
    });
    await page.screenshot({ path: join(SHOTS, `h30-${p.replaceAll('/', '')}-no-js-${view}.png`) });
    out[`${view}:${p}`] = r;
    console.log(view, p, JSON.stringify(r));
    await ctx.close();
  }
await browser.close();
writeFileSync(OUT, JSON.stringify(out, null, 1));
