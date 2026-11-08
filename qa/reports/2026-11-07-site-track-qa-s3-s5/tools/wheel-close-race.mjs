/**
 * qa-agent, 2026-11-07 (S3-S5): the wheel's close race. Drag the vase wheel (as flow.spec), release, and close the wheel
 * at once (Escape, 0 / 50 / 150 ms after release). What is checked at release, what the room's selection says after the
 * close, and what the wheel shows when opened again: all three must agree.
 *   QA_BASE=http://127.0.0.1:8799 node wheel-close-race.mjs out.json
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium, devices } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const out = [];
for (const [how, wait] of [['confirm', 0], ['confirm', 50], ['confirm', 150], ['confirm', 0], ['escape', 0], ['escape', 150]]) {
  const ctx = await browser.newContext({ ...devices['Desktop Chrome'], locale: 'he-IL' });
  const page = await ctx.newPage();
  await page.goto(`${BASE}/rooms/living-room/`);
  await page.locator('button.hotspot').first().waitFor({ state: 'attached', timeout: 30000 });
  await page.locator('.stage').dispatchEvent('pointerdown');
  await page.waitForFunction(() => window.__hdEngine?.ready === true, undefined, { timeout: 30000 });
  await page.locator('button.hotspot[data-slot="vase"]').click();
  const arc = page.locator('.arc');
  await arc.waitFor({ state: 'visible' });
  await page.waitForTimeout(600);
  const box = await arc.boundingBox();
  const y = box.y + box.height / 2;
  await page.mouse.move(box.x + box.width * 0.3, y);
  await page.mouse.down();
  for (let i = 1; i <= 8; i++) await page.mouse.move(box.x + box.width * (0.3 + i * 0.05), y);
  await page.mouse.up();
  const atRelease = await page.evaluate(() => document.querySelector('[role="radio"][aria-checked="true"]')?.getAttribute('aria-label')?.slice(0, 10));
  if (wait) await page.waitForTimeout(wait);
  if (how === 'escape') await page.keyboard.press('Escape');
  else await page.getByRole('button', { name: /בחירה והצגה בחדר/ }).click();
  await page.waitForTimeout(1500);
  const room = await page.evaluate(() => {
    const s = JSON.parse(localStorage.getItem('hd.selection') ?? localStorage.getItem('hd.room.selection') ?? 'null');
    const btn = document.querySelector('button.hotspot[data-slot="vase"]');
    return { stored: s?.vase ?? s?.['living-room']?.vase ?? null, hotspot_label: btn?.getAttribute('aria-label')?.slice(0, 60) ?? null, keys: Object.keys(localStorage) };
  });
  await page.locator('button.hotspot[data-slot="vase"]').click();
  await arc.waitFor({ state: 'visible' });
  await page.waitForTimeout(600);
  const reopened = await page.evaluate(() => document.querySelector('[role="radio"][aria-checked="true"]')?.getAttribute('aria-label')?.slice(0, 10));
  out.push({ how, after_release_ms: wait, at_release: atRelease, room_after_close: room, wheel_reopened: reopened, agree: how === 'escape' ? reopened?.startsWith('1 ') : atRelease === reopened });
  await ctx.close();
}
await browser.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(out, null, 1));
for (const o of out) console.log(JSON.stringify(o));
