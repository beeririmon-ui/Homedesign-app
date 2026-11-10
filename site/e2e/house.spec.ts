/**
 * S10: the warm-modern house in the room engine (DIR2), behind the flag. Its phase 1 as approved (AP3-WM): the v3c base
 * and the cushions slot, three sets on the wheel, B the default (CAM1); the status label; the soft switch between the
 * houses in the engine (1.0 s, 0.3 s with reduced motion), every layer in the one composed frame; and the swap of a set,
 * which may change nothing outside the sets' own area (studio rules ו.5), measured on what the browser shows.
 */
import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import sharp from 'sharp';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
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
const switchTimes = (page: Page) => page.evaluate(() => (window as unknown as { __hdHouseSwitch?: SwitchTimes }).__hdHouseSwitch ?? null);
const engineOf = (page: Page) =>
  page.evaluate(() => {
    const e = (window as unknown as { __hdEngine?: Engine }).__hdEngine;
    return e ? { ready: e.ready, cam: { ...e.cam }, vp: { ...e.vp } } : null;
  });

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
    const DIL = Math.ceil(3 * k);
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
    expect(t.end - t.start, 'the dissolve').toBeLessThan(1150);
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
    expect(t.end - t.start).toBeLessThan(450);
    expect((await engineOf(page))!.cam).toEqual(camBefore!.cam);
    console.log(`house switch, reduced motion: dissolve ${Math.round(t.end - t.start)} ms`);
  });
});
