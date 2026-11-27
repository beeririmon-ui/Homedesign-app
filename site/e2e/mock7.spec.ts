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
 *  5. reduced motion: the rooms dissolve, nothing walks (no depth is ever uploaded);
 *  6. FB20 (2026-11-26, briefs/site-wheel-3d-2026-11-26.md), the 3D wheel: the bedroom's throw on a ring (the cushion
 *     sets A and C of M0-W are not in yet), the room dimmed while it is open, turning it never changes the room, the
 *     choice lifts the dim as the product cross-fades in (600–900 ms), a cancel changes nothing; reduced motion; a ring
 *     of ten (the fixture) turned by the keys and the mouse's wheel, only the card it rests on asked for.
 *
 * The numbers go to the evidence when HD_EVIDENCE_DIR is set.
 */
import { test, expect, type Page } from '@playwright/test';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

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
  // MOCK9 (FB21): the owner's guided route; its first leg is a clip (e2e/mock9.spec.ts), the others walk in code
  ['dining', 'dining'],
  ['bath', 'bath-b1'],
  ['master', 'master'],
  ['boy', 'boy'],
  ['girl', 'girl'],
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
    // MOCK8: the walk is FB19's (K-A2 to the hall and the push in code, or the final walk into M0-W fix1)
    const end = (JSON.parse(readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), '../.generated/arrival.json'), 'utf8')) as { end: string }).end;
    // MOCK8 (FB19): the walk goes on by pushes ("המשך" is one)
    for (let i = 0; i < 600 && (await page.evaluate(() => window.__hdTourState?.phase)) !== 'room'; i++) {
      if (await page.evaluate(() => window.__hdTourState?.walkRest === true)) await page.locator('#tour-walk-next').click();
      await page.waitForTimeout(200);
    }
    await atRest(page);
    const fx = await page.evaluate(() => {
      const e = window.__hdTour!;
      const f = e.frames['arrive-living'];
      return { frames: f?.dt.length ?? 0, ms: f ? f.dt.reduce((a, b) => a + b, 0) : 0, room: window.__hdTourState!.room };
    });
    note('arrival-push.json', fx);
    expect(fx.room).toBe('living-room');
    if (end === 'still') {
      expect(fx.frames, 'the push from the hall ran as an effect').toBeGreaterThan(3);
      expect(fx.ms).toBeGreaterThan(800);
    }
    // the room it lands in rests on the plain composition
    expect(await hashes(page)).toEqual(want);
    expect(asked.filter((u) => OLD.test(u))).toEqual([]);
  });

  // MOCK8: M0-W's fix1 stack adds the curtain (14 marks), and the cushion sets are its wheel (e2e/mock8.spec.ts)
  test('the living room M0-W at rest: 14 marks, the coffee table not sold yet, no style change', async ({ page }) => {
    await page.goto('/tour/?skip=1');
    await ready(page);
    await atRest(page);
    await expect(page.locator('.tour-spot')).toHaveCount(14);
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
      if (btn === 'dining') {
        // MOCK9: living → kitchen is leg 1's clip, not a push (e2e/mock9.spec.ts); it lands on the same composition
        expect(await hashes(page), `${frame} rests on the plain composition of its layers`).toEqual(want[frame]);
        continue;
      }
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
    // MOCK9: one station back (the fade through the light), then one ahead on a leg that walks in code
    await more(page);
    await page.locator('#tour-girl').click();
    await page.waitForFunction(() => window.__hdTourState?.room === 'girl');
    await atRest(page);
    await more(page);
    await page.locator('#tour-work').click();
    await page.waitForFunction(() => window.__hdTourState?.room === 'work');
    await atRest(page);
    const s = await page.evaluate(() => window.__hdTour!.seams.filter((x) => x.label === 'room-work'));
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

  // ---------- FB20: the 3D wheel ----------
  const checked = (page: Page) => page.locator('.arc.ring .arc-card[aria-checked="true"]').getAttribute('aria-label');
  async function openThrow(page: Page) {
    await page.locator('.tour-spot[data-slot="throw"]').click({ force: true });
    await expect(page.getByRole('dialog')).toBeVisible();
    await atRest(page);
  }

  test('FB20, the 3D wheel: the throw on a ring over the dimmed room; turning it never changes the room; the choice is revealed', async ({ page }) => {
    await page.goto('/tour/?skip=1&room=master');
    await ready(page);
    await atRest(page);
    await openThrow(page);
    await expect(page.locator('.picker[data-ring] .arc.ring .arc-card')).toHaveCount(3);
    await expect(page.locator('.ring-track')).toHaveCount(1);
    const open = await page.evaluate(() => ({ ev: window.__hdTour!.d.ev, vig: window.__hdTour!.d.vig }));
    expect(open.ev, 'the room is dimmed while the wheel is open').toBeLessThan(-0.5);
    expect(open.vig).toBeGreaterThan(0);
    // the ring closes on itself: → from the first is the last; ← the next (right to left)
    expect(await checked(page)).toMatch(/^1 מתוך 3/);
    await page.keyboard.press('ArrowRight');
    await expect.poll(() => checked(page)).toMatch(/^3 מתוך 3/);
    await page.keyboard.press('ArrowLeft');
    await page.keyboard.press('ArrowLeft');
    await expect.poll(() => checked(page)).toMatch(/^2 מתוך 3/);
    // a drag turns it too; the room under it stays as it was
    const box = (await page.locator('.arc.ring').boundingBox())!;
    await page.mouse.move(box.x + box.width * 0.35, box.y + box.height * 0.8);
    await page.mouse.down();
    for (let i = 1; i <= 8; i++) {
      await page.mouse.move(box.x + box.width * 0.35 + i * 12, box.y + box.height * 0.8);
      await page.waitForTimeout(16);
    }
    await page.mouse.up();
    await page.waitForFunction(() => !window.__hdTour!.busy && document.querySelectorAll('.arc-card[aria-checked="true"]').length === 1);
    expect(await page.evaluate(() => window.__hdTour!.selection['throw'])).toBe(1);
    await page.locator('.arc-card[aria-checked="true"]').focus();
    await page.keyboard.press('Home');
    await page.keyboard.press('ArrowLeft');
    await expect.poll(() => checked(page)).toMatch(/^2 מתוך 3/);
    // the choice: the dim lifts as the product comes into the room
    await page.getByRole('button', { name: 'בחירה והצגה בחדר' }).click();
    await expect(page.getByRole('dialog')).toBeHidden();
    await atRest(page);
    const chosen = await page.evaluate(() => {
      const e = window.__hdTour!;
      const f = e.frames['select-reveal'];
      return { sel: e.selection['throw'], ev: e.d.ev, vig: e.d.vig, frames: f?.dt.length ?? 0, ms: f ? f.dt.reduce((a, b) => a + b, 0) : 0 };
    });
    note('wheel3d-reveal.json', { open, chosen });
    expect(chosen.sel).toBe(2);
    expect(chosen.ev).toBe(0);
    expect(chosen.vig).toBe(0);
    expect(chosen.frames, 'the reveal ran as an effect').toBeGreaterThan(3);
    expect(chosen.ms, 'about 600–900 ms').toBeGreaterThan(600);
    expect(chosen.ms, 'about 600–900 ms (and a frame’s slack)').toBeLessThan(900 + 250);
    const after = await hashes(page);
    // a cancel changes nothing: the room rests on the same composition
    await openThrow(page);
    await page.keyboard.press('ArrowLeft');
    await expect.poll(() => checked(page)).toMatch(/^3 מתוך 3/);
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).toBeHidden();
    await atRest(page);
    expect(await page.evaluate(() => [window.__hdTour!.selection['throw'], window.__hdTour!.d.ev])).toEqual([2, 0]);
    expect(await hashes(page)).toEqual(after);
  });

  test('FB20, reduced motion: the ring turns at once, the choice lands at once', async ({ browser }) => {
    const ctx = await browser.newContext({ reducedMotion: 'reduce', locale: 'he-IL' });
    const page = await ctx.newPage();
    await page.goto('/tour/?skip=1&room=master');
    await ready(page);
    await atRest(page);
    await openThrow(page);
    await page.keyboard.press('ArrowLeft');
    expect(await checked(page)).toMatch(/^2 מתוך 3/);
    await page.keyboard.press('Enter');
    await expect(page.getByRole('dialog')).toBeHidden();
    await atRest(page);
    const r = await page.evaluate(() => ({
      sel: window.__hdTour!.selection['throw'],
      ev: window.__hdTour!.d.ev,
      frames: window.__hdTour!.frames['select-reveal']?.dt.length ?? 0,
    }));
    expect(r).toEqual({ sel: 2, ev: 0, frames: 0 });
    await ctx.close();
  });

  test('FB20, a ring of ten (the fixture): the keys and the mouse’s wheel turn it; only the card it rests on is asked for', async ({ page }) => {
    const want = await plain(page, 'boy');
    await page.goto('/tour/?skip=1&room=boy&fixture=wheel10');
    await ready(page);
    await atRest(page);
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.locator('.arc.ring .arc-card')).toHaveCount(10);
    const count = page.locator('.ring-count');
    await expect(count).toHaveText('1 / 10');
    await page.keyboard.press('End');
    await expect(count).toHaveText('10 / 10');
    await expect.poll(async () => (await page.evaluate(() => window.__hdWheelFixture!)).shown).toBe(10);
    await page.keyboard.press('Home');
    await expect(count).toHaveText('1 / 10');
    await expect.poll(async () => (await page.evaluate(() => window.__hdWheelFixture!)).shown).toBe(1);
    const before = (await page.evaluate(() => window.__hdWheelFixture!)).loads.length;
    // the mouse's wheel: a turn of a few cards, then one rest
    const box = (await page.locator('.arc.ring').boundingBox())!;
    await page.mouse.move(box.x + box.width / 2, box.y + box.height * 0.7);
    for (let i = 0; i < 6; i++) await page.mouse.wheel(0, 60);
    await expect(count).not.toHaveText('1 / 10');
    const at = Number((await count.textContent())!.split(' / ')[0]);
    await expect.poll(async () => (await page.evaluate(() => window.__hdWheelFixture!)).shown).toBe(at);
    const loads = (await page.evaluate(() => window.__hdWheelFixture!)).loads.slice(before);
    expect(loads, 'the cards passed on the way are never asked for').toEqual([at]);
    expect(await hashes(page)).toEqual(want);
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).toBeHidden();
  });
});
