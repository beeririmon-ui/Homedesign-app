/** qa-agent, 2026-11-10 (S6-S7): the phone wheel as a person would open it, at 400 (touch): (a) tap a hotspot that is
 * on screen without panning; (b) pan the stage until the vase is on screen (the stage's own horizontal scroll), then tap
 * it. After each: where the wheel's dialog is, and a screenshot. */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OV = '/home/user/homedesign-app/qa/reports/2026-11-10-site-track-qa-s6-s7/overlays';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-background-networking', '--disable-features=PushMessaging,GCMChannelStatusRequest,MediaRouter'] });
const res = [];
const open = async (label, prep) => {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: 400, height: 860 }, isMobile: true, hasTouch: true });
  const p = await ctx.newPage();
  await p.goto(`${BASE}/rooms/living-room/`);
  await p.locator('button.hotspot').first().waitFor({ state: 'attached', timeout: 30000 });
  await p.locator('.stage').dispatchEvent('pointerdown');
  await p.waitForFunction(() => window.__hdEngine?.ready === true, undefined, { timeout: 30000 }).catch(() => null);
  await p.waitForTimeout(800);
  const slot = await prep(p);
  const hb = await p.evaluate((s) => { const b = document.querySelector(`button.hotspot[data-slot="${s}"]`).getBoundingClientRect(); return [b.left + b.width / 2, b.top + b.height / 2].map(Math.round); }, slot);
  await p.touchscreen.tap(hb[0], hb[1]);
  await p.waitForTimeout(3000);
  const r = await p.evaluate(() => { const d = document.querySelector('[role="dialog"]'); const b = d?.getBoundingClientRect(); const st = document.querySelector('.stage'); return { dialog: b ? [b.left, b.top, b.width, b.height].map(Math.round) : null, stage_scroll: st ? st.scrollLeft : null, checked: document.querySelector('[role="radio"][aria-checked="true"]')?.getAttribute('aria-label')?.slice(0, 24) ?? null }; });
  await p.screenshot({ path: `${OV}/phone-wheel-real-${label}.png` });
  res.push({ case: label, slot, tap_at: hb, ...r, on_screen: !!r.dialog && r.dialog[0] >= -1 && r.dialog[0] + r.dialog[2] <= 401 });
  await ctx.close();
};
await open('a-visible-hotspot', async (p) => p.evaluate(() => [...document.querySelectorAll('button.hotspot')].find((b) => { const r = b.getBoundingClientRect(); return r.left > 20 && r.right < 380 && r.top > 100 && r.bottom < 760; })?.dataset.slot));
await open('b-pan-then-vase', async (p) => {
  await p.evaluate(() => { const st = document.querySelector('.stage'); const v = document.querySelector('button.hotspot[data-slot="vase"]').getBoundingClientRect(); st.scrollBy({ left: v.left - 180, behavior: 'instant' }); });
  await p.waitForTimeout(800);
  return 'vase';
});
await browser.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(res, null, 1));
console.log(JSON.stringify(res, null, 1));
