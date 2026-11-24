/**
 * MOCK5 (2026-11-24), every room the owner approved (briefs/site-mock5-house-rooms-2026-11-24.md), behind HD_PUBLIC=0:
 *
 *  1. the counting rule and the plan, read off the generated rooms: the owner's line counts a product once in its room
 *     (the living room 16, the bedroom 22, the bath 18, the kitchen 23, the work room 18), in the frame where it is
 *     biggest; the warm-modern cameras are the style shell's (D2 at −86, never the Nordic −91);
 *  2. each room from the panel lands on its rest frame (MB0, B2, D1, W0), at rest on the plain composition of its
 *     layers, a mark for every product the frame sells and none for the furniture that is not sold, the room's line;
 *  3. the frame control (MB0 / MB1, B2 / B1, D1 / D2): a dissolve that never moves the camera in (rule ו.6), landing on
 *     the other frame's plain composition; the room's line stays the room's;
 *  4. the wheels: the kitchen's pendant (V1, V3) in its close-up, the work room's art (08, 01, 02) and B1's mat;
 *  5. the rights rule: every print whose card's rights are not confirmed is ×1 only — no zoom in its frame, its own
 *     mark opens its card where it is, and no close-up of a neighbour shows it (the work room's art is the wheel's own
 *     slot: its wheel opens where it is);
 *  6. the encoding gate on the new frames (defaults and the wheels' variants against the folders' composites);
 *  7. a phone's first load of each new frame under 3 MB;
 *  8. axe on the new rooms at rest (a wide screen and a phone), the frame control, and the two new wheels.
 *
 * The numbers go to the evidence when HD_EVIDENCE_DIR is set.
 */
import { test, expect, devices, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import sharp from 'sharp';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { failures, measure, type Measure } from '../tools/lib/encoding';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const REPO = resolve(SITE, '..');
const read = <T>(f: string): T => JSON.parse(readFileSync(f, 'utf8')) as T;
const note = (name: string, data: unknown) => {
  const dir = process.env.HD_EVIDENCE_DIR;
  if (!dir) return;
  mkdirSync(join(dir, 'data'), { recursive: true });
  writeFileSync(join(dir, 'data', name), JSON.stringify(data, null, 1));
};
type Box = [number, number, number, number];
type Frame = {
  room: string;
  group: string;
  frame: string;
  frame_he: string | null;
  camera: { yaw_deg_left: number };
  camera_from: string;
  slots: { id: string; fixed?: boolean; closeup?: boolean; count_key?: string | null; area_px?: number; options: { position: number; box: Box }[] }[];
  avoid: Box[];
  x1: string[];
  rights: { slot: string; card: string | null; usage_rights: string }[];
  zoom: boolean;
  for_sale: number;
  sample?: string;
};
const frame = (id: string) => read<Frame>(resolve(SITE, `.generated/tour.${id}.warm-modern.json`));
const index = read<{ rooms: { id: string; frames: string[] }[] }>(resolve(SITE, 'tools/tour/frames.json'));
/** the brief's counts (MOCK5 ch. 8) */
const COUNT: Record<string, number> = { 'living-room': 16, master: 22, bath: 18, dining: 23, work: 18 };
const TITLE: Record<string, RegExp> = { master: /^חדר שינה/, bath: /^חדר רחצה/, dining: /^מטבח/, work: /^חדר עבודה/ };

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
/** the part of the frame the window shows, in canvas UV */
const view = (page: Page) =>
  page.evaluate(() => {
    const e = window.__hdTour!;
    const fw = Math.max(e.vp.w, e.vp.h * (16 / 9));
    const fh = fw / (16 / 9);
    const hu = e.vp.w / (2 * fw * e.cam.z);
    const hv = e.vp.h / (2 * fh * e.cam.z);
    return { z: e.cam.z, rest: e.rest.z, u: [e.cam.cu - hu, e.cam.cu + hu], v: [e.cam.cv - hv, e.cam.cv + hv] };
  });
const shows = (v: { u: number[]; v: number[] }, a: Box) => v.u[0]! < a[1] && v.u[1]! > a[0] && v.v[0]! < a[3] && v.v[1]! > a[2];
async function openSlot(page: Page, slot: string) {
  const tile = page.locator(`.tour-tile[data-slot="${slot}"]`);
  if (await tile.isVisible()) await tile.click();
  else await page.locator(`.tour-spot[data-slot="${slot}"]`).click({ force: true });
  await expect(page.getByRole('dialog')).toBeVisible();
  await atRest(page);
}
async function closeSlot(page: Page) {
  await page.getByRole('button', { name: 'סגירת התקריב' }).click();
  await expect(page.getByRole('dialog')).toBeHidden();
  await atRest(page);
}
async function audit(page: Page, label: string) {
  // a fresh load fades the band in (the door's 0.9 s): axe reads the page once every transition has ended
  await page.waitForFunction(() => document.getAnimations().every((a) => a.playState !== 'running'), undefined, { timeout: 10_000 });
  const r = await new AxeBuilder({ page } as unknown as ConstructorParameters<typeof AxeBuilder>[0])
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  const summary = r.violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.length} × ${v.nodes[0]?.target.join(' ')} — ${v.help}`);
  expect(summary, `${label}\n${summary.join('\n')}`).toEqual([]);
}

test.describe('MOCK5: every approved room', () => {
  test.describe.configure({ timeout: 400_000 });

  test('the counting rule and the plan: a product once a room, in its biggest frame; the warm-modern cameras', () => {
    const out: Record<string, { total: number; by: Record<string, number> }> = {};
    for (const r of index.rooms) {
      const best = new Map<string, { f: string; a: number }>();
      for (const f of r.frames)
        for (const s of frame(f).slots) {
          if (s.fixed) continue;
          expect(s.count_key, `${f} ${s.id} has a count key`).toBeTruthy();
          // the key is a hash: no supplier's address in the page
          expect(s.count_key).toMatch(/^[0-9a-f]{12}$/);
          const b = best.get(s.count_key!);
          if (!b || (s.area_px ?? 0) > b.a) best.set(s.count_key!, { f, a: s.area_px ?? 0 });
        }
      const by: Record<string, number> = {};
      for (const { f } of best.values()) by[f] = (by[f] ?? 0) + 1;
      out[r.id] = { total: best.size, by };
      expect(best.size, `${r.id}: the owner's count`).toBe(COUNT[r.id]);
    }
    note('room-counts.json', out);
    console.log(
      Object.entries(out)
        .map(
          ([k, v]) =>
            `${k} ${v.total} (${Object.entries(v.by)
              .map(([f, n]) => `${f} ${n}`)
              .join(' + ')})`,
        )
        .join(', '),
    );
    // registration 1.3.9 ch. 6.1: the warm-modern cameras are the style shell's
    for (const r of index.rooms) for (const f of r.frames) expect(frame(f).camera_from, f).toMatch(/^style_shells_1_3_1\.warm-modern\./);
    expect(frame('dining-d2').camera.yaw_deg_left).toBe(-86);
    expect(frame('dining').camera.yaw_deg_left).toBe(-56);
    expect(frame('master-mb1').camera.yaw_deg_left).toBe(33.7);
    // the rights rule: which prints it hit, by their cards
    const hit = index.rooms.flatMap((r) => r.frames.flatMap((f) => frame(f).rights.map((x) => ({ frame: f, ...x }))));
    note('rights.json', hit);
    for (const h of hit) expect(h.usage_rights === 'confirmed' || frame(h.frame).x1.includes(h.slot), `${h.frame} ${h.slot}`).toBe(true);
    expect(hit.map((h) => `${h.frame}/${h.slot}`).sort()).toEqual(
      [
        'dining-d2/framed-art',
        'dining/framed-art',
        'master-mb1/framed-art',
        'master-mb1/framed-art-2',
        'master/framed-art',
        'master/framed-art-2',
        'work/framed-art',
        'work/framed-art-2',
      ].sort(),
    );
  });

  for (const r of index.rooms) {
    test(`${r.id}: from the panel to its rest frame${r.frames.length > 1 ? ', and the frame control' : ''}; the plain composition; the marks; the owner's line`, async ({
      page,
    }) => {
      const want: Record<string, Awaited<ReturnType<typeof hashes>>> = {};
      for (const f of r.frames) want[f] = await plain(page, f);
      await page.goto('/tour/?skip=1');
      await ready(page);
      await atRest(page);
      await expect(page.locator('.tour-sale')).toHaveText(`${COUNT['living-room']} מוצרים למכירה בחדר`);
      await more(page);
      await page.locator(`#tour-${r.id}`).click();
      const first = r.frames[0]!;
      await page.waitForFunction((x) => window.__hdTourState?.room === x, first);
      await atRest(page);
      const check = async (f: string) => {
        const d = frame(f);
        expect(await hashes(page), `${f} rests on the plain composition of its layers`).toEqual(want[f]);
        await expect(page.locator('.tour-spot')).toHaveCount(d.for_sale);
        for (const s of d.slots.filter((x) => x.fixed)) await expect(page.locator(`.tour-spot[data-slot="${s.id}"]`)).toHaveCount(0);
        await expect(page.locator('.tour-sale')).toHaveText(`${COUNT[r.id]} מוצרים למכירה בחדר`);
        await expect(page.locator('#tour-title')).toHaveText(TITLE[r.id]!);
        // a frame with a ×1-only print has no zoom (the rights rule)
        if (!d.zoom) await expect(page.locator('#tour-zoom')).toBeHidden();
      };
      await check(first);
      if (r.frames.length === 1) {
        await expect(page.locator('.tour-frames')).toHaveCount(0);
        return;
      }
      // the frame control: one button a frame, the frame shown pressed
      await expect(page.locator('.tour-frames button')).toHaveText(r.frames.map((f) => frame(f).frame_he!));
      await expect(page.locator(`.tour-frames button[data-frame="${first}"]`)).toHaveAttribute('aria-pressed', 'true');
      for (const to of [r.frames[1]!, first]) {
        // the camera is sampled on every frame of the dissolve: it never moves in (rule ו.6)
        await page.evaluate(() => {
          const w = window as unknown as { __zs: number[]; __zrun: boolean };
          w.__zs = [];
          w.__zrun = true;
          const tick = () => {
            const e = window.__hdTour!;
            w.__zs.push(e.cam.z / e.rest.z);
            if (w.__zrun) requestAnimationFrame(tick);
          };
          requestAnimationFrame(tick);
        });
        await page.locator(`.tour-frames button[data-frame="${to}"]`).click();
        await page.waitForFunction((x) => window.__hdTourState?.room === x, to);
        await atRest(page);
        const zs = await page.evaluate(() => {
          const w = window as unknown as { __zs: number[]; __zrun: boolean };
          w.__zrun = false;
          return w.__zs;
        });
        expect(Math.max(...zs), `${first} → ${to}: never a zoom-in`).toBeLessThanOrEqual(1.001);
        await check(to);
        await expect(page.locator(`.tour-frames button[data-frame="${to}"]`)).toHaveAttribute('aria-pressed', 'true');
      }
    });
  }

  test('the wheels: the kitchen’s pendant (V1, V3) in its close-up, the work room’s art (×1: where it is), B1’s mat', async ({ page }) => {
    const cases = [
      { room: 'dining', slot: 'dining-pendant', n: 2, closeup: true },
      { room: 'work', slot: 'framed-art', n: 3, closeup: false },
      { room: 'bath-b1', slot: 'bath-mat', n: 2, closeup: true },
    ];
    const seen: Record<string, unknown> = {};
    for (const c of cases) {
      const d = frame(c.room);
      expect(d.sample).toBe(c.slot);
      await page.goto(`/tour/?skip=1&room=${c.room}`);
      await ready(page);
      await atRest(page);
      await page.locator(`.tour-spot[data-slot="${c.slot}"]`).click({ force: true });
      await expect(page.getByRole('dialog')).toBeVisible();
      await atRest(page);
      await expect(page.locator('.arc-card')).toHaveCount(c.n);
      const v = await view(page);
      seen[c.room] = v;
      if (c.closeup) expect(v.z, `${c.room}: the close-up comes closer`).toBeGreaterThan(v.rest * 1.2);
      else expect(v.z, `${c.room}: ×1 only, the wheel opens where it is`).toBeLessThanOrEqual(v.rest * 1.001);
      for (const a of d.avoid) expect(v.z > v.rest * 1.001 && shows(v, a), `${c.room}: a zoomed view never shows a ×1-only print`).toBe(false);
      for (let pos = 2; pos <= c.n; pos++) {
        await page.keyboard.press('ArrowLeft');
        await expect.poll(() => page.evaluate((s) => window.__hdTour!.selection[s], c.slot)).toBe(pos);
      }
      await page.keyboard.press('Escape');
      await expect(page.getByRole('dialog')).toBeHidden();
      await atRest(page);
    }
    note('wheels.json', seen);
  });

  test('the rights rule: every ×1-only print — no zoom, its mark opens where it is, no neighbour’s close-up shows it (a phone)', async ({ browser }) => {
    const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, hasTouch: true, isMobile: true });
    const page = await ctx.newPage();
    const seen: Record<string, unknown> = {};
    for (const f of ['master-mb1', 'dining', 'dining-d2', 'work']) {
      const d = frame(f);
      expect(d.avoid.length, `${f} has ×1-only prints`).toBeGreaterThan(0);
      expect(d.zoom).toBe(false);
      await page.goto(`/tour/?skip=1&room=${f}`);
      await ready(page);
      await atRest(page);
      await expect(page.locator('#tour-zoom')).toBeHidden();
      // the prints themselves, and every product near one (within a quarter of the frame)
      const near = d.slots.filter(
        (s) =>
          !s.fixed &&
          (d.x1.includes(s.id) ||
            d.avoid.some((a) => {
              const b = s.options[0]!.box;
              return Math.max(0, a[0] - b[1], b[0] - a[1]) < 0.25 && Math.max(0, a[2] - b[3], b[2] - a[3]) < 0.25;
            })),
      );
      for (const s of near) {
        await openSlot(page, s.id);
        const v = await view(page);
        seen[`${f} ${s.id}`] = v;
        const zoomed = v.z > v.rest * 1.001;
        if (d.x1.includes(s.id)) expect(zoomed, `${f} ${s.id}: a ×1-only print opens where it is`).toBe(false);
        for (const a of d.avoid) expect(zoomed && shows(v, a), `${f} ${s.id}: a zoomed view never shows a ×1-only print`).toBe(false);
        await closeSlot(page);
      }
    }
    note('rights-x1.json', seen);
    await ctx.close();
  });

  test('the encoding gate on the new frames: the defaults and the wheels’ variants against the folders’ composites', async ({ page }) => {
    const out: Record<string, Measure & { pass: boolean; identical: number }> = {};
    const bad: string[] = [];
    const variants: Record<string, string[]> = {
      dining: ['D1-V3.png'],
      work: ['w0-variant-art-01.png', 'w0-variant-art-02.png'],
      'bath-b1': ['b1-variant-mat-beige.png'],
    };
    for (const id of ['master-mb1', 'bath-b1', 'dining', 'dining-d2', 'work']) {
      type Cfg = { layers: string; manifest: string; truth: string; sample: string | null; frame_id?: string };
      const cfg = read<Cfg>(resolve(SITE, `tools/tour/${id}.warm-modern.json`));
      const dir = resolve(REPO, cfg.layers);
      type L = { slot: string; layer: string; default?: boolean; frame?: string; retired?: unknown };
      const lm = read<{ layers: L[]; variants?: (L & { composite?: string })[] }>(join(dir, cfg.manifest));
      const mine = (l: L) => (!cfg.frame_id || l.frame === cfg.frame_id) && !l.retired;
      const defaults = lm.layers.filter((l) => mine(l) && l.default !== false);
      const alt = [...lm.layers.filter((l) => mine(l) && l.default === false), ...(lm.variants ?? []).filter((l) => mine(l) && l.default === false)];
      const cases = [
        { pos: 1, truth: cfg.truth, alpha: defaults.map((l) => l.layer) },
        ...(variants[id] ?? []).map((t, i) => ({
          pos: i + 2,
          truth: t,
          alpha: defaults
            .filter((l) => l.slot !== cfg.sample)
            .map((l) => l.layer)
            .concat(alt[i]!.layer),
        })),
      ];
      await page.goto(`/tour/?skip=1&room=${id}`);
      await ready(page);
      await atRest(page);
      expect(await page.evaluate(() => window.__hdTour!.gl.width), 'a wide screen composes at the layers’ own width').toBe(2720);
      for (const c of cases) {
        const b64 = await page.evaluate(
          async ([slot, pos]) => {
            const e = window.__hdTour!;
            const m = window.__hdTourFx!;
            e.sync = true;
            if (slot && pos > 1) {
              const ui = { ring() {}, label() {}, spots() {}, count() {}, dims() {} };
              await e.option(slot, pos);
              if (e.selection[slot] !== pos) await m.swap(e, ui, e.slot(slot), pos, pos > e.selection[slot]! ? 1 : -1, 's1');
            }
            const a = e.read([0, 0, e.gl.width, e.gl.height]);
            let s = '';
            for (let i = 0; i < a.length; i += 0x8000) s += String.fromCharCode(...a.subarray(i, i + 0x8000));
            return btoa(s);
          },
          [cfg.sample, c.pos] as const,
        );
        const enc = Buffer.from(b64, 'base64');
        const truth = await sharp(join(dir, c.truth)).ensureAlpha().raw().toBuffer();
        const keep = new Uint8Array(2720 * 1530);
        for (const f of c.alpha) {
          const al = await sharp(join(dir, f)).ensureAlpha().extractChannel(3).raw().toBuffer();
          for (let i = 0; i < al.length; i++) if (al[i] === 255) keep[i] = 1;
        }
        const idx: number[] = [];
        for (let i = 0; i < keep.length; i++) if (keep[i]) idx.push(i);
        const A = new Uint8Array(idx.length * 4);
        const B = new Uint8Array(idx.length * 4);
        idx.forEach((k, j) => {
          A.set(truth.subarray(k * 4, k * 4 + 4), j * 4);
          B.set(enc.subarray(k * 4, k * 4 + 4), j * 4);
        });
        let same = 0;
        for (let i = 0; i < truth.length; i += 4) if (truth[i] === enc[i] && truth[i + 1] === enc[i + 1] && truth[i + 2] === enc[i + 2]) same++;
        const mm = measure(A, B, false);
        const f = failures(mm);
        out[`${id} ${c.pos} (${c.truth})`] = { ...mm, pass: f.length === 0, identical: +(same / (truth.length / 4)).toFixed(4) };
        for (const x of f) bad.push(`${id} ${c.pos}: ${x}`);
      }
    }
    note('encoding-mock5.json', out);
    console.log(
      Object.entries(out)
        .map(([k, m]) => `${k}: ΔE00 p99 ${m.de00_p99}, p99 ${m.p99}, identical ${(m.identical * 100).toFixed(1)}%`)
        .join('\n'),
    );
    expect(bad, bad.join('\n')).toEqual([]);
  });

  test('a phone’s first load of each new frame stays under 3 MB', async ({ browser }) => {
    const { defaultBrowserType: _b, ...pixel } = devices['Pixel 7'];
    const sizes: Record<string, number> = {};
    for (const id of ['master-mb1', 'bath-b1', 'dining', 'dining-d2', 'work']) {
      const ctx = await browser.newContext({ ...pixel, locale: 'he-IL' });
      const page = await ctx.newPage();
      let bytes = 0;
      const client = await ctx.newCDPSession(page);
      await client.send('Network.enable');
      const urls = new Map<string, string>();
      client.on('Network.requestWillBeSent', (e) => void urls.set(e.requestId, e.request.url));
      // the walk (it is not this room's) and what loads behind the room once it rests are not its first load
      const behind = (u: string) => /\/media\/tour\/arrival\//.test(u) || /\/slots\/[a-z-]+\/[23]\./.test(u) || /\/media\/rooms\//.test(u);
      client.on('Network.loadingFinished', (e) => void (!behind(urls.get(e.requestId) ?? '') && (bytes += e.encodedDataLength)));
      await page.goto(`/tour/?skip=1&room=${id}`);
      await ready(page);
      await atRest(page);
      sizes[id] = bytes;
      await ctx.close();
    }
    note('first-load-mock5.json', sizes);
    console.log(
      Object.entries(sizes)
        .map(([k, b]) => `${k}: ${(b / 1048576).toFixed(2)} MB`)
        .join(', '),
    );
    for (const b of Object.values(sizes)) expect(b).toBeLessThanOrEqual(3 * 1024 * 1024);
  });

  test('axe finds nothing: the new rooms at rest, the frame control, the two new wheels (a wide screen and a phone)', async ({ browser }) => {
    for (const vp of [
      { width: 1280, height: 800, touch: false },
      { width: 390, height: 844, touch: true },
    ]) {
      const ctx = await browser.newContext({
        locale: 'he-IL',
        viewport: { width: vp.width, height: vp.height },
        ...(vp.touch ? { deviceScaleFactor: 3, hasTouch: true, isMobile: true } : {}),
      });
      const page = await ctx.newPage();
      for (const id of ['master-mb1', 'bath-b1', 'dining', 'dining-d2', 'work']) {
        await page.goto(`/tour/?skip=1&room=${id}`);
        await ready(page);
        await atRest(page);
        await audit(page, `${vp.width}: ${id} at rest`);
        if (id === 'dining' || id === 'work') {
          await openSlot(page, frame(id).sample!);
          await audit(page, `${vp.width}: ${id}'s wheel`);
          await closeSlot(page);
        }
      }
      // the frame control, after a switch (focus stays on it)
      await page.goto('/tour/?skip=1&room=dining-d2');
      await ready(page);
      await atRest(page);
      await page.locator('.tour-frames button[data-frame="dining"]').click();
      await page.waitForFunction(() => window.__hdTourState?.room === 'dining');
      await atRest(page);
      await audit(page, `${vp.width}: the frame control after a switch`);
      await ctx.close();
    }
  });
});
