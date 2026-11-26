/**
 * MOCK7 (2026-11-26), the full tour in design C with the walks between rooms in code
 * (briefs/site-mock7-tour-transitions-2026-11-26.md, and the coordinator's update: the living room is M0-W), behind
 * HD_PUBLIC=0:
 *
 *  1. design C is the preview's look without a flag; ?design=0 keeps the look before FB13;
 *  2. the arrival: the walk stops in the hall (frame 490, before the old table enters the opening), the push walks on
 *     into the living room M0-W, and the room lands on the plain composition of its layers; nothing of the old living
 *     room is asked for (the phase 2 files, the house's old base, the story);
 *  3. the living room M0-W at rest: a mark for each of its 13 products, the coffee table "עוד לא במכירה", no wheel, no
 *     style change;
 *  4. the walk between rooms, in the route's order: each room button walks (a push of 0.8–1.4 s) and lands on the plain
 *     composition; its two ends are the frames before and after it, to the value;
 *  5. reduced motion: the rooms dissolve, nothing walks (no depth is ever uploaded).
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
async function more(page: Page) {
  if ((await page.locator('#tour-fold').getAttribute('aria-expanded')) !== 'true') await page.locator('#tour-fold').click();
  await page.waitForFunction(() => window.__hdTourState?.more === true && window.__hdTour?.busy === false);
}
const hashes = (page: Page) =>
  page.evaluate(() => {
    const fnv = (a: Uint8Array) => {
      let h = 0x811c9dc5;
      for (let i = 0; i < a.length; i++) h = Math.imul(h ^ a[i]!, 0x01000193) >>> 0;
      return h;
    };
    const e = window.__hdTour!;
    const composition = fnv(e.read([0, 0, e.gl.width, e.gl.height]));
    e.render();
    return { composition, screen: fnv(e.gl.readScreen().data) };
  });
async function plain(page: Page, room: string) {
  await page.goto(`/tour/?skip=1&room=${room}`);
  await ready(page);
  await atRest(page);
  return hashes(page);
}
/** the route's rooms after the living room, by their buttons, and the frame each lands on (tools/tour/frames.json) */
const ROUTE = [
  ['dining', 'dining'],
  ['boy', 'boy'],
  ['girl', 'girl'],
  ['bath', 'bath-b1'],
  ['master', 'master'],
  ['work', 'work'],
] as const;
/** what the old living room is made of: none of it is ever asked for */
const OLD = /phase2-2026-11-10|\/media\/house\/living-room\/warm-modern\/|\/tour\/living-room\/warm-modern\/M0\/|\/story\//;

test.describe('MOCK7: the full tour in design C, with the walks between rooms', () => {
  test.describe.configure({ timeout: 400_000 });

  test('design C is the preview’s look; ?design=0 keeps the look before FB13', async ({ page }) => {
    await page.goto('/tour/?skip=1');
    await ready(page);
    expect(await page.evaluate(() => document.documentElement.dataset.design)).toBe('c');
    await page.goto('/tour/?skip=1&design=0');
    await ready(page);
    expect(await page.evaluate(() => document.documentElement.dataset.design ?? null)).toBeNull();
    // kept for the tab
    await page.goto('/tour/?skip=1');
    await ready(page);
    expect(await page.evaluate(() => document.documentElement.dataset.design ?? null)).toBeNull();
    await page.goto('/tour/?skip=1&design=c');
    await ready(page);
    expect(await page.evaluate(() => document.documentElement.dataset.design)).toBe('c');
  });

  test('the arrival: the walk stops in the hall, the push walks into M0-W, and nothing of the old room is asked for', async ({ page }) => {
    const want = await plain(page, 'living-room');
    const asked: string[] = [];
    page.on('request', (r) => asked.push(r.url()));
    await page.goto('/tour/');
    await ready(page);
    await page.locator('#tour-enter').click();
    await page.waitForFunction(() => (window.__hdTourState?.walk ?? 0) > 30, undefined, { timeout: 60_000 });
    // the walk's file ends at frame 490 (the old table enters the opening at 493)
    const dur = await page.locator('video.tour-video').evaluate((v: HTMLVideoElement) => v.duration);
    expect(dur * 60).toBeLessThan(491);
    await atRest(page);
    const fx = await page.evaluate(() => {
      const e = window.__hdTour!;
      const f = e.frames['arrive-living'];
      return { frames: f?.dt.length ?? 0, ms: f ? f.dt.reduce((a, b) => a + b, 0) : 0, room: window.__hdTourState!.room };
    });
    note('arrival-push.json', fx);
    expect(fx.room).toBe('living-room');
    expect(fx.frames, 'the push from the hall ran as an effect').toBeGreaterThan(3);
    expect(fx.ms).toBeGreaterThan(800);
    // the room it lands in rests on the plain composition
    expect(await hashes(page)).toEqual(want);
    expect(asked.filter((u) => OLD.test(u))).toEqual([]);
  });

  test('the living room M0-W at rest: 13 marks, the coffee table not sold yet, no wheel, no style change', async ({ page }) => {
    await page.goto('/tour/?skip=1');
    await ready(page);
    await atRest(page);
    await expect(page.locator('.tour-spot')).toHaveCount(13);
    await expect(page.locator('.tour-spot[data-slot="coffee-table"]')).toHaveAttribute('aria-label', /עוד לא במכירה/);
    await more(page);
    await expect(page.locator('.tour-style')).toHaveCount(0);
    expect(await page.evaluate(() => window.__hdTourState!.room)).toBe('living-room');
  });

  test('the walk between rooms, in the route’s order: a push of 0.8–1.4 s, seamless at both ends, landing on the plain composition', async ({ page }) => {
    const want: Record<string, { composition: number; screen: number }> = {};
    for (const [, frame] of ROUTE) want[frame] = await plain(page, frame);
    await page.goto('/tour/?skip=1');
    await ready(page);
    await atRest(page);
    const seen: Record<string, unknown> = {};
    for (const [btn, frame] of ROUTE) {
      await more(page);
      await page.locator(`#tour-${btn}`).click();
      await page.waitForFunction((x) => window.__hdTourState?.room === x, frame);
      await atRest(page);
      const r = await page.evaluate((f) => {
        const e = window.__hdTour!;
        const l = e.frames[`room-${f}`];
        return { frames: l?.dt.length ?? 0, ms: l ? l.dt.reduce((a, b) => a + b, 0) : 0 };
      }, frame);
      seen[frame] = r;
      expect(r.frames, `${frame}: the walk ran`).toBeGreaterThan(3);
      expect(r.ms, `${frame}: 0.8–1.4 s`).toBeGreaterThan(800);
      expect(r.ms, `${frame}: 0.8–1.4 s (and a frame's slack)`).toBeLessThan(1400 + 250);
      expect(await hashes(page), `${frame} rests on the plain composition of its layers`).toEqual(want[frame]);
    }
    // the ends of a walk, to the value: the first frame is the frame before it, the last the frame after it
    const seams = await page.evaluate(async () => {
      const e = window.__hdTour!;
      e.sync = true;
      e.seams = [];
      return e.seams;
    });
    expect(seams).toEqual([]);
    await more(page);
    await page.locator('#tour-dining').click();
    await page.waitForFunction(() => window.__hdTourState?.room === 'dining');
    await atRest(page);
    const s = await page.evaluate(() => window.__hdTour!.seams.filter((x) => x.label === 'room-dining'));
    note('walks.json', { seen, seams: s });
    expect(s).toHaveLength(1);
    expect(s[0]!.first.max, 'the walk’s first frame is the frame before it').toBe(0);
    expect(s[0]!.last.max, 'the walk’s last frame is the frame after it').toBe(0);
  });

  test('reduced motion: the rooms dissolve, nothing walks', async ({ browser }) => {
    const ctx = await browser.newContext({ reducedMotion: 'reduce', locale: 'he-IL' });
    const page = await ctx.newPage();
    await page.goto('/tour/?skip=1');
    await ready(page);
    await atRest(page);
    await more(page);
    await page.locator('#tour-dining').click();
    await page.waitForFunction(() => window.__hdTourState?.room === 'dining');
    await atRest(page);
    const depth = await page.evaluate(() => (window.__hdTour!.gl as unknown as { has(k: string): boolean }).has('dining:depth'));
    expect(depth, 'no depth is uploaded: no push runs').toBe(false);
    await ctx.close();
  });
});
