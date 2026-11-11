/**
 * S10: the warm-modern house in the room engine (DIR2), behind the flag. Its phase 1 as approved (AP3-WM): the v3c base
 * and the cushions slot, three sets on the wheel, B the default (CAM1); the status label; the soft switch between the
 * houses in the engine (1.0 s, 0.3 s with reduced motion), every layer in the one composed frame; and the swap of a set,
 * which may change nothing outside the sets' own area (studio rules ו.5), measured on what the browser shows.
 */
import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import sharp from 'sharp';
import { mkdirSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
/** S12: the evidence screens, when HD_SHOTS_DIR is set */
const SHOTS = process.env.HD_SHOTS_DIR ?? null;
const HOUSE = '/rooms/living-room/?style=warm-modern';
const LABEL = 'הבית המודרני החם, שלב 1: אושר. עוד לא באתר הציבורי';
const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'];
type Box = [number, number, number, number];
type HouseFile = {
  scene: {
    source: string;
    aspect: number;
    widths: { lo: number };
    slots: Record<string, { product: { rect: Box; src: string[] }; shadow: { rect: Box; src: string[] } | null }>;
  };
  room: { slots: { id: string; name_he: string }[] };
  sets: { position: number; id: string; items: { variant_id: string | null }[] }[];
};
const house = JSON.parse(readFileSync(resolve(SITE, '.generated/house.living-room.warm-modern.json'), 'utf8')) as HouseFile;
const LAYERED = house.scene.source.startsWith('layers-v3c');
const SLOT = house.room.slots[0]!;

type SwitchTimes = { from: string; to: string; asked: number; start: number; end: number };
type Engine = { ready: boolean; cam: { cu: number; cv: number; z: number }; vp: { w: number; h: number } };
/** S12, QA ת26: the longest gap between two frames the engine drew while animating (window.__hdFrames, ms) */
const frameGap = (page: Page) => page.evaluate(() => Math.max(16, ...(window.__hdFrames ?? [])));
const switchTimes = (page: Page) => page.evaluate(() => (window as unknown as { __hdHouseSwitch?: SwitchTimes }).__hdHouseSwitch ?? null);
const engineOf = (page: Page) =>
  page.evaluate(() => {
    const e = (window as unknown as { __hdEngine?: Engine }).__hdEngine;
    return e ? { ready: e.ready, cam: { ...e.cam }, vp: { ...e.vp } } : null;
  });

/**
 * Runs in the page: reads the canvas right after the display pass draws it, on a 64 × 36 grid (the luma of each point).
 * `grab(mix)` draws the dissolve's state `mix` with the engine's own camera (no parallax, no drift) and reads it;
 * `record(on)` reads every frame the engine draws while on, and returns them when turned off.
 */
function installProbe() {
  type DisplayState = { mix: number } & Record<string, unknown>;
  type Comp = { gl: WebGL2RenderingContext; display(s: DisplayState): void };
  const e = (window as unknown as { __hdEngine: { comp: Comp; cam: object; vp: object; aspect: number; requestRender(): void } }).__hdEngine;
  const comp = e.comp;
  const gl = comp.gl;
  const read = (): number[] => {
    const W = gl.drawingBufferWidth;
    const H = gl.drawingBufferHeight;
    const buf = new Uint8Array(W * H * 4);
    gl.readPixels(0, 0, W, H, gl.RGBA, gl.UNSIGNED_BYTE, buf);
    const out: number[] = [];
    for (let j = 0; j < 36; j++)
      for (let i = 0; i < 64; i++) {
        const x = Math.floor(((i + 0.5) / 64) * W);
        const y = Math.floor(((j + 0.5) / 36) * H);
        const k = (y * W + x) * 4;
        out.push(0.2126 * buf[k]! + 0.7152 * buf[k + 1]! + 0.0722 * buf[k + 2]!);
      }
    return out;
  };
  const display = comp.display.bind(comp);
  let frames: { mix: number; mean: number }[] | null = null;
  comp.display = (s: DisplayState) => {
    display(s);
    if (frames) {
      const g = read();
      frames.push({ mix: s.mix, mean: g.reduce((a, b) => a + b, 0) / g.length });
    }
  };
  window.__hdProbe = {
    grab(mix: number) {
      display({ cam: e.cam, vp: e.vp, aspect: e.aspect, mix, parallax: 0, focus: 0.3, drift: [0, 0], blur: 0 });
      return read();
    },
    record(on: boolean) {
      const was = frames ?? [];
      frames = on ? [] : null;
      return was;
    },
    restore() {
      e.requestRender();
    },
  };
}

async function audit(page: Page, label: string) {
  const r = await new AxeBuilder({ page } as unknown as ConstructorParameters<typeof AxeBuilder>[0]).withTags(TAGS).analyze();
  const summary = r.violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.length} × ${v.nodes[0]?.target.join(' ')} — ${v.help}`);
  expect(summary, `${label}\n${summary.join('\n')}`).toEqual([]);
}
async function houseReady(page: Page, url = HOUSE) {
  await page.goto(url);
  await expect(page.locator('section.stage[data-house="warm-modern"]')).toBeVisible({ timeout: 20_000 });
  await expect(page.locator(`button.hotspot[data-slot="${SLOT.id}"]`)).toBeAttached({ timeout: 20_000 });
}
/** the engine starts on the first sign of intent: a press on the stage (here on the wall, away from the sofa) */
async function engineReady(page: Page) {
  const box = (await page.locator('section.stage').boundingBox())!;
  await page.mouse.click(box.x + 30, box.y + box.height / 2);
  await expect.poll(async () => (await engineOf(page))?.ready, { timeout: 20_000 }).toBe(true);
}

test.describe("a house's own address (S10 question 7, S11)", () => {
  test('?style=warm-modern is served that house’s own page: no Nordic poster in it, the page CSP; the Nordic address is unchanged', async ({ request }) => {
    const house = await request.get(HOUSE);
    expect(house.status()).toBe(200);
    const html = await house.text();
    expect(html).not.toContain('class="poster"');
    expect(html).not.toContain('/media/rooms/living-room/nordic/M0/base/shell.');
    expect(html).toContain('house-pending');
    expect(house.headers()['content-security-policy']).toContain("default-src 'self'");
    const nordic = await request.get('/rooms/living-room/');
    expect(nordic.status()).toBe(200);
    expect(await nordic.text()).toContain('/media/rooms/living-room/nordic/M0/base/shell.');
    expect(nordic.headers()['content-security-policy']).toContain("default-src 'self'");
    // a style without a house is the Nordic page, as before
    expect(await (await request.get('/rooms/living-room/?style=no-such-house')).text()).toContain('class="poster"');
  });
});

test.describe('the warm-modern house in the room engine (S10)', () => {
  test('entering at its address: its own picture, the status label, one slot with a mark, B the default', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.setViewportSize({ width: 400, height: 800 });
    const asked: string[] = [];
    const nordicPoster: string[] = [];
    page.on('request', (r) => void (r.url().includes('/media/house/') && asked.push(r.url())));
    // S10 question 7 (S11): a direct entry downloads no Nordic poster for nothing
    page.on('request', (r) => void (r.url().includes('/media/rooms/living-room/nordic/M0/base/shell.') && nordicPoster.push(r.url())));
    // S12, QA ת23: nothing of the Nordic house at all: its layers, its hall, the T-E0 frames (1.4 MB at S10)
    const nordicAny: string[] = [];
    page.on('request', (r) => void (/\/media\/(rooms\/(living-room|hall)\/nordic|transitions)\//.test(r.url()) && nordicAny.push(r.url())));
    const wheelChunk = page.waitForRequest(/\/VariantWheel-[^/]*\.js$/, { timeout: 30_000 });
    await houseReady(page);
    await expect(page.locator('.stage-status')).toHaveText(LABEL);
    await expect(page.locator('#room-title')).toContainText('מודרני חם');
    // the poster is the house's own, never the Nordic one
    await expect.poll(() => page.locator('img.poster').evaluate((i: HTMLImageElement) => i.currentSrc)).toContain('/media/house/living-room/warm-modern/');
    // the other slots are part of the base: no wheel and no mark for them
    await expect(page.locator('button.hotspot')).toHaveCount(1);
    await expect(page.locator('.slot-list > li')).toHaveCount(1);
    await expect(page.locator('.segmented button[data-house="warm-modern"]')).toHaveAttribute('aria-pressed', 'true');
    expect(nordicPoster, 'the Nordic poster is not downloaded on a direct entry to another house').toEqual([]);
    // the page's idle work (the wheel's chunk, the shown house's variants) has run: still nothing Nordic
    await wheelChunk;
    await expect.poll(() => asked.some((u) => /slots\/[a-z-]+\/[23]\.product\./.test(u)), { timeout: 15_000 }).toBe(true);
    expect(nordicAny, 'ת23: no Nordic layer, hall or T-E0 frame on a direct entry to the warm-modern house').toEqual([]);
    await engineReady(page);
    expect(await page.evaluate(() => (window as unknown as { __hdEngine?: { getSelection(): Record<string, number> } }).__hdEngine?.getSelection())).toEqual({
      [SLOT.id]: 1,
    });
    // QA on the layers (finding 1): composed at the files' own width, on a phone too, from its own files (one resample)
    for (const f of ['base/shell.2720.', `slots/${SLOT.id}/1.product.2720.webp`, `slots/${SLOT.id}/1.shadow.2720.webp`])
      expect(
        asked.some((u) => u.includes(f)),
        f,
      ).toBe(true);
    expect(asked.filter((u) => /\.(product|shadow)\.1920\.webp/.test(u))).toEqual([]);
    await audit(page, 'the warm-modern house at rest');
  });

  test('the wheel reaches all three sets (B, A, C), each with its pieces and prices; the whole set goes to the cart', async ({ page }) => {
    // its own rate-limit bucket (the API counts cart writes per client): the suite's other cart tests keep theirs
    await page.setExtraHTTPHeaders({ 'cf-connecting-ip': '198.51.100.10' });
    await houseReady(page);
    const spot = page.locator(`button.hotspot[data-slot="${SLOT.id}"]`);
    await spot.focus();
    await page.keyboard.press('Enter');
    const dialog = page.getByRole('dialog', { name: SLOT.name_he });
    await expect(dialog).toBeVisible({ timeout: 15_000 });
    const radios = dialog.getByRole('radio');
    await expect(radios).toHaveCount(3);
    const sel = () =>
      page.evaluate((id) => (window as unknown as { __hdEngine?: { getSelection(): Record<string, number> } }).__hdEngine?.getSelection()[id], SLOT.id);
    for (const [i, s] of house.sets.entries()) {
      if (i > 0) await page.keyboard.press('ArrowLeft'); // RTL: the next set
      await expect(radios.nth(i)).toHaveAttribute('aria-checked', 'true');
      await expect(radios.nth(i)).toHaveAttribute('aria-label', new RegExp(`סט ${s.id}`));
      await expect.poll(sel).toBe(i + 1);
      const items = dialog.locator('.set-item');
      await expect(items).toHaveCount(s.items.length);
      expect(await items.evaluateAll((els) => els.map((e) => e.getAttribute('data-variant')))).toEqual(s.items.map((x) => x.variant_id ?? ''));
      // a piece with a price shows it; a piece without one has no button (S4)
      for (const el of await items.all()) {
        const priced = (await el.locator('.price, [class*="price"]').count()) > 0 || /₪/.test(await el.innerText());
        if (!priced) await expect(el.locator('button')).toHaveCount(0);
      }
    }
    await audit(page, 'the wheel on set C');
    // back to B, the set as a set
    await page.keyboard.press('Home');
    await expect.poll(sel).toBe(1);
    // PRE1 / MED1: a piece out of stock says so and has no button; the set's button takes the pieces that are sold
    const items = dialog.locator('.set-item');
    const sold = await dialog.locator('.set-item .set-add').count();
    const out = await items.filter({ hasText: 'המלאי אינו זמין כעת' }).count();
    expect(sold + out).toBeLessThanOrEqual(house.sets[0]!.items.length);
    for (const el of await items.filter({ hasText: 'המלאי אינו זמין כעת' }).all()) await expect(el.locator('button')).toHaveCount(0);
    await expect(dialog.locator('#add-set')).toContainText(sold === house.sets[0]!.items.length ? 'הסט כולו לסל' : `${sold} הפריטים שבמלאי לסל`);
    const count = async () => Number(await page.locator('.cart-count').first().innerText());
    const before = await count();
    await dialog.locator('#add-set').click();
    await expect.poll(count, { timeout: 15_000 }).toBe(before + sold);
    await dialog.getByRole('button', { name: 'סגירה וחזרה לחדר בלי שינוי' }).click();
    await expect(dialog).toBeHidden();
  });

  /**
   * S12, QA ת22: the set's pieces, the fourth (the throw, the dearest) too, are all there to read at every width: the list
   * has no scroller hiding a piece, and every piece can be seen whole in the dialog (on a phone the dialog itself scrolls).
   */
  for (const v of [
    { width: 1280, height: 720, dpr: 1 },
    { width: 1440, height: 900, dpr: 1 },
    { width: 1920, height: 1080, dpr: 1 },
    { width: 400, height: 800, dpr: 1 },
    { width: 390, height: 844, dpr: 3 },
  ])
    test(`ת22: every piece of every set shows whole, the throw too (${v.width}×${v.height}@${v.dpr})`, async ({ browser }) => {
      const ctx = await browser.newContext({
        locale: 'he-IL',
        viewport: { width: v.width, height: v.height },
        deviceScaleFactor: v.dpr,
        isMobile: v.dpr > 1,
        hasTouch: v.dpr > 1,
      });
      const page = await ctx.newPage();
      await houseReady(page);
      await page.locator(`button.hotspot[data-slot="${SLOT.id}"]`).focus();
      await page.keyboard.press('Enter');
      const dialog = page.getByRole('dialog', { name: SLOT.name_he });
      await expect(dialog).toBeVisible({ timeout: 15_000 });
      for (const [i, set] of house.sets.entries()) {
        if (i > 0) await page.keyboard.press('ArrowLeft');
        await expect(dialog.getByRole('radio').nth(i)).toHaveAttribute('aria-checked', 'true');
        const items = dialog.locator('.set-item');
        await expect(items).toHaveCount(set.items.length);
        const list = dialog.locator('.set-items');
        const fit = await list.evaluate((el) => ({ scroll: el.scrollHeight, client: el.clientHeight }));
        expect(fit.scroll, `set ${set.id}: the list hides nothing behind a scroller`).toBeLessThanOrEqual(fit.client + 1);
        for (const [n, el] of (await items.all()).entries()) {
          await el.evaluate((e) => e.scrollIntoView({ block: 'nearest' }));
          const b = (await el.boundingBox())!;
          const d = (await dialog.boundingBox())!;
          const where = `set ${set.id}, piece ${n + 1}`;
          expect(b.y, where).toBeGreaterThanOrEqual(Math.max(0, d.y) - 1);
          expect(b.y + b.height, where).toBeLessThanOrEqual(Math.min(v.height, d.y + d.height) + 1);
        }
        if (SHOTS && i === 0 && v.dpr === 1 && (v.width === 1280 || v.width === 400)) {
          mkdirSync(SHOTS, { recursive: true });
          await page.screenshot({ path: join(SHOTS, `set-panel-B-${v.width}x${v.height}.png`) });
        }
        await dialog.evaluate((e) => (e.matches('.picker') ? e : e.querySelector('.picker'))?.scrollTo(0, 0));
      }
      await ctx.close();
    });

  test('a deep link opens the wheel on its set (the story’s "לנסות בחדר")', async ({ page }) => {
    await page.goto(`${HOUSE}&slot=${SLOT.id}&option=2`);
    const dialog = page.getByRole('dialog', { name: SLOT.name_he });
    await expect(dialog).toBeVisible({ timeout: 20_000 });
    await expect(dialog.getByRole('radio').nth(1)).toHaveAttribute('aria-checked', 'true');
  });

  test('swap: a set changes nothing outside the sets’ own area (alpha and shadow of the two sets)', async ({ page }) => {
    test.skip(!LAYERED, 'the separate layers (layers-v3c/) are not there yet: the house runs on the approved composites');
    await page.setViewportSize({ width: 1280, height: 720 });
    await houseReady(page);
    await engineReady(page);
    // the page's CSP allows no style element: the controls on the stage are hidden through their style attribute
    await page.evaluate(() => {
      document
        .querySelectorAll<HTMLElement>('.stage-ui, .hotspots, .stage-temp-note, .outlines, .stage-back')
        .forEach((el) => (el.style.visibility = 'hidden'));
    });
    await page.mouse.move(0, 0);
    const canvas = page.locator('canvas.room-canvas');
    const shot = async (pos: number) => {
      await page.evaluate(
        ([id, p]) => (window as unknown as { __hdEngine: { setSelection(s: string, n: number, d: number): Promise<void> } }).__hdEngine.setSelection(id, p, 0),
        [SLOT.id, pos] as [string, number],
      );
      await page.waitForTimeout(300);
      return sharp(await canvas.screenshot())
        .ensureAlpha()
        .raw()
        .toBuffer({ resolveWithObject: true });
    };
    const e = (await engineOf(page))!;
    const sc = house.scene.slots[SLOT.id]!;
    // the sets' area in the frame: every pixel a layer covers (alpha) or its shadow darkens, from the files the engine draws
    const area = async (n: number) => {
      const out: { rect: Box; w: number; h: number; on: Uint8Array }[] = [];
      for (const [set, shadow] of [
        [sc.product, false],
        [sc.shadow, true],
      ] as const) {
        if (!set) continue;
        const { data, info } = await sharp(resolve(SITE, 'web/public/media', `${set.src[n - 1]}.${house.scene.widths.lo}.webp`))
          .ensureAlpha()
          .raw()
          .toBuffer({ resolveWithObject: true });
        const on = new Uint8Array(info.width * info.height);
        for (let i = 0; i < on.length; i++)
          on[i] = shadow ? +(data[i * 4]! < 255 || data[i * 4 + 1]! < 255 || data[i * 4 + 2]! < 255) : +(data[i * 4 + 3]! > 0);
        out.push({ rect: set.rect, w: info.width, h: info.height, on });
      }
      return out;
    };
    const shots = [await shot(1), await shot(2), await shot(3)];
    const W = shots[0]!.info.width;
    const H = shots[0]!.info.height;
    const k = W / e.vp.w; // screenshot px per CSS px
    const fw = Math.max(e.vp.w, e.vp.h * house.scene.aspect) * e.cam.z;
    const fh = fw / house.scene.aspect;
    const areas = [await area(1), await area(2), await area(3)];
    // S12, QA ת26: the area grows by one pixel of the layer files it is read from (lo: 1920 across the frame), in screen
    // pixels; no wider (3 CSS px were 9 screen px at dpr 3, more than the codec's edge)
    const DIL = Math.max(1, Math.ceil((fw / house.scene.widths.lo) * k));
    const results: string[] = [];
    for (const [i, j] of [
      [0, 1],
      [1, 2],
      [0, 2],
    ] as const) {
      const mask = new Uint8Array(W * H);
      for (const lay of [...areas[i]!, ...areas[j]!]) {
        const [u0, u1, v0, v1] = lay.rect;
        for (let y = 0; y < lay.h; y++)
          for (let x = 0; x < lay.w; x++) {
            if (!lay.on[y * lay.w + x]) continue;
            const u = u0 + ((x + 0.5) / lay.w) * (u1 - u0);
            const v = v0 + ((y + 0.5) / lay.h) * (v1 - v0);
            const sx = Math.round((e.vp.w / 2 + (u - e.cam.cu) * fw) * k);
            const sy = Math.round((e.vp.h / 2 + (v - e.cam.cv) * fh) * k);
            for (let dy = -DIL; dy <= DIL; dy++)
              for (let dx = -DIL; dx <= DIL; dx++) {
                const X = sx + dx;
                const Y = sy + dy;
                if (X >= 0 && X < W && Y >= 0 && Y < H) mask[Y * W + X] = 1;
              }
          }
      }
      let worst = 0;
      let changed = 0;
      let inside = 0;
      let masked = 0;
      const p = shots[i]!.data;
      const q = shots[j]!.data;
      for (let n = 0; n < W * H; n++) {
        const d = Math.max(Math.abs(p[n * 4]! - q[n * 4]!), Math.abs(p[n * 4 + 1]! - q[n * 4 + 1]!), Math.abs(p[n * 4 + 2]! - q[n * 4 + 2]!));
        if (mask[n]) {
          masked++;
          if (d > 2) inside++;
          continue;
        }
        if (d > worst) worst = d;
        if (d > 2) changed++;
      }
      // the measure means something: the area is the sofa's part of the frame, and the sets do differ inside it
      expect(masked / (W * H)).toBeGreaterThan(0.01);
      expect(masked / (W * H)).toBeLessThan(0.3);
      expect(inside).toBeGreaterThan(1000);
      results.push(
        `${house.sets[i]!.id}↔${house.sets[j]!.id}: ${changed} px changed outside (worst ${worst} levels), ${inside} inside an area of ${((100 * masked) / (W * H)).toFixed(1)}%`,
      );
      expect(changed, results.join('; ')).toBe(0);
    }
    console.log(`swap-diff (warm modern, 1280×720): ${results.join('; ')}`);
  });
});

test.describe('the soft switch between houses, in the engine (S10)', () => {
  test('one frame for every layer, the same camera, 1.0 s; the address names the house; back again', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto('/rooms/living-room/');
    await expect(page.locator('button.hotspot').first()).toBeAttached({ timeout: 20_000 });
    const group = page.getByRole('group', { name: 'הבית' });
    await expect(group.getByRole('button')).toHaveCount(2);
    await expect(group.locator('button[data-house="nordic"]')).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('.stage-status')).toHaveCount(0);
    const canvasBox = await page.locator('canvas.room-canvas').boundingBox();
    // one box for all the layers: the house's layers are composed into the one canvas, over the poster at the same box
    expect(await page.locator('img.poster').boundingBox()).toEqual(canvasBox);
    await group.locator('button[data-house="warm-modern"]').click();
    await expect(page).toHaveURL(/\/rooms\/living-room\/\?style=warm-modern$/);
    const camBefore = (await engineOf(page))!.cam;
    await expect.poll(() => switchTimes(page), { timeout: 20_000 }).toMatchObject({ from: 'nordic', to: 'warm-modern' });
    const t = (await switchTimes(page))!;
    expect(t.end - t.start, 'the dissolve').toBeGreaterThanOrEqual(980);
    // S12, QA ת26: it ends on the first frame after 1.0 s; a loaded machine draws few, so the bound is the longest gap
    expect(t.end - t.start, 'the dissolve').toBeLessThan(1000 + (await frameGap(page)) + 50);
    expect((await engineOf(page))!.cam, 'the same camera').toEqual(camBefore);
    expect(await page.locator('canvas.room-canvas').boundingBox()).toEqual(canvasBox);
    expect(await page.locator('img.poster').boundingBox()).toEqual(canvasBox);
    await expect(page.locator('.stage-status')).toHaveText(LABEL);
    await expect(page.locator('button.hotspot')).toHaveCount(1);
    console.log(`house switch nordic → warm-modern: dissolve ${Math.round(t.end - t.start)} ms, press → end ${Math.round(t.end - t.asked)} ms`);
    // and back: the Nordic house with its own choices, the address without ?style
    await group.locator('button[data-house="nordic"]').click();
    await expect(page).toHaveURL(/\/rooms\/living-room\/$/);
    await expect.poll(async () => (await switchTimes(page))?.to, { timeout: 20_000 }).toBe('nordic');
    await expect(page.locator('.stage-status')).toHaveCount(0);
    expect((await page.locator('button.hotspot').count()) > 1).toBe(true);
  });

  /**
   * S12, QA ת15 (and ת26): what the display pass draws, read back from the canvas in the same task as the draw (so it
   * needs no preserveDrawingBuffer). Two readings:
   *  - **every frame of the dissolve** the engine draws while it runs: none darker than the darker house;
   *  - **the dissolve's own states** once it is over (both compositions are still held): at 0 the previous house exactly as
   *    it was shown before the press, at 1 the new one, and at the midpoint both, half each. A cut to black (QA S8–S10:
   *    the previous composition thrown away when the width changes, 1920 Nordic → 2720 warm-modern) fails both.
   * Deterministic: the midpoint does not depend on how many frames a loaded machine manages to draw.
   */
  for (const vp of [
    { width: 1280, height: 720 },
    { width: 400, height: 800 },
  ])
    test(`ת15: the dissolve draws both houses mixed, never black, both ways (${vp.width}×${vp.height})`, async ({ page }) => {
      await page.setViewportSize(vp);
      await page.goto('/rooms/living-room/');
      await expect(page.locator('button.hotspot').first()).toBeAttached({ timeout: 20_000 });
      await engineReady(page);
      expect(await page.evaluate(() => (window as unknown as { __hdEngine: { kind: string } }).__hdEngine.kind)).toBe('webgl2');
      await page.evaluate(installProbe);
      const group = page.getByRole('group', { name: 'הבית' });
      for (const [to, from] of [
        ['warm-modern', 'nordic'],
        ['nordic', 'warm-modern'],
      ] as const) {
        const before = await page.evaluate(() => window.__hdProbe!.grab(1));
        await page.evaluate(() => window.__hdProbe!.record(true));
        await group.locator(`button[data-house="${to}"]`).click();
        await expect.poll(async () => (await switchTimes(page))?.to, { timeout: 20_000 }).toBe(to);
        const frames = await page.evaluate(() => window.__hdProbe!.record(false));
        const [at0, mid, at1] = await page.evaluate(() => [window.__hdProbe!.grab(0), window.__hdProbe!.grab(0.5), window.__hdProbe!.grab(1)]);
        const mean = (g: number[]) => g.reduce((a, b) => a + b, 0) / g.length;
        const dist = (a: number[], b: number[]) => mean(a.map((x, i) => Math.abs(x - b[i]!)));
        const blend = at0.map((x, i) => (x + at1[i]!) / 2);
        const lumaFloor = Math.min(mean(at0), mean(at1));
        const report = `${from} → ${to}: before ${mean(before).toFixed(1)}, at 0 ${mean(at0).toFixed(1)}, mid ${mean(mid).toFixed(1)}, at 1 ${mean(at1).toFixed(1)}; |0 − before| ${dist(at0, before).toFixed(2)}, |mid − half each| ${dist(mid, blend).toFixed(2)}, |0 − 1| ${dist(at0, at1).toFixed(1)}; frames drawn in the dissolve ${frames.filter((f) => f.mix > 0 && f.mix < 1).length}, darkest ${Math.min(...frames.map((f) => f.mean)).toFixed(1)}`;
        console.log(`ת15 ${vp.width}: ${report}`);
        // the two houses differ (else nothing is measured), and the dissolve starts from the house that was on screen
        expect(dist(at0, at1), report).toBeGreaterThan(8);
        expect(dist(at0, before), report).toBeLessThan(1.5);
        expect(mean(at0), report).toBeGreaterThan(0.9 * mean(before));
        // the midpoint: half of each, so far from either end
        expect(dist(mid, blend), report).toBeLessThan(2.5);
        expect(dist(mid, at0), report).toBeGreaterThan(0.35 * dist(at0, at1));
        expect(dist(mid, at1), report).toBeGreaterThan(0.35 * dist(at0, at1));
        // and what was drawn while it ran: no frame darker than the darker house (a black frame is ~20)
        for (const f of frames) expect(f.mean, `${report}; frame at mix ${f.mix.toFixed(2)}`).toBeGreaterThan(0.9 * lumaFloor);
        // the evidence: the dissolve's midpoint as the canvas shows it (the engine draws nothing more at rest)
        if (SHOTS) {
          mkdirSync(SHOTS, { recursive: true });
          await page.evaluate(() => window.__hdProbe!.grab(0.5));
          await page.locator('canvas.room-canvas').screenshot({ path: join(SHOTS, `switch-midpoint-${vp.width}-to-${to}.png`) });
        }
        await page.evaluate(() => window.__hdProbe!.restore());
      }
    });

  test('reduced motion: a short dissolve, 0.3 s, nothing moves', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/rooms/living-room/');
    await expect(page.locator('button.hotspot').first()).toBeAttached({ timeout: 20_000 });
    const camBefore = await page
      .locator('.segmented button[data-house="warm-modern"]')
      .click()
      .then(() => engineOf(page));
    await expect.poll(() => switchTimes(page), { timeout: 20_000 }).toMatchObject({ to: 'warm-modern' });
    const t = (await switchTimes(page))!;
    expect(t.end - t.start).toBeGreaterThanOrEqual(280);
    // S12, QA ת26: the first frame after 0.3 s, however far apart a loaded machine draws its frames
    expect(t.end - t.start).toBeLessThan(300 + (await frameGap(page)) + 50);
    expect((await engineOf(page))!.cam).toEqual(camBefore!.cam);
    console.log(`house switch, reduced motion: dissolve ${Math.round(t.end - t.start)} ms`);
  });
});
