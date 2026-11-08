/** qa-agent, 2026-11-07 (S3-S5): does "חזרה לסיפור" on the stage cover a hotspot (its 44 px target) or another control? */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const out = [];
for (const [w, h] of [[1280, 900], [1440, 900], [400, 860], [360, 740]]) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: w, height: h }, isMobile: w < 500, hasTouch: w < 500 });
  const p = await ctx.newPage();
  await p.goto(`${BASE}/rooms/living-room/?from=%2Fstory%2Fliving-room%2Fnordic%2F`);
  await p.locator('button.hotspot').first().waitFor({ state: 'attached', timeout: 30000 });
  await p.locator('.stage').dispatchEvent('pointerdown');
  await p.waitForFunction(() => window.__hdEngine?.ready === true, undefined, { timeout: 30000 }).catch(() => null);
  await p.waitForTimeout(1500);
  const r = await p.evaluate(() => {
    const a = document.getElementById('back-to-story');
    if (!a) return null;
    const b = a.getBoundingClientRect();
    const hit = (x) => { const c = x.getBoundingClientRect(); return !(c.right <= b.left || c.left >= b.right || c.bottom <= b.top || c.top >= b.bottom) && c.width > 0; };
    const others = [...document.querySelectorAll('.stage button, .stage a, .stage [role="button"]')].filter((x) => x !== a && hit(x) && getComputedStyle(x).visibility !== 'hidden');
    const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
    return { box: [b.left, b.top, b.width, b.height].map(Math.round), overlaps: others.map((x) => `${x.tagName.toLowerCase()}.${x.className.split(' ')[0]} ${x.dataset.slot ?? ''}`), on_top: top === a || a.contains(top) };
  });
  out.push({ viewport: `${w}x${h}`, ...r });
  await p.screenshot({ path: `/home/user/homedesign-app/qa/reports/2026-11-07-site-track-qa-s3-s5/overlays/room-back-link-${w}.png` });
  await ctx.close();
}
await browser.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(out, null, 1));
for (const o of out) console.log(JSON.stringify(o));
