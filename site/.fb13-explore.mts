// FB13 exploration (temporary): the default tour's door, living room, close-up and rooms panel at 1280 and 400.
// Run from site/ as a copy: tsx .fb13-explore.mts <out dir> [design]
import { chromium, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';

const OUT = process.argv[2]!;
const design = process.argv[3] ?? '';
const BASE = 'http://127.0.0.1:8788';
mkdirSync(OUT, { recursive: true });
const b = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'],
});
const ready = (p: Page) => p.waitForFunction(() => window.__hdTour?.ready === true, undefined, { timeout: 60000 });
const rest = (p: Page) =>
  p.waitForFunction(() => window.__hdTourState?.phase === 'room' && window.__hdTourState.busy === false && window.__hdTour?.busy === false, undefined, {
    timeout: 120000,
  });
const still = (p: Page) => p.waitForFunction(() => document.getAnimations().every((a) => a.playState !== 'running'), undefined, { timeout: 15000 });
const d = design ? `&design=${design}` : '';
for (const [w, h] of [
  [1280, 720],
  [400, 860],
] as const) {
  const ctx = await b.newContext({ viewport: { width: w, height: h }, locale: 'he-IL' });
  const p = await ctx.newPage();
  p.on('pageerror', (e) => console.log('pageerror', e.message));
  const shot = (name: string) => p.screenshot({ path: join(OUT, `${w}-${name}.png`) });
  await p.goto(`${BASE}/tour/?x=1${d}`);
  await ready(p);
  await p.waitForTimeout(800);
  await shot('door');
  await p.goto(`${BASE}/tour/?skip=1&room=living-room${d}`);
  await ready(p);
  await rest(p);
  await still(p);
  await p.waitForTimeout(400);
  await shot('living');
  const slots = await p.evaluate(() => [...document.querySelectorAll('.tour-spot')].map((e) => (e as HTMLElement).dataset.slot));
  console.log(w, 'slots', slots.join(','));
  if (w === 1280) {
    // hover a mark
    await p.locator('#tour-fold').click();
    await p.waitForFunction(() => window.__hdTourState?.more === true && window.__hdTour?.busy === false);
    await still(p);
    await shot('nav');
    await p.keyboard.press('Escape');
    await p.waitForTimeout(600);
  }
  const slot = process.argv[4] ?? 'armchair';
  const tile = p.locator(`.tour-tile[data-slot="${slot}"]`);
  if (await tile.isVisible()) await tile.click();
  else await p.locator(`.tour-spot[data-slot="${slot}"]`).click({ force: true });
  await p.getByRole('dialog').waitFor();
  await rest(p);
  await still(p);
  await p.waitForTimeout(400);
  await shot('close');
  await ctx.close();
}
await b.close();
