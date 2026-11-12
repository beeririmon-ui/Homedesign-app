/**
 * The evidence of S10 (the warm-modern house in the room engine): the stage at 400 and 1280 with each of the three sets,
 * the wheel on each set, the switch between the houses half way, and its timings (press → end, the dissolve itself, at
 * full motion and reduced), against the local production build with its API.
 * Runs only as `HD_SHOTS_DIR=<dir> npx --no-install playwright test --project=evidence e2e/shots-s10.spec.ts`; never part of e2e.
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const DIR = process.env.HD_SHOTS_DIR ?? '';
const HOUSE = '/rooms/living-room/?style=warm-modern';
const SETS = ['B', 'A', 'C'];
const evidence: Record<string, unknown> = {};
type Times = { from: string; to: string; asked: number; start: number; end: number };

test.skip(!DIR, 'evidence only: set HD_SHOTS_DIR');
test.beforeAll(() => mkdirSync(join(DIR, 'screens'), { recursive: true }));
test.afterAll(() => {
  if (DIR) writeFileSync(join(DIR, 'timings.json'), JSON.stringify(evidence, null, 1));
});

async function shot(page: Page, name: string): Promise<void> {
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(500);
  await page.screenshot({ path: join(DIR, 'screens', `${name}.png`) });
}
const times = (page: Page) => page.evaluate(() => (window as unknown as { __hdHouseSwitch?: Times }).__hdHouseSwitch ?? null);
const ready = (page: Page) =>
  expect.poll(() => page.evaluate(() => !!(window as unknown as { __hdEngine?: { ready: boolean } }).__hdEngine?.ready), { timeout: 20_000 }).toBe(true);

for (const [w, h, tag] of [
  [400, 800, 'phone'],
  [1280, 800, 'desk'],
] as const) {
  test(`the three sets at ${w}`, async ({ page }) => {
    await page.setViewportSize({ width: w, height: h });
    await page.goto(HOUSE);
    const spot = page.locator('button.hotspot[data-slot="cushions"]');
    await expect(spot).toBeAttached({ timeout: 20_000 });
    await shot(page, `${tag}-${w}-0-house-at-rest`);
    const loaded: string[] = [];
    page.on('request', (r) => {
      if (r.url().includes('/media/house/')) loaded.push(r.url().replace(/^.*\/media\//, ''));
    });
    for (const [i, id] of SETS.entries()) {
      await spot.click({ force: true });
      const dialog = page.getByRole('dialog');
      await expect(dialog).toBeVisible({ timeout: 15_000 });
      // the keyboard, from the first set (a press on the current card would choose it and close the wheel)
      await page.keyboard.press('Home');
      for (let k = 0; k < i; k++) await page.keyboard.press('ArrowLeft');
      await expect(dialog.getByRole('radio').nth(i)).toHaveAttribute('aria-checked', 'true');
      await page.waitForTimeout(600);
      await shot(page, `${tag}-${w}-${i + 1}-wheel-set-${id}`);
      await dialog.getByRole('button', { name: 'בחירה והצגה בחדר' }).click();
      await expect(dialog).toBeHidden({ timeout: 10_000 });
      await page.waitForTimeout(1400);
      await page.mouse.move(0, 0);
      await page.waitForTimeout(3500); // the marks fade: the room at rest, clean
      await shot(page, `${tag}-${w}-${i + 1}-room-set-${id}`);
    }
    await ready(page);
    evidence[`files_${tag}`] = [...new Set(loaded)].sort();
  });
}

test('the switch between the houses, timed (1280)', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto('/rooms/living-room/');
  await expect(page.locator('button.hotspot').first()).toBeAttached({ timeout: 20_000 });
  await shot(page, 'desk-1280-switch-0-nordic');
  await page.locator('.segmented button[data-house="warm-modern"]').click();
  await expect.poll(() => times(page), { timeout: 20_000 }).not.toBeNull();
  // half way through a second switch, back to the Nordic house
  const before = await times(page);
  await page.waitForTimeout(1200);
  await shot(page, 'desk-1280-switch-1-warm-modern');
  await page.locator('.segmented button[data-house="nordic"]').click();
  await expect.poll(async () => (await times(page))?.to, { timeout: 20_000 }).toBe('nordic');
  const back = await times(page);
  await page.locator('.segmented button[data-house="warm-modern"]').click();
  await page.waitForFunction(() => {
    const t = (window as unknown as { __hdHouseSwitch?: Times }).__hdHouseSwitch;
    return t?.to === 'nordic' && performance.now() - t.end > 0;
  });
  await page.waitForTimeout(650);
  await shot(page, 'desk-1280-switch-2-half-way');
  await expect.poll(async () => (await times(page))?.to, { timeout: 20_000 }).toBe('warm-modern');
  const again = await times(page);
  const ms = (t: Times | null) => t && { dissolve_ms: Math.round(t.end - t.start), press_to_end_ms: Math.round(t.end - t.asked), from: t.from, to: t.to };
  evidence['switch_full_motion'] = [ms(before), ms(back), ms(again)];
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.locator('.segmented button[data-house="nordic"]').click();
  await expect.poll(async () => (await times(page))?.to, { timeout: 20_000 }).toBe('nordic');
  evidence['switch_reduced_motion'] = ms(await times(page));
});
