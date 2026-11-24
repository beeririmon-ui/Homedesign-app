/**
 * MOCK4 (2026-11-18), the house as it stands (briefs/site-mock4-house-tour-2026-11-18.md), behind HD_PUBLIC=0:
 *
 *  1. the arrival v2: the door is the walk's first frame; the walk plays to the landing on M0 and gives the window to the
 *     room, which rests on the plain composition; nothing loads, decodes, uploads, compiles or measures while it plays;
 *  2. the names at the rest on HC sit on their doors (ARR-M1: the bath's lintel at u 0.3944–0.4114, the bedroom's
 *     centred at 0.496, the laundry without a name), and while the walk plays "דלג" is the one button; "דלג" lands at rest;
 *  3. the bedroom and the bathroom, from the panel (a temporary dissolve): at rest the frame is the plain composition of
 *     their layers, pixel for pixel; a mark for every product for sale and none for the furniture that is not; the
 *     owner's line counts them; the art 776445 (rights unclear) is ×1 only: no zoom in the bedroom, its own mark opens
 *     its card where it is, and a neighbour's close-up keeps it out of view;
 *  4. the encoding gate on the two rooms (QA R8 F7, tools/lib/encoding.ts): the composition at the layers' own width
 *     against the render folder's approved composites — the defaults and the sample's two variants — on the products'
 *     own opaque pixels;
 *  5. a phone's first load of each room stays under 3 MB, and the walk's own file under 3 MB.
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
type Arrival = { labels: { id: string; u: [number, number] }[]; videos: Record<'desktop' | 'phone', { bytes: number }> };
const arrival = read<Arrival>(resolve(SITE, '.generated/arrival.json'));
type Room = {
  slots: { id: string; fixed?: boolean; options: { position: number }[] }[];
  /** MOCK5: one box a ×1-only print (the bedroom's 776445 first, then 386242) */
  avoid: [number, number, number, number][];
  for_sale: number;
  sample: string;
};
const roomData = (id: string) => read<Room>(resolve(SITE, `.generated/tour.${id}.warm-modern.json`));

const ready = (page: Page) => page.waitForFunction(() => window.__hdTour?.ready === true, undefined, { timeout: 60_000 });
const atRest = (page: Page, phase: 'door' | 'room' = 'room') =>
  page.waitForFunction((p) => window.__hdTourState?.phase === p && window.__hdTourState.busy === false && window.__hdTour?.busy === false, phase, {
    timeout: 120_000,
  });
async function more(page: Page) {
  if ((await page.locator('#tour-fold').getAttribute('aria-expanded')) !== 'true') await page.locator('#tour-fold').click();
  await page.waitForFunction(() => window.__hdTourState?.more === true && window.__hdTour?.busy === false);
}
/** the composition's own pixels and the canvas, as two hashes (e2e/mock1.spec.ts) */
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

async function audit(page: Page, label: string) {
  const r = await new AxeBuilder({ page } as unknown as ConstructorParameters<typeof AxeBuilder>[0])
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  const summary = r.violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.length} × ${v.nodes[0]?.target.join(' ')} — ${v.help}`);
  expect(summary, `${label}\n${summary.join('\n')}`).toEqual([]);
}

test.describe('MOCK4: the house as it stands', () => {
  test.describe.configure({ timeout: 300_000 });

  test('axe finds nothing: the door, the rest on HC with the names, the bedroom at rest, the bathroom’s close-up (a phone and a wide screen)', async ({
    browser,
  }) => {
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
      await page.goto('/tour/');
      await ready(page);
      await page.waitForFunction(() => window.__hdTour?.warmReady === true, undefined, { timeout: 60_000 });
      await audit(page, `${vp.width}: the door`);
      await page.locator('#tour-enter').click();
      await page.waitForFunction(() => (window.__hdTourState?.walk ?? 0) >= 383, undefined, { timeout: 60_000 });
      await page.locator('video.tour-video').evaluate((el: HTMLVideoElement) => el.pause());
      await audit(page, `${vp.width}: the rest on HC`);
      await page.locator('#tour-skip').click();
      await atRest(page);
      await more(page);
      await page.locator('#tour-master').click();
      await page.waitForFunction(() => window.__hdTourState?.room === 'master');
      await atRest(page);
      await audit(page, `${vp.width}: the bedroom at rest`);
      await more(page);
      await page.locator('#tour-bath').click();
      await page.waitForFunction(() => window.__hdTourState?.room === 'bath');
      await atRest(page);
      const tile = page.locator('.tour-tile[data-slot="hand-towel"]');
      if (await tile.isVisible()) await tile.click();
      else await page.locator('.tour-spot[data-slot="hand-towel"]').click({ force: true });
      await expect(page.getByRole('dialog')).toBeVisible();
      await atRest(page);
      await audit(page, `${vp.width}: the bathroom's close-up`);
      await ctx.close();
    }
  });

  test('the arrival: the door, the walk to the landing, the names on the doors at the rest on HC, and nothing loads inside it', async ({ page }) => {
    const want = await plain(page, 'living-room');
    await page.goto('/tour/');
    await ready(page);
    await page.waitForFunction(() => window.__hdTour?.warmReady === true, undefined, { timeout: 60_000 });
    // the door: the walk's first frame is the page's first paint
    const v = page.locator('video.tour-video');
    await expect(v).toBeVisible();
    expect(await page.locator('img.tour-door-img').evaluate((el: HTMLImageElement) => el.currentSrc)).toMatch(/\/media\/tour\/arrival\/d0\.1920\.webp$/);
    expect(await v.evaluate((el: HTMLVideoElement) => el.currentSrc || el.src)).toMatch(/\/media\/tour\/arrival\/arrival\.1920\.60\.mp4$/);
    await page.evaluate(() => window.__hdTourFx!.metrics.reset());
    await page.locator('#tour-enter').click();
    // while the walk plays, "דלג" is the one button (route ch. 11.1): the folded control is not there
    await page.waitForFunction(() => (window.__hdTourState?.walk ?? 0) > 60, undefined, { timeout: 60_000 });
    await expect(page.locator('#tour-skip')).toBeVisible();
    await expect(page.locator('#tour-fold')).toBeHidden();
    await expect(page.locator('#tour-enter')).toBeHidden();
    // the rest on HC: the walk is held there, and the names are read off the page
    await page.waitForFunction(() => (window.__hdTourState?.walk ?? 0) >= 383, undefined, { timeout: 60_000 });
    await v.evaluate((el: HTMLVideoElement) => el.pause());
    const at = await page.evaluate(() => {
      const win = document.querySelector('.tour-win')!.getBoundingClientRect();
      const lines = Array.from(document.querySelectorAll<SVGLineElement>('.tour-doors line')).map((l) => ({
        u: [Number(l.getAttribute('x1')), Number(l.getAttribute('x2'))],
        on: Number(getComputedStyle(l).opacity),
      }));
      const names = Array.from(document.querySelectorAll<HTMLElement>('.tour-door-name')).map((n) => {
        const r = n.getBoundingClientRect();
        return {
          text: n.textContent,
          cx: (r.left + r.width / 2 - win.left) / win.width,
          bottom: (r.bottom - win.top) / win.height,
          on: Number(getComputedStyle(n).opacity),
        };
      });
      return { frame: window.__hdTourState!.walk, lines, names };
    });
    note('arrival-labels.json', at);
    expect(at.names.map((n) => n.text)).toEqual(['רחצה', 'חדר ילד', 'חדר ילדה', 'חדר שינה']);
    for (const n of at.names) expect(n.on, `${n.text} is on at the rest`).toBeGreaterThan(0.99);
    // ARR-M1: the bath's lintel runs over u 0.3944–0.4114; the bedroom's name is centred at 0.496; no laundry
    const bath = at.lines[0]!.u.sort();
    expect(bath[0]).toBeCloseTo(0.3944, 3);
    expect(bath[1]).toBeCloseTo(0.4114, 3);
    expect(at.names[3]!.cx).toBeCloseTo(0.496, 2);
    expect(at.lines).toHaveLength(arrival.labels.length);
    await v.evaluate((el: HTMLVideoElement) => el.play());
    await atRest(page);
    // the room it lands in rests on the plain composition
    expect(await hashes(page)).toEqual(want);
    const walk = await page.evaluate(() => window.__hdTourFx!.metrics.effects['arrival']);
    note('arrival-counters.json', walk);
    expect(walk, 'the walk ran as an effect').toBeTruthy();
    expect(walk!.counts, 'nothing loads, decodes, uploads, compiles or measures while the walk plays').toEqual({
      decode: 0,
      upload: 0,
      compile: 0,
      readback: 0,
      layout: 0,
    });
    // "דלג": straight to the room at rest, with the reveal
    await page.goto('/tour/');
    await ready(page);
    await page.waitForFunction(() => window.__hdTour?.warmReady === true, undefined, { timeout: 60_000 });
    await page.locator('#tour-enter').click();
    await page.waitForFunction(() => (window.__hdTourState?.walk ?? 0) > 30, undefined, { timeout: 60_000 });
    const t0 = Date.now();
    await page.locator('#tour-skip').click();
    await atRest(page);
    note('skip.json', { ms_to_rest: Date.now() - t0 });
    expect(await hashes(page)).toEqual(want);
  });

  // MOCK5: a mark per product of the frame (MB0 19, B2 12); the owner's line counts the room, every frame of it, a
  // product once (the bedroom 22 with MB1, the bath 18 with B1: e2e/mock5.spec.ts)
  for (const [id, count, room] of [
    ['master', 19, 22],
    ['bath', 12, 18],
  ] as const) {
    test(`the ${id === 'master' ? 'bedroom' : 'bathroom'}: from the panel; the plain composition at rest; a mark per product for sale; the owner's line`, async ({
      page,
    }) => {
      const r = roomData(id);
      expect(r.for_sale).toBe(count);
      const want = await plain(page, id);
      // from the living room, through the panel (the temporary dissolve)
      await page.goto('/tour/?skip=1');
      await ready(page);
      await atRest(page);
      await more(page);
      await page.locator(`#tour-${id}`).click();
      await page.waitForFunction((x) => window.__hdTourState?.room === x, id);
      await atRest(page);
      expect(await hashes(page), 'the room rests on the plain composition of its layers').toEqual(want);
      await expect(page.locator('.tour-spot')).toHaveCount(count);
      for (const s of r.slots.filter((x) => x.fixed)) await expect(page.locator(`.tour-spot[data-slot="${s.id}"]`)).toHaveCount(0);
      await expect(page.locator('.tour-sale')).toHaveText(`${room} מוצרים למכירה בחדר`);
      await expect(page.locator('#tour-title')).toHaveText(new RegExp(id === 'master' ? '^חדר שינה' : '^חדר רחצה'));
      // the sample slot's wheel: three options, and the room swaps the product
      await page.locator(`.tour-spot[data-slot="${r.sample}"]`).click({ force: true });
      await expect(page.getByRole('dialog')).toBeVisible();
      await atRest(page);
      await expect(page.locator('.arc-card')).toHaveCount(3);
      await page.keyboard.press('ArrowLeft');
      await expect.poll(() => page.evaluate((s) => window.__hdTour!.selection[s], r.sample)).toBe(2);
      await page.keyboard.press('Escape');
      await expect(page.getByRole('dialog')).toBeHidden();
      await atRest(page);
    });
  }

  test('the art 776445 is ×1 only: no zoom in the bedroom, its mark opens its card where it is, a neighbour’s close-up leaves it out', async ({ browser }) => {
    const r = roomData('master');
    const boxes = r.avoid;
    expect(boxes.length, 'MOCK5: both prints of MB0 are ×1 only (776445 and 386242)').toBe(2);
    const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, hasTouch: true, isMobile: true });
    const page = await ctx.newPage();
    await page.goto('/tour/?skip=1&room=master');
    await ready(page);
    await atRest(page);
    await expect(page.locator('#tour-zoom')).toBeHidden();
    const view = () =>
      page.evaluate(() => {
        const e = window.__hdTour!;
        const fw = Math.max(e.vp.w, e.vp.h * (16 / 9));
        const fh = fw / (16 / 9);
        const hu = e.vp.w / (2 * fw * e.cam.z);
        const hv = e.vp.h / (2 * fh * e.cam.z);
        return { z: e.cam.z, rest: e.rest.z, u: [e.cam.cu - hu, e.cam.cu + hu], v: [e.cam.cv - hv, e.cam.cv + hv] };
      });
    const seen: Record<string, unknown> = {};
    for (const slot of ['framed-art', 'framed-art-2', 'throw', 'bedding', 'pillowcases']) {
      await page.locator(`.tour-tile[data-slot="${slot}"]`).click();
      await expect(page.getByRole('dialog')).toBeVisible();
      await atRest(page);
      const v = await view();
      seen[slot] = v;
      const zoomed = v.z > v.rest * 1.001;
      const showsArt = boxes.some((a) => v.u[0]! < a[1] && v.u[1]! > a[0] && v.v[0]! < a[3] && v.v[1]! > a[2]);
      expect(!(zoomed && showsArt), `${slot}: a zoomed view never shows the art`).toBe(true);
      if (slot.startsWith('framed-art')) expect(zoomed, `${slot}: no close-up next to the art`).toBe(false);
      await page.getByRole('button', { name: 'סגירת התקריב' }).click();
      await expect(page.getByRole('dialog')).toBeHidden();
      await atRest(page);
    }
    note('art-x1.json', { avoid: boxes, seen });
    // the throw does get its close-up, below the art
    expect((seen['throw'] as { z: number; rest: number }).z).toBeGreaterThan((seen['throw'] as { rest: number }).rest * 1.2);
    await ctx.close();
  });

  test('the encoding gate on the bedroom and the bathroom: the defaults and the sample’s variants against their approved composites', async ({ page }) => {
    const out: Record<string, Measure & { pass: boolean; identical: number }> = {};
    const bad: string[] = [];
    for (const id of ['master', 'bath'] as const) {
      const cfg = read<{ layers: string; manifest: string; truth: string; sample: string }>(resolve(SITE, `tools/tour/${id}.warm-modern.json`));
      const dir = resolve(REPO, cfg.layers);
      type Lm = {
        layers: { slot: string; layer: string }[];
        variants: { slot: string; default: boolean; layer: string; frame?: string; composite?: string }[];
      };
      const lm = read<Lm>(join(dir, cfg.manifest));
      const variants = lm.variants.filter((x) => x.slot === cfg.sample && !x.default);
      const cases = [
        { pos: 1, truth: cfg.truth, alpha: lm.layers.map((l) => l.layer) },
        ...variants.map((x, i) => ({
          pos: i + 2,
          truth: x.composite ?? x.frame!,
          alpha: lm.layers
            .filter((l) => l.slot !== cfg.sample)
            .map((l) => l.layer)
            .concat(x.layer),
        })),
      ];
      await page.goto(`/tour/?skip=1&room=${id}`);
      await ready(page);
      await atRest(page);
      const width = await page.evaluate(() => window.__hdTour!.gl.width);
      expect(width, 'a wide screen composes at the layers’ own width').toBe(2720);
      for (const c of cases) {
        const b64 = await page.evaluate(
          async ([slot, pos]) => {
            const e = window.__hdTour!;
            const m = window.__hdTourFx!;
            e.sync = true;
            const ui = { ring() {}, label() {}, spots() {}, count() {}, dims() {} };
            await e.option(slot, pos);
            if (e.selection[slot] !== pos) await m.swap(e, ui, e.slot(slot), pos, pos > e.selection[slot]! ? 1 : -1, 's1');
            const a = e.read([0, 0, e.gl.width, e.gl.height]);
            let s = '';
            for (let i = 0; i < a.length; i += 0x8000) s += String.fromCharCode(...a.subarray(i, i + 0x8000));
            return btoa(s);
          },
          [cfg.sample, c.pos] as const,
        );
        const enc = Buffer.from(b64, 'base64');
        const truth = await sharp(join(dir, c.truth)).ensureAlpha().raw().toBuffer();
        // every product's own opaque pixels (what its layer's encoding decides; the base under a soft edge is the base's)
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
    note('encoding-rooms.json', out);
    console.log(
      Object.entries(out)
        .map(([k, m]) => `${k}: ΔE00 p99 ${m.de00_p99}, p99 ${m.p99}, identical ${(m.identical * 100).toFixed(1)}%`)
        .join('\n'),
    );
    expect(bad, bad.join('\n')).toEqual([]);
  });

  test('a phone’s first load of each room stays under 3 MB, and the walk’s own file under 3 MB', async ({ browser }) => {
    const { defaultBrowserType: _b, ...pixel } = devices['Pixel 7'];
    const sizes: Record<string, number> = {};
    for (const id of ['master', 'bath'] as const) {
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
    note('first-load-rooms.json', { ...sizes, walk_phone: arrival.videos.phone.bytes, walk_desktop: arrival.videos.desktop.bytes });
    console.log(
      Object.entries(sizes)
        .map(([k, b]) => `${k}: ${(b / 1048576).toFixed(2)} MB`)
        .join(', '),
    );
    for (const b of Object.values(sizes)) expect(b).toBeLessThanOrEqual(3 * 1024 * 1024);
    expect(arrival.videos.phone.bytes).toBeLessThanOrEqual(3 * 1024 * 1024);
    expect(arrival.videos.desktop.bytes).toBeLessThanOrEqual(8 * 1024 * 1024);
  });
});
