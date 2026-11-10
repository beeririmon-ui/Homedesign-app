/** qa-agent, 2026-11-10 (S6-S7): the room's wheel on a phone shows a black stage (QA's capture and frontend-dev's own
 * S6 evidence phone-3-wheel.png). Where are the wheel, the arc, the canvas and the picture after the vase's wheel opens,
 * with and without touch emulation, at 400 and 390, and with a real tap? Screenshots per case. */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OV = '/home/user/homedesign-app/qa/reports/2026-11-10-site-track-qa-s6-s7/overlays';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-background-networking', '--disable-features=PushMessaging,GCMChannelStatusRequest,MediaRouter'] });
const res = [];
for (const [label, opts, how] of [
  ['400-touch-click', { viewport: { width: 400, height: 860 }, isMobile: true, hasTouch: true }, 'click'],
  ['400-touch-tap', { viewport: { width: 400, height: 860 }, isMobile: true, hasTouch: true }, 'tap'],
  ['400-no-touch', { viewport: { width: 400, height: 860 } }, 'click'],
  ['390-touch-tap', { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 3 }, 'tap'],
  ['720-no-touch', { viewport: { width: 720, height: 900 } }, 'click'],
]) {
  const ctx = await browser.newContext({ locale: 'he-IL', ...opts });
  const p = await ctx.newPage();
  const errors = [];
  p.on('pageerror', (e) => errors.push(String(e).slice(0, 160)));
  p.on('console', (m) => { if (m.type() === 'error') errors.push(m.text().slice(0, 160)); });
  await p.goto(`${BASE}/rooms/living-room/`);
  await p.locator('button.hotspot').first().waitFor({ state: 'attached', timeout: 30000 });
  await p.locator('.stage').dispatchEvent('pointerdown');
  await p.waitForFunction(() => window.__hdEngine?.ready === true, undefined, { timeout: 30000 }).catch(() => null);
  await p.waitForTimeout(800);
  await p.screenshot({ path: `${OV}/phone-wheel-diag-${label}-0-before.png` });
  const hs = p.locator('button.hotspot[data-slot="vase"]');
  const before = await p.evaluate(() => { const b = document.querySelector('button.hotspot[data-slot="vase"]').getBoundingClientRect(); return [b.left, b.top, b.width, b.height].map(Math.round); });
  if (how === 'tap') await hs.tap({ force: true });
  else await hs.click({ force: true });
  await p.waitForTimeout(3500);
  const r = await p.evaluate(() => {
    const box = (s) => { const e = document.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect(); return [b.left, b.top, b.width, b.height].map(Math.round); };
    const st = document.querySelector('.stage');
    const cv = document.querySelector('.stage canvas');
    return {
      stage: box('.stage'),
      stage_scroll: st ? [st.scrollLeft, st.scrollWidth, st.clientWidth] : null,
      canvas: box('.stage canvas'),
      canvas_style: cv ? cv.style.transform || getComputedStyle(cv).transform : null,
      picker: box('.picker'),
      arc: box('.arc'),
      dialog: box('[role="dialog"]'),
      imgs: [...document.querySelectorAll('.stage img')].slice(0, 3).map((i) => { const b = i.getBoundingClientRect(); return `${(i.currentSrc || i.src).split('/').pop()} ${[b.left, b.top, b.width, b.height].map(Math.round)}`; }),
      engine: window.__hdEngine ? { ready: window.__hdEngine.ready, keys: Object.keys(window.__hdEngine).slice(0, 12) } : null,
      checked: document.querySelector('[role="radio"][aria-checked="true"]')?.getAttribute('aria-label')?.slice(0, 20) ?? null,
    };
  });
  await p.screenshot({ path: `${OV}/phone-wheel-diag-${label}-1-open.png` });
  res.push({ case: label, hotspot_before: before, ...r, errors });
  await ctx.close();
}
await browser.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(res, null, 1));
console.log(JSON.stringify(res, null, 1));
