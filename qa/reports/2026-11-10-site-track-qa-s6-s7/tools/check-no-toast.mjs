/**
 * qa-agent, 2026-11-10 (S6-S7): §7.2, no toast. On a shop product page and in the room's wheel, "הוספה לסל": every
 * element that becomes visible on top of the page (fixed / absolute / sticky, not there before) within 3 s; the
 * button's own text; the live region's text; the .toast element's painted size.
 *   QA_BASE=http://127.0.0.1:8799 node check-no-toast.mjs out.json
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OV = '/home/user/homedesign-app/qa/reports/2026-11-10-site-track-qa-s6-s7/overlays';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const res = [];
const overlays = (p) =>
  p.evaluate(() =>
    [...document.querySelectorAll('body *')]
      .filter((el) => {
        const s = getComputedStyle(el);
        if (!['fixed', 'absolute', 'sticky'].includes(s.position) || s.visibility === 'hidden' || s.display === 'none' || Number(s.opacity) === 0) return false;
        const r = el.getBoundingClientRect();
        if (r.width < 4 || r.height < 4) return false;
        if (s.clip && s.clip !== 'auto' && /rect\(0px,? 0px,? 0px,? 0px\)/.test(s.clip)) return false;
        return (el.textContent ?? '').trim().length > 0;
      })
      .map((el) => `${el.tagName.toLowerCase()}.${(el.className?.toString() ?? '').split(' ')[0]}:${(el.textContent ?? '').trim().slice(0, 30)}`),
  );
for (const [w, h] of [[1280, 900], [400, 860]]) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: w, height: h }, isMobile: w < 500, hasTouch: w < 500 });
  const p = await ctx.newPage();
  await p.goto(`${BASE}/p/vase-textured-white-stoneware-w90r9/`, { waitUntil: 'load' });
  await p.waitForTimeout(1200);
  const before = await overlays(p);
  const btn = p.getByRole('button', { name: /הוספה לסל/ }).first();
  await btn.scrollIntoViewIfNeeded();
  await btn.click();
  const seen = new Set();
  for (let i = 0; i < 12; i++) {
    await p.waitForTimeout(250);
    for (const o of await overlays(p)) if (!before.includes(o)) seen.add(o);
  }
  const toast = await p.evaluate(() => { const t = document.querySelector('.toast'); if (!t) return null; const r = t.getBoundingClientRect(); const s = getComputedStyle(t); return { text: t.textContent, w: r.width, h: r.height, clip: s.clip, position: s.position }; });
  const live = await p.evaluate(() => document.querySelector('.live-region')?.textContent ?? null);
  const btnText = await p.evaluate(() => [...document.querySelectorAll('button')].find((b) => /נוסף לסל|הוספה לסל/.test(b.textContent))?.textContent.trim());
  await p.screenshot({ path: `${OV}/shop-product-after-add-${w}.png` });
  res.push({ width: w, page: 'product', new_visible_overlays: [...seen], toast_element: toast, live_region: live, button_text_after: btnText });
  await ctx.close();
}
await browser.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(res, null, 1));
console.log(JSON.stringify(res, null, 1));
