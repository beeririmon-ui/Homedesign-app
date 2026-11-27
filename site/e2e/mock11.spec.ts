/**
 * MOCK11 (2026-11-27, briefs/site-mock11-route-legs-2026-11-27.md), behind HD_PUBLIC=0, design C: the real route legs.
 *
 *  1. the real legs play: "הלאה" at each station from the kitchen plays that leg's clip at its own pace, and it lands on
 *     the next room's own composition (a leg without a clip fades, see 2);
 *  2. a leg without its clip (leg 6, girl → work) fades through the warm light, about 450 ms, as the way back does:
 *     no push, no video;
 *  3. a chained jump of three stations: the legs back to back at ×2.5, the ease frames between them skipped (the
 *     manifests' `fast_forward`), no flash of the room and no pause at the joins;
 *  4. the seams: each real leg's first frame against the room it leaves, its last against the room it reaches, both
 *     as the visitor sees them (the window, the video over the live canvas with its FB16 grade), mean, p99 and shift;
 *  5. the preload: at rest, only the leg reachable from the room is fetched; a phone fetches the 1080 file.
 *
 * Which legs are real is tools/tour/route.json's (as .generated/route.json carries it): a leg that gets its clip
 * changes what these tests expect of it, not the tests. The numbers go to the evidence when HD_EVIDENCE_DIR is set.
 */
import { test, expect, type Page } from '@playwright/test';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import sharp from 'sharp';

type LegVideo = { src: string; poster: string; w: number; h: number; fps: number; frames: number; ease_in: [number, number]; ease_out: [number, number] };
type Leg = { id: string; from: string; to: string; real: Record<'desktop' | 'phone', LegVideo> | null };
const ROUTE = JSON.parse(readFileSync(new URL('../.generated/route.json', import.meta.url), 'utf8')) as { order: string[]; legs: Leg[] };
/** a station's room: its first frame (tools/tour/frames.json) */
const ROOM: Record<string, string> = {
  'living-room': 'living-room',
  dining: 'dining',
  bath: 'bath-b1',
  master: 'master',
  boy: 'boy',
  girl: 'girl',
  work: 'work',
};
const own = (v: LegVideo) => ((v.frames - 1) / v.fps) * 1000;

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
const noIntro = (page: Page) => page.addInitScript(() => sessionStorage.setItem('hd-intro', '1'));
async function at(page: Page, room: string) {
  await page.goto(`/tour/?skip=1&room=${room}`);
  await ready(page);
  await atRest(page);
}
/** the plain composition of each room (its default products), as a hash */
async function plain(page: Page, rooms: string[]) {
  const out: Record<string, number> = {};
  for (const r of rooms) {
    await at(page, r);
    out[r] = await hashes(page);
  }
  return out;
}
/** watches the light over the window and the legs on screen, once per frame */
const watch = (page: Page) =>
  page.evaluate(() => {
    const w = window as unknown as { __seen: [number, number, number, string, number][]; __watch: boolean };
    w.__seen = [];
    w.__watch = true;
    const vids = Array.from(document.querySelectorAll<HTMLVideoElement>('video.tour-leg'));
    const tick = () => {
      const on = vids.findIndex((v) => v.hasAttribute('data-on'));
      const v = vids[on];
      const lit = +getComputedStyle(document.querySelector('.tour-light')!).opacity;
      w.__seen.push([performance.now(), on, v ? v.currentTime : -1, v?.getAttribute('src') ?? '', lit]);
      if (w.__watch) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
const seen = (page: Page) =>
  page.evaluate(() => {
    const w = window as unknown as { __seen: [number, number, number, string, number][]; __watch: boolean };
    w.__watch = false;
    return w.__seen;
  });

/** two screenshots of the window, as raw RGB: mean and p99 of the largest channel difference, and the best shift */
async function compare(a: Buffer, b: Buffer, scale: number) {
  const ra = await sharp(a).removeAlpha().raw().toBuffer({ resolveWithObject: true });
  const rb = await sharp(b).removeAlpha().raw().toBuffer();
  const { width: w, height: h } = ra.info;
  const hist = new Array<number>(256).fill(0);
  let sum = 0;
  for (let i = 0; i < w * h; i++) {
    const j = i * 3;
    const d = Math.max(Math.abs(ra.data[j]! - rb[j]!), Math.abs(ra.data[j + 1]! - rb[j + 1]!), Math.abs(ra.data[j + 2]! - rb[j + 2]!));
    hist[d]!++;
    sum += d;
  }
  let acc = 0;
  let p99 = 0;
  for (let d = 0; d < 256; d++)
    if ((acc += hist[d]!) >= 0.99 * w * h) {
      p99 = d;
      break;
    }
  // the shift: greys at half size, a search of ±6 px over the middle (the edges move out of the frame)
  const gw = Math.round(w / 2);
  const gh = Math.round(h / 2);
  const ga = await sharp(a).resize(gw, gh).greyscale().raw().toBuffer();
  const gb = await sharp(b).resize(gw, gh).greyscale().raw().toBuffer();
  let best = { dx: 0, dy: 0, e: Infinity };
  const R = 6;
  for (let dy = -R; dy <= R; dy++)
    for (let dx = -R; dx <= R; dx++) {
      let e = 0;
      let n = 0;
      for (let y = R + 8; y < gh - R - 8; y += 2)
        for (let x = R + 8; x < gw - R - 8; x += 2) {
          e += Math.abs(ga[y * gw + x]! - gb[(y + dy) * gw + x + dx]!);
          n++;
        }
      if (e / n < best.e) best = { dx, dy, e: e / n };
    }
  // in the 1920 frame's pixels
  return { mean: +(sum / (w * h)).toFixed(2), p99, shift_px: +(Math.hypot(best.dx, best.dy) * 2 * scale).toFixed(1) };
}

/**
 * a leg's frame against the room at rest, both as the window shows them (the page around the picture set aside): the
 * leg's file on the page's own video over the canvas, its first frame where it starts, its last where it ends
 */
async function seam(page: Page, v: LegVideo, which: 'first' | 'last') {
  const win = page.locator('.tour-win');
  const box = (await win.boundingBox())!;
  const room = await page.screenshot({ clip: box });
  await page.evaluate(
    async ({ src, last }) => {
      const el = document.querySelectorAll<HTMLVideoElement>('video.tour-leg')[1]!;
      el.style.setProperty('--leg-ms', '0ms');
      el.style.setProperty('visibility', 'visible', 'important');
      el.preload = 'auto';
      el.src = src;
      if (el.readyState < 2) await new Promise((r) => el.addEventListener('loadeddata', r, { once: true }));
      el.toggleAttribute('data-on', true);
      // the last frame: the file played through to its end, as the tour plays a leg (the test server, like the
      // Artifact's, sends no byte ranges: a seek past what has arrived falls back to the start); its last 0.6 s slowly,
      // so this GPU-less machine presents every frame of it and the one on screen at the end is the file's last
      if (last) {
        el.playbackRate = 16;
        const ended = new Promise((r) => el.addEventListener('ended', r, { once: true }));
        await el.play();
        while (el.currentTime < el.duration - 0.6) await new Promise((r) => requestAnimationFrame(r));
        el.playbackRate = 0.25;
        await ended;
      }
      await new Promise((r) => setTimeout(r, 600));
    },
    { src: `/media/${v.src}`, last: which === 'last' },
  );
  const leg = await page.screenshot({ clip: box });
  await page.evaluate(() => {
    const el = document.querySelectorAll<HTMLVideoElement>('video.tour-leg')[1]!;
    el.removeAttribute('data-on');
    el.style.setProperty('visibility', 'hidden', 'important');
    el.removeAttribute('src');
    el.load();
  });
  const dir = process.env.HD_EVIDENCE_DIR;
  if (dir) {
    // the two pictures of each seam, for the evidence
    mkdirSync(join(dir, 'seams'), { recursive: true });
    const name = `${v.src.replace(/^.*\//, '').replace(/\.mp4$/, '')}.${which}`;
    writeFileSync(join(dir, 'seams', `${name}.room.png`), room);
    writeFileSync(join(dir, 'seams', `${name}.leg.png`), leg);
  }
  return compare(room, leg, 1920 / box.width);
}

test.describe('MOCK11: the real route legs', () => {
  test.describe.configure({ timeout: 400_000 });

  test('the real legs play: "הלאה" at each station, the clip at its own pace, landing on the room’s own composition', async ({ page }) => {
    await noIntro(page);
    const hops = ROUTE.legs.filter((l) => ROUTE.order.indexOf(l.from) >= ROUTE.order.indexOf('dining') && l.to !== 'work');
    const want = await plain(
      page,
      hops.map((l) => ROOM[l.to]!),
    );
    await at(page, 'dining');
    const got: unknown[] = [];
    for (const l of hops) {
      await page.locator('#route-next').click();
      if (l.real) {
        await page.waitForFunction((id) => window.__hdTourState?.leg?.id === id, l.id, { timeout: 60_000 });
        expect(await page.locator('video.tour-leg[data-on]').getAttribute('src')).toMatch(new RegExp(`tour/route/${l.id}\\.1920\\.60\\.mp4$`));
      }
      await page.waitForFunction((r) => window.__hdTourState?.room === r, ROOM[l.to]!, { timeout: 120_000 });
      await atRest(page);
      const s = await state(page);
      got.push(s.trip);
      expect(s.trip).toMatchObject({ to: ROOM[l.to], kind: 'ahead', rate: 1 });
      if (l.real) {
        const v = l.real.desktop;
        expect(s.trip!.hops).toEqual([{ leg: l.id, real: true, start: 0, end: +((v.frames - 1) / v.fps).toFixed(4) }]);
        // the leg's own time, and its blends: a walk, not a jump
        expect(s.trip!.ms, `${l.id}: its own pace`).toBeGreaterThan(own(v) * 0.95);
      } else expect(s.trip!.hops).toMatchObject([{ leg: l.id, real: false }]);
      await expect(page.locator('video.tour-leg[data-on]')).toHaveCount(0);
      expect(await hashes(page), `${l.to}: the room at rest is its own composition`).toBe(want[ROOM[l.to]!]);
    }
    note('next.json', got);
  });

  test('a leg without its clip (girl → work) fades through the warm light, about 450 ms: no push, no video', async ({ page }) => {
    const l = ROUTE.legs.find((x) => !x.real)!;
    expect(l, 'a leg still waits for its clip').toBeTruthy();
    await noIntro(page);
    const want = await plain(page, [ROOM[l.to]!]);
    await at(page, ROOM[l.from]!);
    await watch(page);
    await page.locator('#route-next').click();
    await page.waitForFunction((r) => window.__hdTourState?.room === r, ROOM[l.to]!, { timeout: 60_000 });
    await atRest(page);
    const s = await state(page);
    const frames = await seen(page);
    const pushed = await page.evaluate(() => Object.keys(window.__hdTour!.frames).filter((k) => /^(room|route)-/.test(k)));
    note('null-leg.json', { trip: s.trip, peak: Math.max(...frames.map((f) => f[4])), pushed });
    expect(s.trip).toMatchObject({ to: ROOM[l.to], kind: 'ahead', rate: 1, hops: [{ leg: l.id, real: false }] });
    const fade = s.trip!.hops[0]!.fade!;
    // the fade itself, up into the light and down onto the room (the room's change inside the full light is apart)
    expect(fade).toBeGreaterThan(400);
    // (the GPU-less test machine draws a frame in 50–100 ms: the slack of the other walks' checks, MOCK7)
    expect(fade).toBeLessThan(450 + 250);
    expect(Math.max(...frames.map((f) => f[4])), 'the window went up into the light').toBeGreaterThan(0.85);
    expect(
      frames.filter((f) => f[1] >= 0),
      'no video',
    ).toHaveLength(0);
    expect(pushed, 'no push in code (the MOCK7 zoom, FB26)').toEqual([]);
    expect(await hashes(page)).toBe(want[ROOM[l.to]!]);
  });

  test('a chained jump of three stations: the legs back to back at ×2.5, the ease frames skipped, no flash and no pause at the joins', async ({ page }) => {
    await noIntro(page);
    const from = 'dining';
    const to = ROUTE.order[ROUTE.order.indexOf(from) + 3]!;
    const legs = ROUTE.legs.slice(ROUTE.order.indexOf(from), ROUTE.order.indexOf(to));
    const want = await plain(page, [ROOM[to]!]);
    await at(page, ROOM[from]!);
    await watch(page);
    await page.locator(`.route-rail button[data-g="${to}"]`).click();
    await page.waitForFunction((r) => window.__hdTourState?.room === r, ROOM[to]!, { timeout: 120_000 });
    await atRest(page);
    const s = await state(page);
    const f = await seen(page);
    expect(s.trip).toMatchObject({ to: ROOM[to], kind: 'ahead', rate: 2.5 });
    // the stretches: the ease-in of every leg but the first, the ease-out of every leg but the last (`fast_forward`)
    expect(s.trip!.hops.map((h) => [h.leg, h.real])).toEqual(legs.map((l) => [l.id, !!l.real]));
    legs.forEach((l, i) => {
      if (!l.real) return;
      const v = l.real.desktop;
      const first = i > 0 ? v.ease_in[1] + 1 : 1;
      const last = i < legs.length - 1 ? v.ease_out[0] - 1 : v.frames;
      expect(s.trip!.hops[i]).toMatchObject({ start: +((first - 1) / v.fps).toFixed(4), end: +((last - 1) / v.fps).toFixed(4) });
    });
    // the whole jump: well under the legs' own time
    const ownAll = legs.reduce((a, l) => a + (l.real ? own(l.real.desktop) : 450), 0);
    expect(s.trip!.ms).toBeLessThan(ownAll / 2);
    // the frames between the first leg on screen and the last: the room never shows through (a flash), unless the
    // light covers it (a leg without its clip)
    const a = f.findIndex((x) => x[1] >= 0);
    let b = f.length - 1;
    while (b > 0 && f[b]![1] < 0) b--;
    const flash = f.slice(a, b + 1).filter((x) => x[1] < 0 && x[4] < 0.5).length;
    // the joins between two clips: from the last frame the leg before moved to the first the next one moves on
    const dts = f
      .slice(a, b)
      .map((x, j) => f[a + j + 1]![0] - x[0])
      .sort((x, y) => x - y);
    const frameMs = Math.round(dts[dts.length >> 1]!);
    const joins: { from: string; to: string; stall_ms: number; frame_ms: number }[] = [];
    for (let i = a + 1; i <= b; i++) {
      const p = f[i - 1]!;
      const q = f[i]!;
      // (a change of clip inside the full light is the fade of a leg without its clip, not a join)
      if (p[1] < 0 || q[1] < 0 || p[3] === q[3] || p[4] > 0.05 || q[4] > 0.05) continue;
      // the frame on which the leg before last moved (its time reached its last value there)
      let k = i - 1;
      while (k > a && f[k - 1]![3] === p[3] && f[k - 1]![2] === f[k]![2]) k--;
      // the first frame on which the next leg has moved on from where it was cued
      let m = i;
      while (m < b && f[m + 1]![3] === q[3] && f[m + 1]![2] === f[m]![2]) m++;
      m = Math.min(m + 1, b);
      joins.push({ from: p[3].replace(/^.*\//, ''), to: q[3].replace(/^.*\//, ''), stall_ms: Math.round(f[m]![0] - f[k]![0]), frame_ms: frameMs });
    }
    note('chain.json', { trip: s.trip, flash, joins });
    expect(flash, 'no flash of the room between the legs').toBe(0);
    const pairs = legs.slice(1).filter((l, i) => l.real && legs[i]!.real).length;
    expect(joins).toHaveLength(pairs);
    // a cut between two decoded frames: the next leg moves on within a few frames of the machine's own pace
    for (const j of joins) expect(j.stall_ms, `${j.from} → ${j.to}`).toBeLessThan(Math.max(250, j.frame_ms * 4));
    await expect(page.locator('video.tour-leg[data-on]')).toHaveCount(0);
    expect(await hashes(page)).toBe(want[ROOM[to]!]);
  });

  test('the seams: each real leg’s first frame is the room it leaves, its last the room it reaches, as the window shows them', async ({ page }) => {
    await noIntro(page);
    const out: Record<string, unknown> = {};
    const real = ROUTE.legs.filter((l) => l.real);
    for (const room of [...new Set(real.flatMap((l) => [l.from, l.to]))]) {
      await at(page, ROOM[room]!);
      // ?skip=1 still fades the door away over the room at rest: the room is measured once it is gone
      await page.waitForFunction(() => {
        const d = document.querySelector('.tour-door-img');
        return !d || +getComputedStyle(d).opacity === 0 || getComputedStyle(d).visibility === 'hidden';
      });
      await page.waitForTimeout(300);
      // the picture alone: everything of the page over it is set aside (the page's CSP refuses a style tag)
      await page.evaluate(() => {
        document.querySelectorAll<HTMLElement>('body *').forEach((el) => el.style.setProperty('visibility', 'hidden', 'important'));
        document.querySelector<HTMLElement>('.room-canvas')!.style.setProperty('visibility', 'visible', 'important');
      });
      for (const l of real) {
        for (const k of ['desktop', 'phone'] as const) {
          if (l.from === room) out[`${l.id}.${k}.first`] = await seam(page, l.real![k], 'first');
          if (l.to === room) out[`${l.id}.${k}.last`] = await seam(page, l.real![k], 'last');
        }
      }
    }
    note('seams.json', out);
    console.log(`MOCK11 seams: ${JSON.stringify(out)}`);
    for (const [k, v] of Object.entries(out) as [string, { mean: number; p99: number; shift_px: number }][]) {
      // the encoding, the FB16 grade against the leg's graded still, and the frame's lock (the manifests: ≤ ~5 levels).
      // The phone's file is 1080 px wide, softer than the canvas at this 1280 window; and the end of a 30 fps file can be
      // presented a frame late on this GPU-less machine (its frames end on the wide screen's to the pixel, checked on
      // the files themselves), so it is held to a looser bound
      const phone = k.includes('.phone.');
      expect(v.mean, `${k}: mean`).toBeLessThan(phone ? 10 : 6);
      expect(v.shift_px, `${k}: no visible jump`).toBeLessThanOrEqual(phone ? 8 : 3);
    }
  });

  test('the preload: at rest only the reachable leg is fetched; a phone fetches its 1080 file', async ({ page, browser }) => {
    // the visitor's way: the living room, "הלאה" to the kitchen (leg 1), and at rest there the next leg is fetched
    const l = ROUTE.legs[1]!;
    expect(l.real, 'leg 2 is a clip').toBeTruthy();
    const asked: string[] = [];
    const to = async (p: Page) => {
      await noIntro(p);
      await p.goto('/tour/?skip=1');
      await ready(p);
      await atRest(p);
      await p.locator('#route-next').click();
      await p.waitForFunction((r) => window.__hdTourState?.room === r, ROOM[l.from]!, { timeout: 60_000 });
      await atRest(p);
      asked.length = 0;
      await p.waitForFunction((id) => document.querySelector('video.tour-leg')?.getAttribute('src')?.includes(`/${id}.`), l.id, { timeout: 15_000 });
      await p.waitForTimeout(1500);
    };
    page.on('request', (r) => {
      if (/\/tour\/route\//.test(r.url())) asked.push(r.url().replace(/^.*\/tour\/route\//, ''));
    });
    await to(page);
    expect([...new Set(asked.map((u) => u.split('.')[0]))]).toEqual([l.id]);
    expect(asked.filter((u) => u.includes('.mp4'))).not.toHaveLength(0);
    expect(asked.filter((u) => u.includes('.mp4')).every((u) => u.startsWith(`${l.id}.1920.60.mp4`))).toBe(true);
    // a phone: the 30 fps file
    const ctx = await browser.newContext({ viewport: { width: 400, height: 860 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, locale: 'he-IL' });
    const p2 = await ctx.newPage();
    await to(p2);
    expect(await p2.locator('video.tour-leg').first().getAttribute('src')).toMatch(new RegExp(`${l.id}\\.1080\\.30\\.mp4$`));
    await ctx.close();
  });
});
