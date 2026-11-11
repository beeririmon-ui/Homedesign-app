/**
 * S12, QA S8–S10:
 *  - ת21, "החדר שלך" (fidelity first): a beige cushion and the Pecan throw bought in the warm-modern house draw the
 *    warm-modern house with their set's layer, never the Nordic room; a Nordic product bought in the room's option draws
 *    the Nordic room; a variant no house renders is never drawn in another colour: its card picture and a line say it has
 *    no picture.
 *  - ת25: the empty checkout's way back is a 44 px target.
 * S15, master-designer's copy (docs/proposals/your-room-copy-2026-11-11.md §1): the caption describes the picture only
 * ("הדמיה: {the place}."); the list under it opens with "בהזמנה, ולא בהדמיה:", its name; a row's reason sits on its own
 * line; "עם מה שהזמנתם, בגוונים שבחרתם" only when the list is empty; the caption and the list at 26rem.
 * Screens for the evidence when HD_SHOTS_DIR is set.
 */
import { test, expect, type APIRequestContext, type Page } from '@playwright/test';
import { mkdirSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SHOTS = process.env.HD_SHOTS_DIR ?? null;
type Full = {
  products: { id: string; name_he: string; card_id?: string; variants_full?: { id: string; active: boolean; in_room: boolean; line_name_he?: string }[] }[];
};
type Pub = { rooms: { id: string; slots: { id: string; options: { position: number; product_id: string | null; is_default: boolean }[] }[] }[] };
const gen = <T>(f: string): T => JSON.parse(readFileSync(resolve(SITE, '.generated', f), 'utf8')) as T;
const house = gen<{
  place_he: string;
  sets: { id: string; label_he: string; items: { variant_id: string | null; name_he: string; option_he: string | null }[] }[];
}>('house.living-room.warm-modern.json');
const NORDIC_PLACE = 'הסלון בבית הנורדי';
const LEAD = 'בהזמנה, ולא בהדמיה:';
/** S15 (§0.6): the caption and the list are measured at 26rem; a caption is at most three lines */
async function measured(page: Page, figure: ReturnType<Page['locator']>) {
  const rem = await page.evaluate(() => parseFloat(getComputedStyle(document.documentElement).fontSize));
  for (const el of [figure.locator('figcaption'), page.locator('.your-room-list')]) {
    if (!(await el.count())) continue;
    expect((await el.boundingBox())!.width, 'at most 26rem').toBeLessThanOrEqual(26 * rem + 0.5);
  }
  const lines = await figure
    .locator('figcaption')
    .evaluate((el) => Math.round(el.getBoundingClientRect().height / parseFloat(getComputedStyle(el).lineHeight)));
  expect(lines, 'the caption: at most three lines').toBeLessThanOrEqual(3);
}
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
    expect(await wm.locator('span[data-slot="cushions"] img:not(.is-multiply):not(.is-screen)').getAttribute('src')).toContain(
      '/media/house/living-room/warm-modern/M0/slots/cushions/1.product.',
    );
    // S15: the caption says what the picture shows: the place, and set B drawn whole with how much of it was ordered
    const setB2 = house.sets[0]!;
    await expect(wm.locator('figcaption')).toHaveText(
      `הדמיה: ${house.place_he}. ${setB2.label_he} מוצג כולו; הזמנתם ממנו 2 פריטים מתוך ${setB2.items.length}.`,
    );
    // the Nordic room: only the vase, at its own option; no warm-modern piece in it
    const nd = page.locator('figure.your-room[data-house="nordic"]');
    await expect(nd).toBeVisible();
    await expect(nd.locator('span[data-slot]')).toHaveCount(1);
    await expect(nd.locator(`span[data-slot="${vase.slot}"]`)).toHaveAttribute('data-position', String(vase.position));
    // the list under the pictures is not empty: the caption says the place only, never "what you ordered"
    await expect(nd.locator('figcaption')).toHaveText(`הדמיה: ${NORDIC_PLACE}.`);
    // a colour no room renders: never drawn; its own picture (or none) and the reason, on its own line
    await expect(page.locator('#your-room-missing-title')).toHaveText(LEAD);
    await expect(page.locator('ul.your-room-missing')).toHaveAttribute('aria-labelledby', 'your-room-missing-title');
    const miss = page.locator(`.your-room-missing li[data-variant="${other}"]`);
    await expect(miss.locator('.your-room-why')).toHaveText('אין הדמיה לאפשרות הזו.');
    expect(await miss.locator('.your-room-why').evaluate((el) => getComputedStyle(el).display)).toBe('block');
    for (const img of await miss.locator('img').all()) expect(await img.getAttribute('src')).not.toMatch(/\/media\/(rooms|house)\//);
    await expect(page.locator('.your-room-missing li')).toHaveCount(1);
    await page.setViewportSize({ width: 1280, height: 900 });
    await shot(page, 'your-room-1280');
    await page.setViewportSize({ width: 400, height: 800 });
    await shot(page, 'your-room-400');
  });
});

/**
 * S14, QA ת28: one order with two options of the same slot. A picture draws one option per slot (the first in the order),
 * the other is listed under it with its own picture and the reason, never dropped; the caption says what is drawn: a set
 * drawn whole names the pieces ordered from it, and that another option of the place was ordered too.
 */
test.describe('ת28: two options of the same slot in one order: every line is accounted for', () => {
  async function orderOf(page: Page, request: APIRequestContext, ip: Record<string, string>, items: { variant_id: string; house: string }[]) {
    await page.setExtraHTTPHeaders(ip);
    const { id } = (await (await request.post('/api/cart', { headers: ip })).json()) as { id: string };
    for (const i of items) expect((await request.put(`/api/cart/${id}/items`, { headers: ip, data: { ...i, qty: 1 } })).status(), i.variant_id).toBe(200);
    await page.goto('/cart/');
    await page.evaluate((cart) => localStorage.setItem('hd.cart', cart), id);
    await pay(page);
  }
  /** each line of the order is either drawn (the figure's data-drawn) or listed, never both, never neither */
  async function accounted(page: Page, variants: string[]) {
    const drawn = (await page.locator('figure.your-room').evaluateAll((fs) => fs.flatMap((f) => (f.getAttribute('data-drawn') ?? '').split(' ')))).filter(
      Boolean,
    );
    const listed = await page.locator('.your-room-missing li').evaluateAll((ls) => ls.map((l) => l.getAttribute('data-variant')));
    for (const v of variants) expect(Number(drawn.includes(v)) + Number(listed.includes(v)), v).toBe(1);
    expect(drawn.length + listed.length).toBe(variants.length);
  }

  test('case 3: the Pecan throw (set B) and the white bouclé (set A), both in the warm-modern house', async ({ page, request }) => {
    test.setTimeout(150_000);
    const setA = house.sets.find((s) => s.id === 'A')!;
    const WHITE = setA.items.find((i) => /לבן חם/.test(i.option_he ?? ''))!.variant_id!;
    await orderOf(page, request, { 'cf-connecting-ip': '198.51.100.141' }, [
      { variant_id: PECAN, house: 'warm-modern' },
      { variant_id: WHITE, house: 'warm-modern' },
    ]);
    const wm = page.locator('figure.your-room[data-house="warm-modern"]');
    await expect(wm).toBeVisible({ timeout: 20_000 });
    // one option per slot: set B (the first line), drawn whole
    await expect(wm.locator('span[data-slot]')).toHaveCount(1);
    await expect(wm.locator('span[data-slot="cushions"]')).toHaveAttribute('data-position', '1');
    // S15, §1.2: the caption describes the picture only: the place, and the set drawn whole with the one piece ordered
    // from it by its base name (the option and size are in the order's line)
    const setB2 = house.sets[0]!;
    const pecan = setB2.items.find((i) => i.variant_id === PECAN)!;
    const cap = wm.locator('figcaption');
    await expect(cap).toHaveText(`הדמיה: ${house.place_he}. ${setB2.label_he} מוצג כולו; הזמנתם ממנו פריט אחד: ${pecan.name_he}.`);
    await expect(cap).not.toContainText('עם מה שהזמנתם');
    await expect(cap).not.toContainText('סט B');
    // the white bouclé: listed under the lead, with its card's picture (never a room layer) and what the picture shows in
    // its place, by the set's name, on its own line
    await expect(page.locator('#your-room-missing-title')).toHaveText(LEAD);
    const white = page.locator(`.your-room-missing li[data-variant="${WHITE}"]`);
    await expect(white).toHaveAttribute('data-why', 'slot-taken');
    await expect(white.locator('.your-room-why')).toHaveText(`בהדמיה, באותו מקום: ${setB2.label_he}.`);
    for (const img of await white.locator('img').all()) expect(await img.getAttribute('src')).not.toMatch(/\/media\/(rooms|house)\//);
    await accounted(page, [PECAN, WHITE]);
    for (const w of [1280, 400]) {
      await page.setViewportSize({ width: w, height: w === 400 ? 800 : 900 });
      await measured(page, wm);
      await shot(page, `your-room-case3-${w}`);
    }
  });

  test('case 4: two vases of the vase slot in the Nordic house', async ({ page, request }) => {
    test.setTimeout(150_000);
    const slot = gen<Pub>('catalog.public.json')
      .rooms.find((r) => r.id === 'living-room')!
      .slots.find((s) => s.id === 'vase')!;
    const full = gen<Full>('catalog.full.json');
    const vases = slot.options
      .filter((o) => o.product_id)
      .map((o) => {
        const p = full.products.find((x) => x.id === o.product_id)!;
        const v = p.variants_full?.find((x) => x.in_room);
        // the order's line is named by the variant's base name (api/src/lib/store.ts: line_name_he, else the product's)
        return { position: o.position, variant: v?.id ?? `${p.id}:default`, name: v?.line_name_he ?? p.name_he };
      });
    expect(vases.length).toBeGreaterThanOrEqual(2);
    const [first, second] = vases;
    await orderOf(page, request, { 'cf-connecting-ip': '198.51.100.142' }, [
      { variant_id: first!.variant, house: 'nordic' },
      { variant_id: second!.variant, house: 'nordic' },
    ]);
    const nd = page.locator('figure.your-room[data-house="nordic"]');
    await expect(nd).toBeVisible({ timeout: 20_000 });
    await expect(nd.locator('span[data-slot]')).toHaveCount(1);
    await expect(nd.locator('span[data-slot="vase"]')).toHaveAttribute('data-position', String(first!.position));
    // S15, §1.2: the caption is the place only; the second vase is listed, the first one's base name in its place
    await expect(nd.locator('figcaption')).toHaveText(`הדמיה: ${NORDIC_PLACE}.`);
    await expect(page.locator('#your-room-missing-title')).toHaveText(LEAD);
    const other = page.locator(`.your-room-missing li[data-variant="${second!.variant}"]`);
    await expect(other).toHaveAttribute('data-why', 'slot-taken');
    await expect(other.locator('.your-room-why')).toHaveText(`בהדמיה, באותו מקום: ${first!.name}.`);
    await accounted(page, [first!.variant, second!.variant]);
    for (const w of [1280, 400]) {
      await page.setViewportSize({ width: w, height: w === 400 ? 800 : 900 });
      await measured(page, nd);
      await shot(page, `your-room-case4-${w}`);
    }
  });

  test('all as ordered: the caption says so only when nothing is listed under the picture', async ({ page, request }) => {
    test.setTimeout(150_000);
    const vase = nordicVase();
    await orderOf(page, request, { 'cf-connecting-ip': '198.51.100.143' }, [{ variant_id: vase.variant, house: 'nordic' }]);
    const nd = page.locator('figure.your-room[data-house="nordic"]');
    await expect(nd).toBeVisible({ timeout: 20_000 });
    await expect(nd.locator('figcaption')).toHaveText(`הדמיה: ${NORDIC_PLACE}, עם מה שהזמנתם, בגוונים שבחרתם.`);
    await expect(page.locator('.your-room-list')).toHaveCount(0);
    await accounted(page, [vase.variant]);
    for (const w of [1280, 400]) {
      await page.setViewportSize({ width: w, height: w === 400 ? 800 : 900 });
      await measured(page, nd);
      await shot(page, `your-room-all-${w}`);
    }
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
    await shot(page, `empty-checkout-${w}`);
  }
});
