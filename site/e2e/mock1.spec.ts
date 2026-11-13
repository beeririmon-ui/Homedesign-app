/**
 * MOCK1 (2026-11-12), the wow-tour mock-up (briefs/site-mock1-wow-tour-2026-11-12.md), behind HD_PUBLIC=0:
 *
 *  1. the door is the first screen, and the whole tour works from the keyboard (the door's button, the rooms' buttons,
 *     the wheel, the temporary switches); zero axe violations at the door, in the room and with the wheel open;
 *  2. after each reveal (A, B, C) settles, the frame is the plain composition of the layers, pixel for pixel;
 *  3. no jump at any seam: every effect at its first frame is the frame before it, and at its last frame the frame after
 *     it (the engine runs each effect at its two ends and reads the canvas back: web/src/tour/engine.ts `ends`);
 *  4. the phase 2 layers load and swap: a variant changes its own rectangle and nothing outside it, and the default
 *     comes back exactly;
 *  5. the encoding gate on the phase 2 layers (QA R8 F7): the composition of every option against the render's approved
 *     composite, on the product's own opaque pixels, at 1:1 (tools/lib/encoding.ts: the tool-layer threshold);
 *  6. reduced motion: every effect is a short dissolve, nothing moves, and the room still ends on the plain composition;
 *  7. the first load on a phone stays under 3 MB until the room is composed with its default products.
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
type Slot = { id: string; rect: [number, number, number, number]; options: { position: number; product_id: string | null }[] };
const tour = read<{ native: number; slots: Slot[] }>(resolve(SITE, '.generated/tour.living-room.warm-modern.json'));
const W = tour.native;
const H = Math.round((W * 9) / 16);
const note = (name: string, data: unknown) => {
  const dir = process.env.HD_EVIDENCE_DIR;
  if (!dir) return;
  mkdirSync(join(dir, 'data'), { recursive: true });
  writeFileSync(join(dir, 'data', name), JSON.stringify(data, null, 1));
};

const ready = (page: Page) => page.waitForFunction(() => window.__hdTour?.ready === true, undefined, { timeout: 30_000 });
const atRest = (page: Page, phase: 'door' | 'room' = 'room') =>
  page.waitForFunction((p) => window.__hdTourState?.phase === p && window.__hdTourState.busy === false, phase, { timeout: 60_000 });
/** MOCK3: the rooms, the style and the temporary switches are inside the folded control, "המשך הסיור" */
async function more(page: Page) {
  if ((await page.locator('#tour-fold').getAttribute('aria-expanded')) !== 'true') await page.locator('#tour-fold').click();
  await page.waitForFunction(() => window.__hdTourState?.more === true && window.__hdTour?.busy === false);
}
/** the plain composition, no effect ever run: its own pixels and the canvas, as two hashes */
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
async function plain(page: Page) {
  await page.goto('/tour/?skip=1');
  await ready(page);
  await atRest(page);
  return hashes(page);
}
async function audit(page: Page, label: string) {
  const r = await new AxeBuilder({ page } as unknown as ConstructorParameters<typeof AxeBuilder>[0])
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  const summary = r.violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.length} × ${v.nodes[0]?.target.join(' ')} — ${v.help}`);
  expect(summary, `${label}\n${summary.join('\n')}`).toEqual([]);
}

test.describe('MOCK1: the wow-tour mock-up', () => {
  test.describe.configure({ timeout: 300_000 });

  test('the door is the first screen; the keyboard walks the tour; axe finds nothing', async ({ page }) => {
    await page.goto('/tour/');
    await expect(page.getByRole('heading', { level: 1, name: 'הבית המודרני החם' })).toBeVisible();
    await expect(page.locator('#tour-enter')).toBeVisible();
    await expect(page.locator('.tour-temp')).toHaveText('הדלת זמנית');
    await ready(page);
    await audit(page, 'the door');
    // the door's button
    await page.locator('#tour-enter').focus();
    await page.keyboard.press('Enter');
    await atRest(page);
    await expect(page.locator('.tour-spot[data-on]')).toHaveCount(tour.slots.length);
    await expect(page.locator('.tour-count')).toContainText('מהחדר');
    await audit(page, 'the room at rest');
    // a product and its wheel
    const art = page.locator('.tour-spot[data-slot="framed-art"]');
    await art.focus();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('dialog')).toBeVisible();
    await atRest(page);
    await audit(page, 'the wheel');
    await page.keyboard.press('ArrowLeft');
    await expect.poll(() => page.evaluate(() => window.__hdTour!.selection['framed-art'])).toBe(2);
    await page.keyboard.press('Enter');
    await expect(page.getByRole('dialog')).toBeHidden();
    await atRest(page);
    await expect(art).toBeFocused();
    // the folded control, from the keyboard: it opens, and the focus is on the first room
    await page.locator('#tour-fold').focus();
    await page.keyboard.press('Enter');
    await expect(page.locator('#tour-fold')).toHaveAttribute('aria-expanded', 'true');
    await expect(page.locator('#tour-out')).toBeFocused();
    await page.waitForFunction(() => window.__hdTour?.busy === false);
    await audit(page, 'the panel of the folded control');
    // the temporary switches, last in it
    await page.locator('.tour-panel summary').focus();
    await page.keyboard.press('Enter');
    const s1 = page.locator('input[name="tour-sw"][value="s1"]');
    await s1.focus();
    await page.keyboard.press('ArrowDown');
    await expect(page.locator('input[name="tour-sw"]:checked')).not.toHaveValue('s1');
    await page.locator('.tour-panel summary').focus();
    await page.keyboard.press('Enter');
    // the rooms' buttons: back to the door, and in again
    await page.locator('#tour-out').focus();
    await page.keyboard.press('Enter');
    await atRest(page, 'door');
    await expect(page.locator('#tour-fold')).toHaveAttribute('aria-expanded', 'false');
    await expect(page.locator('#tour-enter')).toBeVisible();
    await more(page);
    await page.locator('#tour-living').focus();
    await page.keyboard.press('Enter');
    await atRest(page);
    await expect(page.locator('.tour-rooms button[aria-disabled="true"]')).toHaveCount(2);
  });

  test('after each reveal (A, B, C) settles, the frame is the plain composition, pixel for pixel', async ({ page }) => {
    const want = await plain(page);
    const got: Record<string, typeof want> = {};
    for (const fx of ['a', 'b', 'c'] as const) {
      await page.goto(`/tour/?fx=${fx}`);
      await ready(page);
      await page.locator('#tour-enter').click();
      await atRest(page);
      got[fx] = await hashes(page);
      expect(got[fx], `reveal ${fx}`).toEqual(want);
    }
    note('settled.json', { plain: want, after: got });
  });

  test('no jump at any seam: every effect starts on the frame before it and ends on the frame after it', async ({ page }) => {
    await page.goto('/tour/');
    await ready(page);
    const seams = await page.evaluate(async () => {
      const e = window.__hdTour!;
      const m = window.__hdTourFx!;
      const ui = { ring() {}, label() {}, spots() {}, count() {}, dims() {} };
      const px = (name: string) => parseFloat(getComputedStyle(document.querySelector('.tour')!).getPropertyValue(name));
      const door = { cx: px('--dx'), cy: px('--dy'), hw: px('--dw') / 2, hh: px('--dh') / 2, r: px('--dr') };
      await e.products();
      await e.otherHouse();
      const vase = e.slot('vase');
      for (const o of vase.options) await e.option('vase', o.position);
      e.sync = true;
      await m.enter(e);
      for (const k of ['a', 'b', 'c'] as const) {
        await m.reveal(e, ui, k);
        await m.collect(e, ui);
      }
      await m.reveal(e, ui, 'b');
      const b = vase.options[0]!.box;
      await e.moveCam('zoom-in', e.camFor([b[0] - 0.02, b[1] + 0.02, b[2] - 0.05, b[3] + 0.05], 0.5), 1000, (k) => {
        e.d.vig = 0.1 * k;
        e.d.vigBox = vase.rect;
      });
      await m.swap(e, ui, vase, 2, 1, 's1');
      await m.swap(e, ui, vase, 3, 1, 's2');
      await m.swap(e, ui, vase, 1, -1, 's3');
      await e.moveCam('zoom-out', e.rest, 1000, (k) => (e.d.vig = 0.1 * (1 - k)));
      await m.style(e, ui, 'nordic', 'y1', 'b');
      await m.style(e, ui, 'warm-modern', 'y1', 'b');
      await m.style(e, ui, 'nordic', 'y2', 'b');
      await m.style(e, ui, 'warm-modern', 'y2', 'b');
      await m.collect(e, ui);
      await m.leave(e, door);
      return e.seams;
    });
    note('seams.json', seams);
    const labels = seams.map((s) => s.label);
    for (const l of [
      'enter',
      'reveal-a',
      'reveal-b',
      'reveal-c-in',
      'reveal-c',
      'collect',
      'zoom-in',
      'swap-s1',
      'swap-s2',
      'swap-s3',
      'zoom-out',
      'style-y1',
      'style-y1-nordic',
      'style-y2',
      'leave',
    ])
      expect(labels, `the seam of ${l} was measured`).toContain(l);
    const bad = seams
      .filter((s) => s.first.max > 0 || s.last.max > 0)
      .map((s) => `${s.label}: first ${s.first.max} (${s.first.px} px), last ${s.last.max} (${s.last.px} px)`);
    expect(bad, bad.join('\n')).toEqual([]);
  });

  test('the phase 2 layers load and swap: a variant changes its own rectangle and nothing outside it', async ({ page }) => {
    await page.goto('/tour/?skip=1');
    await ready(page);
    await atRest(page);
    const rows = await page.evaluate(async () => {
      const e = window.__hdTour!;
      const m = window.__hdTourFx!;
      const ui = { ring() {}, label() {}, spots() {}, count() {}, dims() {} };
      const { width: w, height: h } = e.gl;
      e.sync = true;
      const full = (): Uint8Array => e.read([0, 0, w, h]);
      const base = full();
      const out: { slot: string; position: number; inside: number; outside: number; back: number }[] = [];
      const diff = (a: Uint8Array, b: Uint8Array, r: [number, number, number, number] | null) => {
        let inside = 0;
        let outside = 0;
        for (let i = 0; i < a.length; i += 4) {
          if (a[i] === b[i] && a[i + 1] === b[i + 1] && a[i + 2] === b[i + 2]) continue;
          const x = (i / 4) % w;
          const y = (i / 4 - x) / w;
          if (r && x >= r[0] && x < r[2] && y >= r[1] && y < r[3]) inside++;
          else outside++;
        }
        return { inside, outside };
      };
      for (const id of Object.keys(e.selection)) {
        const s = e.slot(id);
        const r: [number, number, number, number] = [
          Math.round(s.rect[0] * w),
          Math.round(s.rect[2] * h),
          Math.round(s.rect[1] * w),
          Math.round(s.rect[3] * h),
        ];
        for (const o of s.options.slice(1)) {
          await m.swap(e, ui, s, o.position, 1, 's1');
          const d = diff(base, full(), r);
          await m.swap(e, ui, s, 1, -1, 's1');
          out.push({ slot: id, position: o.position, ...d, back: diff(base, full(), null).outside });
        }
      }
      return out;
    });
    note('swap.json', rows);
    expect(rows.length, 'every variant on the wheel: 10 products and 2 cushion sets').toBe(tour.slots.reduce((n, s) => n + s.options.length - 1, 0));
    for (const r of rows) {
      expect(r.inside, `${r.slot} ${r.position} is drawn`).toBeGreaterThan(0);
      expect(r.outside, `${r.slot} ${r.position}: pixels changed outside its rectangle`).toBe(0);
      expect(r.back, `${r.slot}: the default comes back exactly`).toBe(0);
    }
  });

  test('the encoding gate on the phase 2 layers (QA R8 F7): every option against its approved composite', async ({ page }) => {
    // the render folder's own files, as tools/make-tour.ts reads them
    const t = read<{ layers: string; manifest: string }>(resolve(SITE, 'tools/tour/living-room.warm-modern.json'));
    const dir = resolve(REPO, t.layers);
    type Lm = {
      layers: { id: string; file?: string }[];
      variants: Record<string, { file: string; truth: string }[]>;
      slot_cushions: { order: string[]; sets: Record<string, { layer: string }> };
      truths: { default: Record<string, string> };
    };
    const lm = read<Lm>(join(dir, t.manifest));
    const source = (slot: string, n: number): { layer: string; truth: string } => {
      if (slot === 'cushions') {
        const set = lm.slot_cushions.order[n]!;
        return { layer: lm.slot_cushions.sets[set]!.layer, truth: lm.truths.default[set]! };
      }
      if (n === 0) return { layer: lm.layers.find((l) => l.id === slot)!.file!, truth: lm.truths.default[lm.slot_cushions.order[0]!]! };
      const v = lm.variants[slot]![n - 1]!;
      return { layer: v.file, truth: v.truth };
    };
    await page.goto('/tour/?skip=1');
    await ready(page);
    await atRest(page);
    const out: Record<string, Measure & { pass: boolean }> = {};
    const bad: string[] = [];
    for (const s of tour.slots) {
      const r = [Math.round(s.rect[0] * W), Math.round(s.rect[2] * H), Math.round(s.rect[1] * W), Math.round(s.rect[3] * H)] as const;
      const cut = { left: r[0], top: r[1], width: r[2] - r[0], height: r[3] - r[1] };
      for (const [n, o] of s.options.entries()) {
        const b64 = await page.evaluate(
          async ([id, pos, rect]) => {
            const e = window.__hdTour!;
            const m = window.__hdTourFx!;
            e.sync = true;
            const ui = { ring() {}, label() {}, spots() {}, count() {}, dims() {} };
            for (const other of Object.keys(e.selection)) if (other !== id && e.selection[other] !== 1) await m.swap(e, ui, e.slot(other), 1, -1, 's1');
            await m.swap(e, ui, e.slot(id), pos, 1, 's1');
            const a = e.read(rect as [number, number, number, number]);
            let s = '';
            for (let i = 0; i < a.length; i += 0x8000) s += String.fromCharCode(...a.subarray(i, i + 0x8000));
            return btoa(s);
          },
          [s.id, o.position, r] as const,
        );
        const enc = Buffer.from(b64, 'base64');
        const src = source(s.id, n);
        const truth = await sharp(join(dir, src.truth)).ensureAlpha().extract(cut).raw().toBuffer();
        const alpha = await sharp(join(dir, src.layer)).ensureAlpha().extract(cut).raw().toBuffer();
        // the product's own opaque pixels: what its layer's encoding decides (the base under a soft edge is the base's gate)
        const keep: number[] = [];
        for (let i = 0; i < alpha.length; i += 4) if (alpha[i + 3] === 255) keep.push(i);
        const a = new Uint8Array(keep.length * 4);
        const b = new Uint8Array(keep.length * 4);
        keep.forEach((k, j) => {
          a.set(truth.subarray(k, k + 4), j * 4);
          b.set(enc.subarray(k, k + 4), j * 4);
        });
        const m = measure(a, b, false);
        const f = failures(m);
        out[`${s.id} ${o.position}`] = { ...m, pass: f.length === 0 };
        for (const x of f) bad.push(`${s.id} ${o.position}: ${x}`);
      }
    }
    note('encoding.json', out);
    const worst = Object.entries(out).sort((x, y) => y[1].de00_p99 - x[1].de00_p99)[0]!;
    console.log(
      `encoding, phase 2 layers at 1:1: ${Object.keys(out).length} options; the worst ΔE00 p99 ${worst[1].de00_p99} (${worst[0]}), p99 ${worst[1].p99}`,
    );
    expect(bad, bad.join('\n')).toEqual([]);
  });

  test('reduced motion: every effect is a short dissolve, and the room still ends on the plain composition', async ({ browser }) => {
    const ctx = await browser.newContext({ reducedMotion: 'reduce', locale: 'he-IL' });
    const page = await ctx.newPage();
    const want = await plain(page);
    await page.goto('/tour/?fx=a');
    await ready(page);
    await page.locator('#tour-enter').click();
    await atRest(page);
    expect(await hashes(page), 'the room after the calm reveal').toEqual(want);
    // nothing moved over the room either: no ring ran
    // the rings and the measure lines are animated from the page (el.animate); a CSSTransition on them is the
    // inherited `color` of the stage changing phase, which the reduced-motion rule itself shortens to 0.01 ms
    const moved = await page.evaluate(() =>
      document
        .getAnimations()
        .filter((a) => a.constructor.name !== 'CSSTransition' && (a.effect as KeyframeEffect | null)?.target?.closest?.('.tour-rings'))
        .map((a) => {
          const t = (a.effect as KeyframeEffect).target!;
          const prop = (a as unknown as { transitionProperty?: string }).transitionProperty ?? '';
          return `${a.constructor.name} ${prop} ${t.tagName}.${t.className || t.parentElement?.className} ${a.playState}`;
        }),
    );
    expect(moved, moved.join('\n')).toEqual([]);
    await page.locator('.tour-spot[data-slot="framed-art"]').click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await atRest(page);
    await page.keyboard.press('ArrowLeft');
    await expect.poll(() => page.evaluate(() => window.__hdTour!.selection['framed-art'])).toBe(2);
    await page.keyboard.press('Enter');
    await atRest(page);
    await more(page);
    await page.locator('.segmented button[data-house="nordic"]').click();
    await expect.poll(() => page.evaluate(() => window.__hdTourState?.house)).toBe('nordic');
    await atRest(page);
    await more(page);
    await page.locator('.segmented button[data-house="warm-modern"]').click();
    await expect.poll(() => page.evaluate(() => window.__hdTourState?.house)).toBe('warm-modern');
    await atRest(page);
    const ran = await page.evaluate(() =>
      Object.fromEntries(Object.entries(window.__hdTour!.frames).map(([k, v]) => [k, Math.round(v.dt.reduce((a, b) => a + b, 0))])),
    );
    note('reduced-motion.json', ran);
    const moving = ['reveal-a', 'reveal-b', 'reveal-c', 'collect', 'swap-s1', 'swap-s2', 'swap-s3', 'style-y1', 'style-y2', 'style-y1-nordic', 'door-push'];
    expect(Object.keys(ran).filter((l) => moving.includes(l))).toEqual([]);
    for (const l of ['enter', 'reveal-fade', 'swap-fade', 'style-fade']) expect(Object.keys(ran), l).toContain(l);
    // a dissolve is short: 300 ms, and the swap's 150 ms (plus the frame it starts on)
    for (const [l, ms] of Object.entries(ran)) expect(ms, `${l} took ${ms} ms`).toBeLessThanOrEqual(l === 'swap-fade' ? 320 : 480);
    await ctx.close();
  });

  test('the first load on a phone stays under 3 MB until the room is composed', async ({ browser }) => {
    const { defaultBrowserType: _b, ...pixel } = devices['Pixel 7'];
    const ctx = await browser.newContext({ ...pixel, locale: 'he-IL' });
    const page = await ctx.newPage();
    // what the room needs to be shown; the other options and the Nordic house load behind it once it rests
    const background = (url: string) => /\/slots\/[a-z-]+\/(?!1\.)\d+\./.test(url) || /\/media\/rooms\//.test(url);
    let bytes = 0;
    let behind = 0;
    const urls = new Map<string, string>();
    const client = await ctx.newCDPSession(page);
    await client.send('Network.enable');
    client.on('Network.requestWillBeSent', (e) => void urls.set(e.requestId, e.request.url));
    client.on('Network.loadingFinished', (e) => (background(urls.get(e.requestId) ?? '') ? (behind += e.encodedDataLength) : (bytes += e.encodedDataLength)));
    await page.goto('/tour/');
    await ready(page);
    const door = bytes;
    expect(behind, 'nothing loads behind the door before the default products are in').toBe(0);
    // straight in: the room with its default products, revealed and at rest
    await page.locator('#tour-enter').click();
    await atRest(page);
    const room = bytes;
    note('first-load.json', { door_bytes: door, room_bytes: room });
    console.log(
      `the tour's first load (phone): the door ${(door / 1048576).toFixed(2)} MB, the room with its default products ${(room / 1048576).toFixed(2)} MB`,
    );
    expect(room).toBeLessThanOrEqual(3 * 1024 * 1024);
    await ctx.close();
  });
});
