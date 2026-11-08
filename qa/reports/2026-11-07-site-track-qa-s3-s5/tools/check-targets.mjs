/**
 * qa-agent, 2026-11-07 (S3-S5): G7.7 (44 × 44) on the magazine pages in the states system.spec does not open: the
 * product sheet, the cart with lines, a detail page with its options, the checkout with errors, the tool draft. Every
 * visible a/button/input/select/summary/[role=button]; a radio or checkbox counts by its label; an inline link (inside a
 * sentence) is listed apart (WCAG 2.5.8's exception). Also: a focus ring on each stop (outline/box-shadow differs from
 * the same element unfocused).
 *   QA_BASE=http://127.0.0.1:8799 node check-targets.mjs out.json
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const measure = (p, scope) =>
  p.evaluate((scope) => {
    const root = scope ? document.querySelector(scope) : document;
    const vis = (el) => {
      const r = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return r.width > 1 && r.height > 1 && s.visibility !== 'hidden' && s.display !== 'none' && !el.closest('[hidden], [aria-hidden="true"], .sr-only, .mag-skip, .skip-link');
    };
    const inline = (el) => {
      if (el.tagName !== 'A') return false;
      const p = el.closest('p, li, dd, td, label');
      return !!p && (p.textContent ?? '').trim().length > (el.textContent ?? '').trim().length + 2;
    };
    const name = (el) => `${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''}${typeof el.className === 'string' && el.className ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : ''}`;
    const els = [...root.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea, summary, [role="button"]')].filter(vis);
    const rows = els.map((el) => {
      const box = el.matches('input[type=radio], input[type=checkbox]') ? (el.closest('label') ?? el) : el;
      const r = box.getBoundingClientRect();
      return { at: name(el), text: (el.textContent || el.getAttribute('aria-label') || el.value || '').trim().slice(0, 30), w: Math.round(r.width), h: Math.round(r.height), inline: inline(el) };
    });
    return { controls: rows.length, small: rows.filter((r) => !r.inline && (r.w < 43.5 || r.h < 43.5)), inline_small: rows.filter((r) => r.inline && (r.w < 43.5 || r.h < 43.5)).length };
  }, scope);
const res = [];
for (const w of [400, 1280]) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: w, height: w > 500 ? 900 : 860 } });
  const p = await ctx.newPage();
  // the sheet
  await p.goto(`${BASE}/story/living-room/boho/`, { waitUntil: 'load' });
  await p.waitForTimeout(600);
  await p.evaluate(() => window.__story.openSheet('A-5'));
  await p.waitForTimeout(600);
  res.push({ width: w, state: 'boho, the sheet open (A-5)', ...(await measure(p, '#st-sheet')) });
  await p.locator('#st-add').click();
  await p.waitForTimeout(300);
  await p.keyboard.press('Escape');
  await p.waitForTimeout(500);
  // the dots (their hit area)
  res.push({ width: w, state: 'boho, the dots', ...(await p.evaluate(() => { const m = [...document.querySelectorAll('#frame-A .st-mark')].filter((x) => !x.hidden && getComputedStyle(x).display !== 'none'); return { controls: m.length, small: m.map((x) => { const r = x.getBoundingClientRect(); return { at: x.dataset.item, w: Math.round(r.width), h: Math.round(r.height) }; }).filter((r) => r.w < 43.5 || r.h < 43.5) }; })) });
  // the cart with lines
  await p.locator('#look-A').click();
  await p.waitForTimeout(500);
  await p.locator('#st-cart-open').click();
  await p.waitForTimeout(600);
  res.push({ width: w, state: 'boho, the cart open with 5 lines', ...(await measure(p, '#st-cart')) });
  await p.keyboard.press('Escape');
  // a detail page with options
  await p.goto(`${BASE}/story/living-room/nordic/p/cushions-boucle-teddy-d7wrb/`, { waitUntil: 'load' });
  await p.waitForTimeout(500);
  res.push({ width: w, state: 'detail page (bouclé, options)', ...(await measure(p, null)) });
  // the checkout, empty submit
  await p.goto(`${BASE}/story/checkout/`, { waitUntil: 'load' });
  await p.waitForTimeout(500);
  await p.locator('#co-form button[type="submit"]').click();
  await p.waitForTimeout(500);
  res.push({ width: w, state: 'checkout after an empty submit', ...(await measure(p, null)) });
  // the contents, the tool draft, the order page
  for (const [u, s] of [['/story/', 'contents'], ['/story/living-room/warm-modern/tool/', 'tool draft'], ['/story/living-room/japandi/', 'typographic page']]) {
    await p.goto(BASE + u, { waitUntil: 'load' });
    await p.waitForTimeout(500);
    res.push({ width: w, state: s, ...(await measure(p, null)) });
  }
  await ctx.close();
}
await browser.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(res, null, 1));
for (const r of res) console.log(r.width, r.state, 'controls', r.controls, 'small', JSON.stringify(r.small), 'inline small', r.inline_small ?? '-');
