/**
 * QA S6–S7 ת7: on a phone or a tablet the wheel opened off screen after the room was scrolled sideways: the stage (an
 * `overflow: hidden` box) had been scrolled from code by 362 px, and the room's canvas, the wheel and its scrim moved
 * with it, leaving a black screen. Now the stage never scrolls (`overflow: clip`, and a guard), the pan is the camera's,
 * and the wheel sits in the visible part of the stage (the visual viewport).
 *
 * In both houses (the Nordic one and the warm-modern one behind the flag), at 390, 400 and 720: the room is panned
 * sideways the way a finger does it, the stage's own scroll is tried the way QA did it (scrollBy), the product's mark is
 * tapped, and the wheel must be wholly inside the viewport and visible: the room behind it is the room, not a dark
 * layer. Screens for the evidence when HD_SHOTS_DIR is set.
 */
import { test, expect, type Page } from '@playwright/test';
import sharp from 'sharp';
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';

type Box = { x: number; y: number; width: number; height: number };
type Engine = { ready: boolean; cam: { cu: number } };
const SHOTS = process.env.HD_SHOTS_DIR ?? null;
const HOUSES = [
  { name: 'nordic', url: '/rooms/living-room/', slot: 'vase' },
  { name: 'warm-modern', url: '/rooms/living-room/?style=warm-modern', slot: 'cushions' },
];
const SIZES = [
  { width: 390, height: 844 },
  { width: 400, height: 860 },
  { width: 720, height: 1100 },
];

const camU = (page: Page) => page.evaluate(() => (window as unknown as { __hdEngine?: Engine }).__hdEngine?.cam.cu ?? null);
const markBox = (page: Page, slot: string) =>
  page.evaluate((s) => {
    const r = document.querySelector(`button.hotspot[data-slot="${s}"]`)!.getBoundingClientRect();
    return { x: r.left, y: r.top, width: r.width, height: r.height };
  }, slot);

/** one sideways stroke of a finger on the room (the engine's pan), `dir` +1 to the right, −1 to the left */
async function stroke(page: Page, dir: 1 | -1, y: number, x0: number) {
  const st = page.locator('section.stage');
  const ev = (type: string, x: number) => st.dispatchEvent(type, { pointerId: 11, pointerType: 'touch', isPrimary: true, clientX: x, clientY: y });
  await ev('pointerdown', x0);
  for (let k = 1; k <= 6; k++) await ev('pointermove', x0 + dir * k * 20);
  await ev('pointerup', x0 + dir * 120);
  await page.waitForTimeout(60);
}

/** pans the room sideways (away first, then back until the slot's mark is well inside the screen) */
async function panSideways(page: Page, slot: string, width: number) {
  const y = (await page.locator('section.stage').boundingBox())!.y + 300;
  const x0 = width / 2;
  const rest = await camU(page);
  const first = (await markBox(page, slot)).x < width / 2 ? -1 : 1;
  await stroke(page, first, y, x0);
  await stroke(page, first, y, x0);
  const moved = await camU(page);
  for (let i = 0; i < 16; i++) {
    const b = await markBox(page, slot);
    if (b.x > 50 && b.x + b.width < width - 50) break;
    await stroke(page, b.x < 50 ? 1 : -1, y, x0);
  }
  await page.waitForTimeout(250);
  return { rest, moved };
}

async function roomReady(page: Page, url: string) {
  await page.goto(url);
  await expect(page.locator('button.hotspot').first()).toBeAttached({ timeout: 20_000 });
  await page.locator('section.stage').dispatchEvent('pointerdown', { pointerId: 3, pointerType: 'touch', isPrimary: true, clientX: 5, clientY: 400 });
  await page.locator('section.stage').dispatchEvent('pointerup', { pointerId: 3, pointerType: 'touch', isPrimary: true, clientX: 5, clientY: 400 });
  await expect.poll(() => page.evaluate(() => (window as unknown as { __hdEngine?: Engine }).__hdEngine?.ready ?? false), { timeout: 20_000 }).toBe(true);
}

/** the wheel is open, wholly inside the viewport, over the room (not a dark layer) and the stage is not scrolled */
async function expectWheelOnScreen(page: Page, size: { width: number; height: number }, label: string) {
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible({ timeout: 15_000 });
  await page.waitForTimeout(1300); // the zoom (1 s) lands
  const inside = (b: Box | null) => !!b && b.x >= -0.5 && b.y >= -0.5 && b.x + b.width <= size.width + 0.5 && b.y + b.height <= size.height + 0.5;
  const d = await dialog.boundingBox();
  expect(inside(d), `${label}: the wheel's dialog ${JSON.stringify(d)} is inside ${size.width}×${size.height}`).toBe(true);
  expect(d!.width, `${label}: the wheel spans the stage's width`).toBeGreaterThan(size.width * 0.95);
  const card = await page.locator('[role="radio"][aria-checked="true"]').boundingBox();
  expect(inside(card), `${label}: the chosen option ${JSON.stringify(card)} is on screen`).toBe(true);
  const canvas = await page.locator('canvas.room-canvas').boundingBox();
  expect(canvas!.x, `${label}: the room's canvas is where the stage is`).toBeCloseTo(0, 0);
  expect(await page.locator('section.stage').evaluate((s) => [s.scrollLeft, s.scrollTop])).toEqual([0, 0]);
  // visible, not a dark layer: the room behind the wheel is a bright room (QA's black screen had a mean of ~20)
  const png = await page.screenshot({ clip: { x: d!.x, y: d!.y, width: d!.width, height: Math.min(d!.height, size.height - d!.y) } });
  const s = await sharp(png).greyscale().stats();
  const mean = s.channels[0]!.mean;
  const sd = s.channels[0]!.stdev;
  expect(mean, `${label}: the wheel's area is the lit room (mean ${mean.toFixed(1)})`).toBeGreaterThan(90);
  expect(sd, `${label}: the wheel's area has a picture in it (sd ${sd.toFixed(1)})`).toBeGreaterThan(12);
  if (SHOTS) {
    mkdirSync(SHOTS, { recursive: true });
    await page.screenshot({ path: join(SHOTS, `${label}.png`) });
  }
  return { dialog: d, card, mean, sd };
}

for (const h of HOUSES)
  test.describe(`ת7: the wheel on a phone after a sideways scroll, ${h.name}`, () => {
    for (const size of SIZES)
      test(`${size.width}: pan the room, try the stage's own scroll, tap the mark: the wheel is on screen`, async ({ browser }) => {
        const ctx = await browser.newContext({ viewport: size, isMobile: true, hasTouch: true, locale: 'he-IL' });
        const page = await ctx.newPage();
        await roomReady(page, h.url);
        // the stage's own scroll, as QA tried it: it does not move (the pan is the camera's)
        const tried = await page.evaluate(() => {
          const st = document.querySelector<HTMLElement>('section.stage')!;
          st.scrollBy({ left: -360, behavior: 'instant' });
          st.scrollLeft = -360;
          return [st.scrollLeft, st.scrollTop];
        });
        expect(tried, 'the stage never scrolls').toEqual([0, 0]);
        const { rest, moved } = await panSideways(page, h.slot, size.width);
        const canPan = await page.locator('.stage-actions button[aria-label^="הזזת המבט"]').count();
        if (canPan) expect(moved, 'the finger moved the room sideways').not.toBe(rest);
        const b = await markBox(page, h.slot);
        await page.touchscreen.tap(b.x + b.width / 2, b.y + b.height / 2);
        await expectWheelOnScreen(page, size, `wheel-${h.name}-${size.width}-after-pan`);
        // closing returns to the room, still unscrolled
        await page.getByRole('button', { name: 'סגירה וחזרה לחדר בלי שינוי' }).click();
        await expect(page.getByRole('dialog')).toHaveCount(0, { timeout: 5000 });
        expect(await page.locator('section.stage').evaluate((s) => s.scrollLeft)).toBe(0);
        await ctx.close();
      });
  });

test.describe('ת7: the other ways in', () => {
  test('a mark off screen activated from code (assistive tech), and a page scrolled past the stage: the wheel is on screen', async ({ browser }) => {
    const size = { width: 400, height: 860 };
    const ctx = await browser.newContext({ viewport: size, isMobile: true, hasTouch: true, locale: 'he-IL' });
    const page = await ctx.newPage();
    await roomReady(page, '/rooms/living-room/');
    const vase = await markBox(page, 'vase');
    expect(vase.x + vase.width < 0 || vase.x > size.width, 'the vase starts off screen on a phone').toBe(true);
    // Playwright's click scrolls an element into view first: that is what scrolled the stage in S6 (phone-3-wheel.png)
    await page.locator('button.hotspot[data-slot="vase"]').dispatchEvent('click');
    await expectWheelOnScreen(page, size, 'wheel-nordic-400-offscreen-mark');
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).toHaveCount(0, { timeout: 5000 });
    // the page scrolled down a little: the wheel brings the stage back under the header first (after the zoom out)
    await expect(page.locator('button.hotspot[data-slot="vase"]')).toBeEnabled({ timeout: 5000 });
    await page.evaluate(() => scrollTo({ top: 260, behavior: 'instant' }));
    const visible = await page.evaluate(() =>
      Array.from(document.querySelectorAll<HTMLElement>('button.hotspot'))
        .map((b) => ({ s: b.dataset.slot!, r: b.getBoundingClientRect(), v: getComputedStyle(b).visibility }))
        .find(({ r, v }) => v === 'visible' && r.top > 120 && r.bottom < 700 && r.left > 10 && r.right < 390),
    );
    expect(visible, 'a mark is on screen below the header').toBeTruthy();
    await page.touchscreen.tap(visible!.r.x + visible!.r.width / 2, visible!.r.y + visible!.r.height / 2);
    await expectWheelOnScreen(page, size, 'wheel-nordic-400-page-scrolled');
    await ctx.close();
  });
});
