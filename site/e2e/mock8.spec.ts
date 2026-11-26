/**
 * MOCK8 (2026-11-26, briefs/site-mock8-integrate-2026-11-26.md), one round that brings in what is new, behind
 * HD_PUBLIC=0, design C:
 *
 *  1. the arrival (FB19): K-A2 from the door to the hall, played by gentle scroll impulses — the press of "היכנסו" plays
 *     a stretch and the walk rests; a scroll of the mouse's wheel plays another; two or three reach the hall, from where
 *     the push walks into the living room, starting from exactly the frame on screen; forward only;
 *  2. reduced motion: a short fade, the door to the hall (HDx2 fb19) to the room: no walk plays, no push;
 *  3. the living room's cushion wheel: sets B (the default), A and C on the ring, each with its studio picture; a set
 *     chosen changes the cushions' rectangle only, and B again gives the room back to the value;
 *  4. the house light (FB16): each graded frame is the fb16 frame up to the finish's grain (the composition against the
 *     folder's fb16 finish, mean and p99), and far from the ungraded one; B1's glass multiplies; D1's pendant glow
 *     goes with its pendant.
 *
 * The numbers go to the evidence when HD_EVIDENCE_DIR is set.
 */
import { test, expect, type Page } from '@playwright/test';
import sharp from 'sharp';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const REPO = resolve(SITE, '..');
const note = (name: string, data: unknown) => {
  const dir = process.env.HD_EVIDENCE_DIR;
  if (!dir) return;
  mkdirSync(join(dir, 'data'), { recursive: true });
  writeFileSync(join(dir, 'data', name), JSON.stringify(data, null, 1));
};
const read = <T>(p: string): T => JSON.parse(readFileSync(p, 'utf8')) as T;
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
    const composition = fnv(e.read([0, 0, e.gl.width, e.gl.height]));
    e.render();
    return { composition, screen: fnv(e.gl.readScreen().data) };
  });
const state = (page: Page) => page.evaluate(() => ({ ...window.__hdTourState! }));
/** the composition, RGBA, top row first */
const composition = (page: Page) =>
  page.evaluate(() => {
    const e = window.__hdTour!;
    const a = e.read([0, 0, e.gl.width, e.gl.height]);
    let s = '';
    for (let i = 0; i < a.length; i += 0x8000) s += String.fromCharCode(...a.subarray(i, i + 0x8000));
    return { w: e.gl.width, h: e.gl.height, b64: btoa(s) };
  });

test.describe('MOCK8: the arrival by scroll, the cushion wheel, the studio pictures, the house light', () => {
  test.describe.configure({ timeout: 400_000 });

  test('the arrival: K-A2 by scroll impulses — a push plays a stretch and rests, 2–3 reach the hall, the push walks on', async ({ page }) => {
    await page.goto('/tour/?skip=1');
    await ready(page);
    await atRest(page);
    const want = await hashes(page);
    await page.goto('/tour/');
    await ready(page);
    const dur = await page.locator('video.tour-video').evaluate((v: HTMLVideoElement) => (v.readyState ? v.duration : 0));
    await page.locator('#tour-enter').click();
    // the first push: a stretch, then a rest well before the end
    await page.waitForFunction(() => window.__hdTourState?.walkRest === true && (window.__hdTourState.walk ?? 0) > 10, undefined, { timeout: 90_000 });
    const first = await state(page);
    const frames = await page.evaluate(() => Math.round(document.querySelector<HTMLVideoElement>('video.tour-video')!.duration * 60) + 1);
    expect(first.phase).toBe('entering');
    expect(first.walk, 'a push plays a stretch').toBeGreaterThan(0.15 * frames);
    expect(first.walk, 'and rests before the end').toBeLessThan(0.6 * frames);
    // it rests: the frame on screen stays
    await page.waitForTimeout(600);
    expect((await state(page)).walk).toBe(first.walk);
    // the mouse's wheel plays the next stretch (forward only)
    const box = (await page.locator('.tour-win').boundingBox())!;
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    const seen: number[] = [first.walk];
    for (let i = 0; i < 900 && (await state(page)).phase === 'entering'; i++) {
      const s = await state(page);
      if (s.walk) {
        expect(s.walk, 'the walk never goes back').toBeGreaterThanOrEqual(seen[seen.length - 1]!);
        seen.push(s.walk);
      }
      if (s.walkRest) {
        // the tests' run of the push (its two ends, to the value), from the last rest on
        await page.evaluate(() => void ((window.__hdTour!.sync = true), (window.__hdTour!.seams = [])));
        await page.mouse.wheel(0, 100);
        await page.waitForFunction(() => window.__hdTourState?.walkRest !== true || window.__hdTourState.phase !== 'entering', undefined, { timeout: 20_000 });
      }
      await page.waitForTimeout(100);
    }
    await atRest(page);
    const end = await page.evaluate(() => {
      const e = window.__hdTour!;
      const f = e.frames['arrive-living'];
      return { pushes: window.__hdTourState!.walkPushes, seams: e.seams.filter((x) => x.label === 'arrive-living'), push: f?.dt.length ?? 0, room: window.__hdTourState!.room };
    });
    note('arrival-mock8.json', { dur, frames, first: first.walk, pushes: end.pushes, seams: end.seams, walk: seen.filter((_, i) => i % 5 === 0) });
    expect(end.room).toBe('living-room');
    expect(end.pushes, 'two or three pushes reach the end').toBeGreaterThanOrEqual(2);
    expect(end.pushes).toBeLessThanOrEqual(3);
    // the push into the living room starts from exactly the walk's last frame on screen, and lands on the room
    expect(end.seams).toHaveLength(1);
    expect(end.seams[0]!.first.max, 'the push’s first frame is the still on screen').toBe(0);
    expect(end.seams[0]!.last.max, 'its last frame is the room').toBe(0);
    await page.evaluate(() => void (window.__hdTour!.sync = false));
    expect(await hashes(page)).toEqual(want);
  });

  test('reduced motion: a short fade, the door → the hall → the room; no walk, no push', async ({ browser }) => {
    const ctx = await browser.newContext({ reducedMotion: 'reduce', locale: 'he-IL' });
    const page = await ctx.newPage();
    await page.goto('/tour/');
    await ready(page);
    const t0 = Date.now();
    await page.locator('#tour-enter').click();
    await page.waitForFunction(() => document.querySelector('[data-hc]') !== null, undefined, { timeout: 60_000 });
    expect(await page.locator('img.tour-hc').getAttribute('src')).toMatch(/tour\/arrival\/hall\.1920\.webp$/);
    await atRest(page);
    const r = await page.evaluate(() => ({
      walk: window.__hdTourState!.walk,
      push: window.__hdTour!.frames['arrive-living']?.dt.length ?? 0,
      playing: !document.querySelector<HTMLVideoElement>('video.tour-video')!.paused,
    }));
    expect(r).toEqual({ walk: 0, push: 0, playing: false });
    expect(Date.now() - t0).toBeLessThan(30_000);
    await ctx.close();
  });

  test('the cushion wheel: sets B, A and C, each with its studio picture; a set changes the cushions only; B gives the room back', async ({ page }) => {
    await page.goto('/tour/?skip=1');
    await ready(page);
    await atRest(page);
    const want = await hashes(page);
    await page.locator('.tour-spot[data-slot="cushions"]').click({ force: true });
    await expect(page.getByRole('dialog')).toBeVisible();
    await atRest(page);
    const cards = page.locator('.picker[data-ring] .arc.ring .arc-card');
    await expect(cards).toHaveCount(3);
    // every card is the set's studio picture (the room's studio sheet), never its layer
    const hrefs = await page.locator('.picker[data-ring] .arc.ring .arc-card image').evaluateAll((els) => els.map((e) => e.getAttribute('href')));
    // (a card is drawn twice: sharp, and the blurred copy the ring shows it with behind)
    expect(hrefs.length).toBeGreaterThanOrEqual(3);
    for (const h of hrefs) expect(h).toMatch(/M0-W\/studio\.512\.webp$/);
    await page.keyboard.press('ArrowLeft');
    await page.getByRole('button', { name: 'בחירה והצגה בחדר' }).click();
    await expect(page.getByRole('dialog')).toBeHidden();
    await atRest(page);
    const a = await page.evaluate(() => window.__hdTour!.selection['cushions']);
    expect(a).toBe(2);
    const cA = await composition(page);
    // the set changed the cushions' rectangle only
    const rect = await page.evaluate(() => {
      const s = window.__hdTour!.slot('cushions');
      return s.rect;
    });
    await page.goto('/tour/?skip=1');
    await ready(page);
    await atRest(page);
    const cB = await composition(page);
    const A = Buffer.from(cA.b64, 'base64');
    const B = Buffer.from(cB.b64, 'base64');
    const [x0, x1, y0, y1] = [rect[0] * cA.w, rect[1] * cA.w, rect[2] * cA.h, rect[3] * cA.h];
    let inside = 0;
    let outside = 0;
    for (let y = 0; y < cA.h; y++)
      for (let x = 0; x < cA.w; x++) {
        const i = (y * cA.w + x) * 4;
        if (A[i] === B[i] && A[i + 1] === B[i + 1] && A[i + 2] === B[i + 2]) continue;
        if (x >= x0 - 12 && x <= x1 + 12 && y >= y0 - 12 && y <= y1 + 12) inside++;
        else outside++;
      }
    note('cushions-mock8.json', { inside, outside, rect });
    expect(inside, 'set A is another set').toBeGreaterThan(10_000);
    expect(outside, 'nothing outside the cushions changes').toBe(0);
    expect(await hashes(page)).toEqual(want);
  });

  test('the studio pictures in every wheel: the wheel shows them; D1 keeps a card where there is no still', async ({ page }) => {
    const seen: Record<string, (boolean | null)[]> = {};
    for (const id of ['living-room', 'master', 'bath', 'dining', 'boy', 'girl', 'work']) {
      const d = read<{ sample?: string; slots: { id: string; options: { studio?: { src: string; preview_only?: boolean } | null }[] }[] }>(
        join(SITE, '.generated', `tour.${id}.warm-modern.json`),
      );
      const s = d.slots.find((x) => x.id === d.sample)!;
      seen[id] = s.options.map((o) => (o.studio ? (o.studio.preview_only ?? false) : null));
    }
    note('studio-mock8.json', seen);
    // every option has its studio picture; the work room's prints are the preview's only (rights, PR1)
    for (const [id, v] of Object.entries(seen)) {
      expect(v.length, id).toBeGreaterThanOrEqual(2);
      expect(v.every((x) => x !== null), `${id}: every option has its studio picture`).toBe(true);
      expect(v.every((x) => x === (id === 'work')), `${id}: preview only where the rights are not confirmed`).toBe(true);
    }
    // and the wheel shows them (the bedroom's throw)
    await page.goto('/tour/?skip=1&room=master');
    await ready(page);
    await atRest(page);
    await page.locator('.tour-spot[data-slot="throw"]').click({ force: true });
    await expect(page.getByRole('dialog')).toBeVisible();
    const hrefs = await page.locator('.picker[data-ring] .arc.ring .arc-card image').evaluateAll((els) => els.map((e) => e.getAttribute('href')));
    for (const h of hrefs) expect(h).toMatch(/studio\.512\.webp$/);
    await page.keyboard.press('Escape');
  });

  test('the house light (FB16): each graded frame is its fb16 frame up to the finish’s grain, and far from the ungraded one', async ({ page }) => {
    const rooms: [string, string, string, string][] = [
      // [the tour's frame, its folder, its fb16 finish (the canvas), the frame before the grade (fb15's composite)]
      ['work', 'assets/renders/work/warm-modern/stage1-2026-11-20', 'w0-defaults-fb16-finish.png', 'w0-defaults-fb15.png'],
      ['master', 'assets/renders/master/warm-modern/stage1-2026-11-17', 'mb0-defaults-fb16-finish.png', 'mb0-defaults-fb15.png'],
      ['bath-b1', 'assets/renders/bath/warm-modern/b1-2026-11-19', 'b1-defaults-fb16-finish.png', 'b1-defaults-fb15.png'],
      ['dining', 'assets/renders/dining/warm-modern/stage1-2026-11-20', 'D1-defaults-fb16-finish.png', 'D1-defaults-fb15.png'],
    ];
    const out: Record<string, unknown> = {};
    for (const [id, dir, fb16, fb15] of rooms) {
      await page.goto(`/tour/?skip=1&room=${id}`);
      await ready(page);
      await atRest(page);
      const c = await composition(page);
      expect(c.w, 'a wide screen composes at the layers’ own width').toBe(2720);
      const got = Buffer.from(c.b64, 'base64');
      const stat = async (f: string) => {
        const t = await sharp(join(REPO, dir, f)).ensureAlpha().raw().toBuffer();
        const hist = new Array<number>(256).fill(0);
        let sum = 0;
        for (let i = 0; i < t.length; i += 4)
          for (let k = 0; k < 3; k++) {
            const d = Math.abs(t[i + k]! - got[i + k]!);
            hist[d]!++;
            sum += d;
          }
        const n = (t.length / 4) * 3;
        let acc = 0;
        let p99 = 0;
        for (let d = 0; d < 256; d++) if ((acc += hist[d]!) >= 0.99 * n) {
          p99 = d;
          break;
        }
        return { mean: +(sum / n).toFixed(3), p99 };
      };
      const g = await stat(fb16);
      const u = await stat(fb15);
      // D1's pendant glow is the default pendant's: another pendant takes it away
      let glow: unknown = null;
      if (id === 'dining') {
        glow = await page.evaluate(async () => {
          const e = window.__hdTour!;
          const lights = (e as unknown as { lights(): { pos?: number; post?: boolean }[] }).lights().filter((l) => l.pos);
          return lights.length;
        });
      }
      out[id] = { fb16: g, before_grade: u, glow };
      // the finish's grain and light wrap (the gate's mean about 1 at the frame), and the files' encoding at the canvas
      expect(g.mean, `${id}: the fb16 frame, up to the finish's grain and the encoding`).toBeLessThan(3);
      expect(g.p99, `${id}: the fb16 frame, up to the finish's grain and the encoding`).toBeLessThanOrEqual(12);
      expect(u.mean, `${id}: the grade is there (the frame before it is far)`).toBeGreaterThan(g.mean * 2);
      if (id === 'dining') expect(glow, 'D1: the default pendant’s glow goes with it').toBe(1);
    }
    note('fb16-mock8.json', out);
  });
});
