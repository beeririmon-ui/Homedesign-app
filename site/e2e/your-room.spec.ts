/**
 * S12, QA S8–S10:
 *  - ת21, "החדר שלך" (fidelity first): a beige cushion and the Pecan throw bought in the warm-modern house draw the
 *    warm-modern house with their set's layer, never the Nordic room; a Nordic product bought in the room's option draws
 *    the Nordic room; a variant no house renders is never drawn in another colour: its card picture and a line say it is
 *    not in the room yet.
 *  - ת25: the empty checkout's way back is a 44 px target.
 * Screens for the evidence when HD_SHOTS_DIR is set.
 */
import { test, expect, type Page } from '@playwright/test';
import { mkdirSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SHOTS = process.env.HD_SHOTS_DIR ?? null;
type Full = { products: { id: string; card_id?: string; variants_full?: { id: string; active: boolean; in_room: boolean }[] }[] };
type Pub = { rooms: { id: string; slots: { id: string; options: { position: number; product_id: string | null; is_default: boolean }[] }[] }[] };
const gen = <T>(f: string): T => JSON.parse(readFileSync(resolve(SITE, '.generated', f), 'utf8')) as T;
const house = gen<{ sets: { id: string; items: { variant_id: string | null; name_he: string; option_he: string | null }[] }[] }>(
  'house.living-room.warm-modern.json',
);
const setB = house.sets[0]!;
const BEIGE = setB.items.find((i) => /בז'/.test(i.option_he ?? ''))!.variant_id!;
const PECAN = setB.items.find((i) => /פקאן/.test(i.option_he ?? ''))!.variant_id!;

/** a sold variant of a card's option that no house renders (another colour than the room's) */
function notInRoom(card: string): string {
  for (const f of ['catalog.full.json', 'catalog.story.full.json']) {
    const v = gen<Full>(f)
      .products.find((x) => x.card_id === card)
      ?.variants_full?.find((x) => x.active && !x.in_room);
    if (v) return v.id;
  }
  throw new Error(`${card}: no sold option outside the room`);
}
/** the Nordic room's default vase, in the option the room shows */
function nordicVase(): { slot: string; position: number; variant: string } {
  const slot = gen<Pub>('catalog.public.json')
    .rooms.find((r) => r.id === 'living-room')!
    .slots.find((s) => s.id === 'vase')!;
  const o = slot.options.find((x) => x.is_default)!;
  const p = gen<Full>('catalog.full.json').products.find((x) => x.id === o.product_id)!;
  return { slot: slot.id, position: o.position, variant: p.variants_full?.find((v) => v.in_room)?.id ?? `${p.id}:default` };
}
async function shot(page: Page, name: string) {
  if (!SHOTS) return;
  mkdirSync(SHOTS, { recursive: true });
  await page.screenshot({ path: join(SHOTS, `${name}.png`), fullPage: true });
}
async function pay(page: Page) {
  await page.goto('/checkout/');
  await page.getByLabel('שם מלא').fill('נועה כהן');
  await page.getByLabel('אימייל').fill('noa@example.com');
  await page.getByLabel('טלפון').fill('050-1234567');
  await page.getByLabel('עיר').fill('חיפה');
  await page.getByLabel('רחוב').fill('הנמל');
  await page.getByLabel('מספר בית').fill('12');
  await page.getByRole('checkbox', { name: /קראתי ואני מסכים/ }).check();
  await page.getByRole('button', { name: 'מעבר לתשלום מאובטח' }).click();
  await expect(page).toHaveURL(/\/mock-pay\/ms_/);
  await page.getByRole('button', { name: 'אישור תשלום (מדומה)' }).click();
  await expect(page).toHaveURL(/\/order\/\d+\/$/);
}

test.describe('ת21: "החדר שלך" draws what was bought, where it was bought', () => {
  test('a beige cushion and the Pecan throw from the warm-modern house; the Nordic vase; a colour no room renders', async ({ page, request }) => {
    test.setTimeout(150_000);
    const ip = { 'cf-connecting-ip': '198.51.100.121' };
    await page.setExtraHTTPHeaders(ip);
    // in the warm-modern house: the wheel on set B (the default), the two pieces one by one from its panel
    await page.goto('/rooms/living-room/?style=warm-modern');
    await expect(page.locator('section.stage[data-house="warm-modern"]')).toBeVisible({ timeout: 20_000 });
    const spot = page.locator('button.hotspot[data-slot="cushions"]');
    await expect(spot).toBeAttached({ timeout: 20_000 });
    await spot.focus();
    await page.keyboard.press('Enter');
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible({ timeout: 15_000 });
    for (const v of [BEIGE, PECAN]) {
      const before = Number((await page.locator('.cart-count').first().textContent()) || 0);
      await dialog.locator(`.set-item[data-variant="${v}"] .set-add`).click();
      await expect.poll(async () => Number((await page.locator('.cart-count').first().textContent()) || 0)).toBe(before + 1);
    }
    // off the engine (the API, as a product page adds): the Nordic vase in the room's option, and a cushion in a colour
    // no house renders
    const cartId = await page.evaluate(() => localStorage.getItem('hd.cart'));
    const vase = nordicVase();
    const other = notInRoom('cushions-cj-washed-cotton-frayed');
    for (const variant_id of [vase.variant, other])
      expect((await request.put(`/api/cart/${cartId}/items`, { headers: ip, data: { variant_id, qty: 1 } })).status(), variant_id).toBe(200);
    await pay(page);

    const wm = page.locator('figure.your-room[data-house="warm-modern"]');
    await expect(wm).toBeVisible({ timeout: 20_000 });
    // the warm-modern house: its own picture, and set B's layer (the pieces as bought: beige, Pecan)
    await expect
      .poll(() =>
        wm
          .locator('picture img')
          .first()
          .evaluate((i: HTMLImageElement) => i.currentSrc),
      )
      .toContain('/media/house/living-room/warm-modern/');
    await expect(wm.locator('span[data-slot]')).toHaveCount(1);
    await expect(wm.locator('span[data-slot="cushions"]')).toHaveAttribute('data-position', '1');
    expect(await wm.locator('span[data-slot="cushions"] img').first().getAttribute('src')).toContain(
      '/media/house/living-room/warm-modern/M0/slots/cushions/1.product.',
    );
    await expect(wm.locator('figcaption')).toContainText('מודרני חם');
    // the Nordic room: only the vase, at its own option; no warm-modern piece in it
    const nd = page.locator('figure.your-room[data-house="nordic"]');
    await expect(nd).toBeVisible();
    await expect(nd.locator('span[data-slot]')).toHaveCount(1);
    await expect(nd.locator(`span[data-slot="${vase.slot}"]`)).toHaveAttribute('data-position', String(vase.position));
    // a colour no room renders: never drawn; its own picture (or none) and the line
    const miss = page.locator(`.your-room-missing li[data-variant="${other}"]`);
    await expect(miss).toContainText('עוד לא מופיע בהדמיה של החדר');
    for (const img of await miss.locator('img').all()) expect(await img.getAttribute('src')).not.toMatch(/\/media\/(rooms|house)\//);
    await expect(page.locator('.your-room-missing li')).toHaveCount(1);
    await page.setViewportSize({ width: 1280, height: 900 });
    await shot(page, 'your-room-1280');
    await page.setViewportSize({ width: 400, height: 800 });
    await shot(page, 'your-room-400');
  });
});

test('ת25: the empty checkout’s way back to the room is a 44 px target', async ({ page }) => {
  await page.goto('/checkout/');
  await expect(page.getByText('הסל ריק, אין מה לשלם.')).toBeVisible();
  for (const w of [400, 1280]) {
    await page.setViewportSize({ width: w, height: 800 });
    const box = (await page.getByRole('link', { name: 'חזרה לסלון' }).boundingBox())!;
    expect(box.height, `${w}`).toBeGreaterThanOrEqual(44);
    expect(box.width, `${w}`).toBeGreaterThanOrEqual(44);
  }
});
