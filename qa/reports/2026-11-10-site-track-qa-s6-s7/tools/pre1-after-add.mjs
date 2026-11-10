/**
 * qa-agent, 2026-11-10 (S6-S7): PRE1 after the add. In the browser, boho's look goes into the cart; then (outside,
 * on QA's private D1) the throw stops being sold; then: the story cart, /cart/, /checkout/ and the order. Does the
 * customer see that a line left, and is it out of the charge? The D1 change is made by the caller between the steps:
 *   step 1: node pre1-after-add.mjs 1 state.json     (adds the look, saves the browser state)
 *   (caller) UPDATE products SET availability='unavailable' WHERE id='sofa-cover-washed-hemp-throw-g8qc5'
 *   step 2: node pre1-after-add.mjs 2 state.json out.json
 */
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const [step, statePath, out] = process.argv.slice(2);
const OV = '/home/user/homedesign-app/qa/reports/2026-11-10-site-track-qa-s6-s7/overlays';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
if (step === '1') {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: 1280, height: 900 } });
  const p = await ctx.newPage();
  await p.goto(`${BASE}/story/living-room/boho/`, { waitUntil: 'load' });
  await p.waitForTimeout(600);
  await p.locator('#look-A').click();
  await p.waitForTimeout(1500);
  console.log(await p.locator('#st-cart-open').textContent());
  await ctx.storageState({ path: statePath });
} else {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: 1280, height: 900 }, storageState: statePath });
  const p = await ctx.newPage();
  const r = {};
  await p.goto(`${BASE}/story/living-room/boho/`, { waitUntil: 'load' });
  await p.waitForTimeout(1200);
  r.story_count = (await p.locator('#st-cart-open').textContent()).replace(/\s+/g, ' ').trim();
  await p.locator('#st-cart-open').click();
  await p.waitForTimeout(800);
  r.story_cart = (await p.locator('#st-cart').textContent()).replace(/\s+/g, ' ').trim().slice(0, 600);
  await p.screenshot({ path: `${OV}/pre1-after-add-story-cart.png` });
  await p.goto(`${BASE}/cart/`, { waitUntil: 'load' });
  await p.waitForTimeout(1000);
  r.site_cart = (await p.locator('main').textContent()).replace(/\s+/g, ' ').trim().slice(0, 600);
  await p.screenshot({ path: `${OV}/pre1-after-add-site-cart.png`, fullPage: true });
  await p.goto(`${BASE}/checkout/`, { waitUntil: 'load' });
  await p.waitForTimeout(1000);
  r.checkout = (await p.locator('main').textContent()).replace(/\s+/g, ' ').trim().slice(0, 700);
  r.mentions_throw = { story: r.story_cart.includes('שמיכת'), site_cart: r.site_cart.includes('שמיכת'), checkout: r.checkout.includes('שמיכת') };
  writeFileSync(out, JSON.stringify(r, null, 1));
  console.log(JSON.stringify(r, null, 1));
}
await browser.close();
