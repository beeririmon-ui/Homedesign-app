/**
 * qa-agent, 2026-11-07 (S4): the white bouclé's link and the page it opens; axe (WCAG 2.0/2.1 A+AA, and 2.2 AA as
 * information) on the shop's states at 390 and 1280: the cart open, the checkout with its errors, the order, a detail
 * page with a single piece chosen. QA's snapshot, local.
 *   QA_BASE=http://127.0.0.1:8799 node …/check-s4-misc.mjs out.json
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const { AxeBuilder } = require('@axe-core/playwright');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8788';
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const res = { axe: [] };
{
  const ctx = await b.newContext({ locale: 'he-IL' });
  const p = await ctx.newPage();
  await p.goto(`${BASE}/story/living-room/warm-modern/`, { waitUntil: 'load' });
  await p.waitForTimeout(600);
  const id = await p.evaluate(() => Object.values(JSON.parse(document.getElementById('st-data').textContent).items).find((x) => x.product === 'cushions-cj-boucle-teddy' && x.values?.color === 'white').id);
  await p.evaluate((id) => window.__story.openSheet(id), id);
  await p.waitForTimeout(400);
  const link = await p.locator('#st-page').getAttribute('href');
  const row = await p.evaluate((id) => document.querySelector(`.st-credit[data-item="${id}"] .st-open`) && document.querySelector(`.st-credit[data-item="${id}"]`).dataset.item, id);
  await p.goto(BASE + link, { waitUntil: 'load' });
  await p.waitForFunction(() => !!window.__story?.detail?.());
  res.white_boucle = { item: id, sheet_link: link, opens_on: await p.evaluate(() => window.__story.detail().current().key), title: (await p.locator('h1').textContent()).trim(), story_note: await p.evaluate(() => { const n = document.getElementById('st-pd-story-note'); return n && !n.hidden ? n.textContent.trim() : null; }) };
  await ctx.close();
}
const audit = async (p, label, vp) => {
  const r = await new AxeBuilder({ page: p }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
  const r22 = await new AxeBuilder({ page: p }).withTags(['wcag22aa']).analyze();
  const scroll = await p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  res.axe.push({ state: label, viewport: vp, violations: r.violations.map((v) => `${v.id} (${v.impact}) x${v.nodes.length}: ${v.nodes[0]?.target.join(' ')}`), wcag22aa: r22.violations.map((v) => `${v.id} x${v.nodes.length}`), sideways_px: scroll });
};
for (const vp of [{ w: 390, h: 844, m: true }, { w: 1280, h: 800, m: false }]) {
  const ctx = await b.newContext({ viewport: { width: vp.w, height: vp.h }, isMobile: vp.m, hasTouch: vp.m, locale: 'he-IL' });
  const p = await ctx.newPage();
  const v = `${vp.w}`;
  await p.goto(`${BASE}/story/living-room/nordic/`, { waitUntil: 'load' });
  await p.waitForTimeout(800);
  await p.locator('#look-A').click();
  await p.waitForTimeout(400);
  await p.locator('#st-cart-open').click();
  await p.waitForTimeout(500);
  await audit(p, 'cart open (the look of Nordic A)', v);
  await p.goto(`${BASE}/story/checkout/`, { waitUntil: 'load' });
  await p.waitForTimeout(700);
  await audit(p, 'checkout', v);
  await p.locator('#co-form button[type="submit"]').click();
  await p.waitForTimeout(400);
  await audit(p, 'checkout with the errors', v);
  for (const [k, val] of Object.entries({ full_name: 'דנה בדיקה', email: 'qa@example.com', phone: '050-1234567', city: 'חיפה', street: 'הרצל', house: '12' })) await p.locator(`#f-${k}`).fill(val);
  await p.locator('#f-terms').check();
  await Promise.all([p.waitForURL(/\/story\/order\//), p.locator('#co-form button[type="submit"]').click()]);
  await p.waitForTimeout(700);
  await audit(p, 'order', v);
  await p.goto(`${BASE}/story/living-room/nordic/p/candle-holders-cj-travertine-pedestal/`, { waitUntil: 'load' });
  await p.waitForTimeout(500);
  await p.locator('input[name="st-pack"][value="unit"]').check({ force: true });
  await p.waitForTimeout(200);
  await audit(p, 'detail, a single piece chosen', v);
  await ctx.close();
}
await b.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(res, null, 1));
console.log(JSON.stringify(res.white_boucle), res.axe.map((a) => `${a.viewport} ${a.state}: ${a.violations.length}/${a.wcag22aa.length} sideways ${a.sideways_px}`).join(' | '));
