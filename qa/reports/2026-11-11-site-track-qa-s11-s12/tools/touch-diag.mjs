/** qa-agent, 2026-11-11: what a real touch drag delivers to the stage on a phone (pointer and touch events, the camera). */
import { createRequire } from 'node:module';
import { join } from 'node:path';
const require = createRequire(join(process.env.QA_COPY, 'package.json'));
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const [W, H, DPR, URL_] = [Number(process.argv[2] ?? 400), Number(process.argv[3] ?? 860), Number(process.argv[4] ?? 1), process.argv[5] ?? '/rooms/living-room/'];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-background-networking'] });
const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: W, height: H }, deviceScaleFactor: DPR, isMobile: true, hasTouch: true });
const p = await ctx.newPage();
const cdp = await ctx.newCDPSession(p);
await p.goto(`${BASE}${URL_}`, { waitUntil: 'load' });
await p.locator('button.hotspot').first().waitFor({ state: 'attached', timeout: 30000 });
await p.evaluate(() => {
  window.__ev = [];
  const st = document.querySelector('section.stage');
  for (const t of ['pointerdown', 'pointermove', 'pointerup', 'pointercancel', 'touchstart', 'touchmove', 'touchend', 'touchcancel', 'click'])
    st.addEventListener(t, (e) => window.__ev.push(`${t}${e.clientX !== undefined ? `@${Math.round(e.clientX)}` : ''}${e.target?.className ? `:${String(e.target.className).slice(0, 20)}` : ''}`), { capture: true, passive: true });
});
const sb = await p.locator('section.stage').boundingBox();
const y = Math.round(sb.y + Math.min(sb.height, H - sb.y) * 0.55);
const td = (type, x, yy) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: type === 'touchEnd' ? [] : [{ x, y: yy, id: 1 }] });
// start the engine with a tap
await td('touchStart', 20, y); await sleep(50); await td('touchEnd'); 
for (let i = 0; i < 120 && !(await p.evaluate(() => window.__hdEngine?.ready)); i++) await sleep(250);
await sleep(800);
const cam = () => p.evaluate(() => ({ cu: window.__hdEngine?.cam?.cu, canPan: !!document.querySelector('.stage-actions button[aria-label^="הזזת המבט"]'), vase: Math.round(document.querySelector('button.hotspot[data-slot="vase"]')?.getBoundingClientRect().left ?? NaN) }));
console.log('ready', JSON.stringify(await cam()), 'stage', JSON.stringify(sb), 'y', y);
await p.evaluate(() => (window.__ev = []));
for (const [label, x0, x1] of [['finger right', Math.round(W * 0.3), Math.round(W * 0.7)], ['finger left', Math.round(W * 0.7), Math.round(W * 0.3)]]) {
  await td('touchStart', x0, y);
  for (let k = 1; k <= 8; k++) { await sleep(16); await td('touchMove', Math.round(x0 + ((x1 - x0) * k) / 8), y); }
  await sleep(16); await td('touchEnd'); await sleep(300);
  const ev = await p.evaluate(() => window.__ev.splice(0));
  console.log(label, JSON.stringify(await cam()), ev.length, JSON.stringify(ev.slice(0, 6)), '…', JSON.stringify(ev.slice(-4)));
}
// the engine's own pan buttons, if any
const btns = await p.evaluate(() => [...document.querySelectorAll('.stage-actions button')].map((b) => b.getAttribute('aria-label')));
console.log('stage buttons', JSON.stringify(btns));
await browser.close();
