/**
 * MOCK9 (2026-11-27, briefs/site-mock9-route-ui-2026-11-27.md), behind HD_PUBLIC=0, design C:
 *
 *  1. the logo intro (FB19): on a session's first load the wordmark plays in the middle and rises into the header; the
 *     next load has none; reduced motion has none (the wordmark is simply in the header);
 *  2. the route banner (FB21): at rest in a room it shows the station, the next one lit, and "הלאה"; the rail holds
 *     the seven stations in the owner's order;
 *  3. "הלאה" from the living room plays leg 1 (the clip) at its own pace into the kitchen, and lands on D1's own
 *     composition;
 *  4. the scroll scrubs leg 1 like the arrival: a push plays a stretch and rests, more pushes reach the kitchen;
 *  5. two stations ahead: the legs chained at ×2, leg 1 without its ease-out, leg 2 without its ease-in (MOCK11: its clip);
 *  6. back: the fade through the light, about 450 ms, no video;
 *  7. reduced motion: a plain dissolve, no leg plays.
 *
 * The numbers go to the evidence when HD_EVIDENCE_DIR is set.
 */
import { test, expect, type Page } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const note = (name: string, data: unknown) => {
  const dir = process.env.HD_EVIDENCE_DIR;
  if (!dir) return;
  mkdirSync(join(dir, 'data'), { recursive: true });
  writeFileSync(join(dir, 'data', name), JSON.stringify(data, null, 1));
};
const ready = (page: Page) => page.waitForFunction(() => window.__hdTour?.ready === true, undefined, { timeout: 60_000 });
const atRest = (page: Page) =>
  page.waitForFunction(() => window.__hdTourState?.phase === 'room' && window.__hdTourState.busy === false && window.__hdTour?.busy === false, undefined, {
    timeout: 120_000,
  });
const hashes = (page: Page) =>
  page.evaluate(() => {
    const fnv = (a: Uint8Array) => {
      let h = 0x811c9dc5;
      for (let i = 0; i < a.length; i++) h = Math.imul(h ^ a[i]!, 0x01000193) >>> 0;
      return h;
    };
    const e = window.__hdTour!;
    return fnv(e.read([0, 0, e.gl.width, e.gl.height]));
  });
const state = (page: Page) => page.evaluate(() => ({ ...window.__hdTourState! }));
/** a session without the intro (it is the first test's subject) */
const noIntro = (page: Page) => page.addInitScript(() => sessionStorage.setItem('hd-intro', '1'));
async function living(page: Page) {
  await noIntro(page);
  await page.goto('/tour/?skip=1');
  await ready(page);
  await atRest(page);
}

test.describe('MOCK9: the guided route, the refined interface, the logo intro', () => {
  test.describe.configure({ timeout: 300_000 });

  test('the logo intro: once a session, from the middle into the header; none under reduced motion', async ({ page, browser }) => {
    await page.goto('/tour/');
    await page.waitForFunction(() => window.__hdIntro === 'playing', undefined, { timeout: 30_000 });
    await expect(page.locator('.intro .wordmark')).toHaveText('הבית');
    // it starts in the middle, large
    const box = await page.locator('.intro .wordmark').boundingBox();
    const vp = page.viewportSize()!;
    expect(Math.abs(box!.x + box!.width / 2 - vp.width / 2)).toBeLessThan(40);
    expect(box!.height).toBeGreaterThan(60);
    await page.waitForFunction(() => window.__hdIntro === 'done', undefined, { timeout: 30_000 });
    await expect(page.locator('.intro')).toHaveCount(0);
    await expect(page.locator('html')).not.toHaveAttribute('data-intro', '');
    await expect(page.locator('.site-header .brand .wordmark')).toHaveText('הבית');
    // the door still answers under it: the page is the tour's door
    expect((await state(page)).phase).toBe('door');
    // the next load of the session: none
    await page.reload();
    await page.waitForFunction(() => window.__hdIntro !== undefined);
    expect(await page.evaluate(() => window.__hdIntro)).toBe('none');
    // reduced motion: none either, on a first load
    const ctx = await browser.newContext({ reducedMotion: 'reduce', locale: 'he-IL' });
    const p2 = await ctx.newPage();
    await p2.goto('/tour/');
    await p2.waitForFunction(() => window.__hdIntro !== undefined);
    expect(await p2.evaluate(() => window.__hdIntro)).toBe('none');
    await expect(p2.locator('.intro')).toHaveCount(0);
    await ctx.close();
  });

  test('the banner at rest: the station, the next lit, "הלאה"; the rail in the owner’s order', async ({ page }) => {
    await living(page);
    const route = page.getByRole('navigation', { name: 'מסלול הסיור' });
    await expect(route).toBeVisible();
    await expect(route.locator('.route-rail button .nm')).toHaveText(['סלון', 'מטבח', 'חדר רחצה', 'חדר שינה', 'חדר הילד', 'חדר הילדה', 'חדר עבודה']);
    await expect(route.locator('[data-k="here"] .nm')).toHaveText('סלון');
    await expect(route.locator('[data-k="here"]')).toHaveAttribute('aria-current', 'step');
    await expect(route.locator('[data-k="next"] .nm')).toHaveText('מטבח');
    await expect(page.locator('#route-next')).toHaveAttribute('aria-label', 'הלאה: מטבח');
    // over the picture's lower corner on a wide screen, inside the window
    const win = (await page.locator('.tour-win').boundingBox())!;
    const b = (await route.boundingBox())!;
    expect(b.y + b.height).toBeLessThanOrEqual(win.y + win.height + 1);
    expect(b.x).toBeGreaterThanOrEqual(win.x - 1);
    // it steps aside while a product is open
    await page.locator('.tour-spot[data-slot="cushions"]').click({ force: true });
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.locator('nav.route')).toHaveAttribute('data-off', '');
  });

  test('"הלאה" plays leg 1 at its own pace into the kitchen, and lands on D1’s own composition', async ({ page }) => {
    await noIntro(page);
    await page.goto('/tour/?skip=1&room=dining');
    await ready(page);
    await atRest(page);
    const d1 = await hashes(page);
    await page.goto('/tour/?skip=1');
    await ready(page);
    await atRest(page);
    await page.locator('#route-next').click();
    await page.waitForFunction(() => window.__hdTourState?.leg?.id === 'leg1', undefined, { timeout: 60_000 });
    await expect(page.locator('video.tour-leg[data-on]')).toHaveCount(1);
    expect(await page.locator('video.tour-leg[data-on]').getAttribute('src')).toMatch(/tour\/route\/leg1\.1920\.60\.mp4$/);
    // the banner follows: the kitchen is the station while the leg plays
    await expect(page.locator('.route [data-k="here"] .nm')).toHaveText('מטבח');
    await page.waitForFunction(() => window.__hdTourState?.room === 'dining');
    await atRest(page);
    const s = await state(page);
    note('next.json', s.trip);
    expect(s.trip).toMatchObject({ to: 'dining', kind: 'ahead', rate: 1 });
    expect(s.trip!.hops).toEqual([{ leg: 'leg1', real: true, start: 0, end: +(328 / 60).toFixed(4) }]);
    // the leg's own time (5.47 s) and its blends; not a jump
    expect(s.trip!.ms).toBeGreaterThan(5000);
    await expect(page.locator('video.tour-leg[data-on]')).toHaveCount(0);
    expect(await hashes(page), 'the kitchen at rest is D1’s own composition').toBe(d1);
    await expect(page.locator('#tour-title')).toContainText('מטבח');
    await expect(page.locator('#route-next')).toHaveAttribute('aria-label', 'הלאה: חדר רחצה');
  });

  test('the scroll scrubs leg 1 like the arrival: a push plays a stretch and rests; more reach the kitchen', async ({ page }) => {
    await living(page);
    const win = (await page.locator('.tour-win').boundingBox())!;
    await page.mouse.move(win.x + win.width / 2, win.y + win.height / 2);
    await page.mouse.wheel(0, 120);
    await page.waitForFunction(() => window.__hdTourState?.leg?.id === 'leg1', undefined, { timeout: 60_000 });
    await page.waitForFunction(() => window.__hdTourState?.leg?.rest === true, undefined, { timeout: 30_000 });
    const rested = (await state(page)).leg!;
    expect(rested.frame, 'it rests inside the leg').toBeGreaterThan(30);
    expect(rested.frame).toBeLessThan(300);
    await page.waitForTimeout(400);
    expect((await state(page)).leg!.frame, 'and stays where it rests').toBe(rested.frame);
    for (let i = 0; i < 8 && (await state(page)).room !== 'dining'; i++) {
      await page.mouse.wheel(0, 120);
      await page.waitForTimeout(1500);
    }
    await page.waitForFunction(() => window.__hdTourState?.room === 'dining', undefined, { timeout: 60_000 });
    await atRest(page);
    expect((await state(page)).trip).toMatchObject({ to: 'dining', kind: 'ahead', rate: 1 });
  });

  test('two stations ahead: chained at ×2, leg 1 without its ease-out, leg 2 without its ease-in', async ({ page }) => {
    await living(page);
    await page.locator('.route-rail button[data-g="bath"]').click();
    await page.waitForFunction(() => window.__hdTourState?.room === 'bath-b1', undefined, { timeout: 120_000 });
    await atRest(page);
    const s = await state(page);
    note('jump.json', s.trip);
    expect(s.trip).toMatchObject({ to: 'bath-b1', kind: 'ahead', rate: 2 });
    // MOCK11: leg 2 is its clip (994 frames at 60 fps, its ease-in frames 1–25), no longer the push in code
    expect(s.trip!.hops).toEqual([
      { leg: 'leg1', real: true, start: 0, end: +((296 - 2) / 60).toFixed(4) },
      { leg: 'leg2', real: true, start: +(25 / 60).toFixed(4), end: +(993 / 60).toFixed(4) },
    ]);
    // leg 1's stretch at ×2 (2.45 s) and leg 2's (8.07 s): well under the two legs' own pace (22 s)
    expect(s.trip!.ms).toBeLessThan(14_000);
    await expect(page.locator('.route [data-k="here"] .nm')).toHaveText('חדר רחצה');
    await expect(page.locator('.route [data-k="past"]')).toHaveCount(2);
  });

  test('back: the fade through the light, about 450 ms, no video', async ({ page }) => {
    await noIntro(page);
    await page.goto('/tour/?skip=1&room=master');
    await ready(page);
    await atRest(page);
    await page.evaluate(() => {
      const w = window as unknown as { __lit: number[]; __legs: number };
      w.__lit = [];
      w.__legs = 0;
      const tick = () => {
        const el = document.querySelector('.tour-light');
        if (el) w.__lit.push(+getComputedStyle(el).opacity);
        if (document.querySelector('video.tour-leg[data-on]')) w.__legs++;
        if (w.__lit.length < 600) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
    await page.locator('.route-rail button[data-g="dining"]').click();
    await page.waitForFunction(() => window.__hdTourState?.room === 'dining', undefined, { timeout: 60_000 });
    await atRest(page);
    const s = await state(page);
    const seen = await page.evaluate(() => {
      const w = window as unknown as { __lit: number[]; __legs: number };
      return { peak: Math.max(...w.__lit), legs: w.__legs };
    });
    note('back.json', { trip: s.trip, seen });
    expect(s.trip).toMatchObject({ to: 'dining', kind: 'back' });
    // the fade itself (up into the light and down onto the room); the room's change inside the full light is apart
    expect(s.trip!.ms).toBeGreaterThan(400);
    // (the GPU-less test machine draws a frame in 50–100 ms: the slack of the other walks' checks, MOCK7)
    expect(s.trip!.ms).toBeLessThan(450 + 250);
    // the fade as designed: 225 ms up into the light, 225 ms down onto the room
    const css = await page.evaluate(() => {
      const el = document.querySelector('.tour-light')!;
      const out = getComputedStyle(el).transitionDuration;
      document.querySelector('.tour')!.setAttribute('data-light', '');
      const up = getComputedStyle(el).transitionDuration;
      document.querySelector('.tour')!.removeAttribute('data-light');
      return { up, out };
    });
    expect(css).toEqual({ up: '0.225s, 0.225s', out: '0.225s, 0.225s' });
    expect(seen.peak, 'the window went up into the light').toBeGreaterThan(0.85);
    expect(seen.legs, 'no video plays backward').toBe(0);
  });

  test('reduced motion: a plain dissolve ahead, no leg plays', async ({ browser }) => {
    const ctx = await browser.newContext({ reducedMotion: 'reduce', locale: 'he-IL' });
    const page = await ctx.newPage();
    await page.goto('/tour/?skip=1');
    await ready(page);
    await atRest(page);
    await page.locator('#route-next').click();
    await page.waitForFunction(() => window.__hdTourState?.room === 'dining', undefined, { timeout: 60_000 });
    await atRest(page);
    expect((await state(page)).trip).toMatchObject({ to: 'dining', kind: 'ahead', hops: [] });
    await expect(page.locator('video.tour-leg[src]')).toHaveCount(0);
    await ctx.close();
  });
});
