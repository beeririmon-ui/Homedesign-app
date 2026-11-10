/** qa-agent, 2026-11-10 (S6-S7): §7.3, no dark scrim. The home page and the room with the wheel open: any element
 * larger than a quarter of the viewport whose background (color or gradient) is dark and translucent over the picture. */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OV = '/home/user/homedesign-app/qa/reports/2026-11-10-site-track-qa-s6-s7/overlays';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-background-networking', '--disable-features=PushMessaging,GCMChannelStatusRequest,MediaRouter'] });
const scrims = (p) =>
  p.evaluate(() => {
    const out = [];
    const area = innerWidth * innerHeight;
    for (const el of document.querySelectorAll('body *')) {
      const s = getComputedStyle(el);
      if (s.display === 'none' || s.visibility === 'hidden' || Number(s.opacity) === 0) continue;
      const r = el.getBoundingClientRect();
      if (r.width * r.height < area / 4) continue;
      const bg = s.backgroundColor;
      const m = /rgba?\((\d+), (\d+), (\d+)(?:, ([\d.]+))?\)/.exec(bg);
      const darkColor = m && Number(m[4] ?? 1) > 0.05 && Number(m[4] ?? 1) < 1 && (Number(m[1]) + Number(m[2]) + Number(m[3])) / 3 < 90;
      const darkGrad = /gradient/.test(s.backgroundImage) && /rgba\((0|1\d|2\d|3\d), ?\d+, ?\d+, ?0?\.[1-9]/.test(s.backgroundImage);
      if (darkColor || darkGrad || (s.backdropFilter && s.backdropFilter !== 'none')) out.push(`${el.tagName.toLowerCase()}.${(el.className?.toString() ?? '').split(' ')[0]} bg=${bg} img=${s.backgroundImage.slice(0, 60)} bf=${s.backdropFilter}`);
    }
    return out;
  });
const res = [];
for (const [w, h] of [[1280, 900], [400, 860]]) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: w, height: h }, isMobile: w < 500, hasTouch: w < 500 });
  const p = await ctx.newPage();
  await p.goto(`${BASE}/`, { waitUntil: 'load' });
  await p.waitForTimeout(1500);
  res.push({ width: w, state: 'home', scrims: await scrims(p) });
  await p.goto(`${BASE}/rooms/living-room/`);
  await p.locator('button.hotspot').first().waitFor({ state: 'attached', timeout: 30000 });
  await p.locator('.stage').dispatchEvent('pointerdown');
  await p.waitForFunction(() => window.__hdEngine?.ready === true, undefined, { timeout: 30000 }).catch(() => null);
  await p.locator('button.hotspot[data-slot="vase"]').click({ force: true });
  await p.locator('.arc').waitFor({ state: 'visible' });
  await p.waitForTimeout(900);
  res.push({ width: w, state: 'room, the wheel open', scrims: await scrims(p) });
  await p.screenshot({ path: `${OV}/room-wheel-open-${w}.png` });
  await ctx.close();
}
await browser.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(res, null, 1));
console.log(JSON.stringify(res, null, 1));
