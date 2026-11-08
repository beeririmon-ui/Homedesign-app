/**
 * qa-agent, 2026-11-07 (S3-S5): the wheel's spring in wall-clock time. The vase's wheel, a drag of 40 % (as flow.spec),
 * then the first card's rotateY sampled every frame until it holds still for 300 ms: the settle time after release, the
 * frame rate meanwhile, and when aria-checked changed. Run idle and under the caller's CPU load (QA_LOAD=1 just labels it).
 *   QA_BASE=http://127.0.0.1:8799 node wheel-settle.mjs out.json [runs]
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium, devices } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const RUNS = Number(process.argv[3] ?? 4);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const out = [];
for (let r = 0; r < RUNS; r++) {
  const ctx = await browser.newContext({ ...devices['Desktop Chrome'], locale: 'he-IL' });
  const page = await ctx.newPage();
  await page.goto(`${BASE}/rooms/living-room/`);
  await page.locator('button.hotspot').first().waitFor({ state: 'attached', timeout: 30000 });
  await page.locator('.stage').dispatchEvent('pointerdown');
  await page.waitForFunction(() => window.__hdEngine?.ready === true, undefined, { timeout: 30000 });
  await page.locator('button.hotspot[data-slot="vase"]').click();
  const arc = page.locator('.arc');
  await arc.waitFor({ state: 'visible' });
  await page.waitForTimeout(800);
  const box = await arc.boundingBox();
  const y = box.y + box.height / 2;
  await page.evaluate(() => {
    window.__qs = { samples: [], checked: null, up: null };
    document.addEventListener('pointerup', () => (window.__qs.up = performance.now()), true);
    new MutationObserver((ms) => {
      for (const m of ms) if (m.attributeName === 'aria-checked' && m.target.getAttribute('aria-checked') === 'true' && window.__qs.up && !window.__qs.checked) window.__qs.checked = performance.now();
    }).observe(document.body, { subtree: true, attributes: true, attributeFilter: ['aria-checked'] });
    const card = () => document.querySelector('.arc [style*="rotateY"]');
    const loop = () => {
      const c = card();
      window.__qs.samples.push([performance.now(), c ? c.style.transform : '']);
      if (window.__qs.samples.length < 3000) requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  });
  await page.mouse.move(box.x + box.width * 0.3, y);
  await page.mouse.down();
  for (let i = 1; i <= 8; i++) await page.mouse.move(box.x + box.width * (0.3 + i * 0.05), y);
  await page.mouse.up();
  await page.waitForTimeout(4000);
  const q = await page.evaluate(() => window.__qs);
  const after = q.samples.filter(([t]) => t >= q.up);
  let lastChange = q.up;
  for (let i = 1; i < after.length; i++) if (after[i][1] !== after[i - 1][1]) lastChange = after[i][0];
  const frames = after.filter(([t]) => t <= lastChange).length;
  const secs = (lastChange - q.up) / 1000;
  out.push({ run: r + 1, load: process.env.QA_LOAD === '1', settle_ms: Math.round(lastChange - q.up), fps_while_settling: secs > 0 ? Math.round((frames / secs) * 10) / 10 : null, checked_after_up_ms: q.checked ? Math.round(q.checked - q.up) : null });
  await ctx.close();
}
await browser.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(out, null, 1));
console.log(JSON.stringify(out));
