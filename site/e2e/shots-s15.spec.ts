/**
 * The evidence of S15 (master-designer's copy, SEO per house, public honesty): the wheel and the set panel of the
 * warm-modern house ("3 סטים", the set names), the Nordic wheel ("3 גרסאות", "כריות ושמיכה"), the list under the room
 * of each house, and a product page (behind the flag: the render and the supplier's photo; in a public build: the
 * render alone). At 400 and 1280, against the local production build with its API.
 * Runs only as `HD_SHOTS_DIR=<dir> [HD_SHOTS_TAG=public] npx --no-install playwright test --project=evidence e2e/shots-s15.spec.ts`.
 */
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type Page } from '@playwright/test';

const DIR = process.env.HD_SHOTS_DIR ?? '';
const TAG = process.env.HD_SHOTS_TAG ?? 'flag';
const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const HOUSE = '/rooms/living-room/?style=warm-modern';
const evidence: Record<string, unknown> = {};

test.skip(!DIR, 'evidence only: set HD_SHOTS_DIR');
test.beforeAll(() => mkdirSync(join(DIR, 'screens'), { recursive: true }));
test.afterAll(() => {
  if (DIR) writeFileSync(join(DIR, `shots-${TAG}.json`), JSON.stringify(evidence, null, 1));
});

async function shot(page: Page, name: string, full = false): Promise<void> {
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(500);
  await page.screenshot({ path: join(DIR, 'screens', `${name}.png`), fullPage: full });
}
const SIZES = [
  [400, 800],
  [1280, 800],
] as const;

/** product pages: what the gallery shows (FR-I behind the flag; the render alone in a public build), and a product the
 *  room has no render of (the neutral tile in a public build) */
const products = (() => {
  const pub = JSON.parse(readFileSync(resolve(SITE, '.generated/catalog.public.json'), 'utf8')) as { products: { id: string }[] };
  return [pub.products.find((p) => p.id.startsWith('vase-'))!.id, pub.products.find((p) => p.id.startsWith('magazine-holder-arch-iron-cane'))!.id];
})();

for (const [w, h] of SIZES)
  for (const [k, product] of products.entries()) {
    test(`product page ${k + 1} at ${w} (${TAG})`, async ({ page }) => {
      await page.setViewportSize({ width: w, height: h });
      await page.goto(`/p/${product}/`);
      await expect(page.locator('#product-title')).toBeVisible();
      const kinds = await page.locator('.gallery-slide').evaluateAll((s) => s.map((x) => x.getAttribute('data-kind')));
      const srcs = await page.locator('.product-media img').evaluateAll((s) => s.map((x) => (x as HTMLImageElement).getAttribute('src')));
      evidence[`product_${k + 1}_${w}`] = { product, slides: kinds, images: [...new Set(srcs)], tile: await page.locator('.product-noimg').count() };
      await shot(page, `${TAG}-product-${k + 1}-${w}`, true);
    });
  }

if (TAG !== 'public') {
  for (const [w, h] of SIZES) {
    test(`the warm-modern set panel and the Nordic wheel at ${w}`, async ({ page }) => {
      await page.setViewportSize({ width: w, height: h });
      await page.goto(HOUSE);
      const spot = page.locator('button.hotspot[data-slot="cushions"]');
      await expect(spot).toBeAttached({ timeout: 20_000 });
      await spot.click({ force: true });
      const dialog = page.getByRole('dialog');
      await expect(dialog).toBeVisible({ timeout: 15_000 });
      await page.waitForTimeout(600);
      evidence[`set_panel_${w}`] = {
        eyebrow: await dialog.locator('.picker-head .eyebrow').innerText(),
        heading: await dialog.locator('.picker-head h2').innerText(),
        radios: await dialog.getByRole('radio').evaluateAll((r) => r.map((x) => x.getAttribute('aria-label'))),
        button: await dialog.locator('#add-set').innerText(),
      };
      await shot(page, `set-panel-${w}`);
      await page.keyboard.press('Escape');
      await expect(dialog).toBeHidden();
      await page.locator('.room-intro').scrollIntoViewIfNeeded();
      await shot(page, `warm-modern-list-${w}`);

      await page.goto('/rooms/living-room/');
      const cushions = page.locator('button.hotspot[data-slot="cushions"]');
      await expect(cushions).toBeAttached({ timeout: 20_000 });
      await cushions.click({ force: true });
      const nd = page.getByRole('dialog');
      await expect(nd).toBeVisible({ timeout: 15_000 });
      await page.waitForTimeout(600);
      evidence[`nordic_wheel_${w}`] = {
        eyebrow: await nd.locator('.picker-head .eyebrow').innerText(),
        heading: await nd.locator('.picker-head h2').innerText(),
      };
      await shot(page, `nordic-wheel-${w}`);
    });
  }
}

/**
 * The order page with a line whose option the room does not render: behind the flag its card's picture (the supplier's
 * photo of that option); in a public build that picture is withheld (its rights), and the neutral tile stands in its place.
 */
test(`"החדר שלך" with an option no room renders (${TAG})`, async ({ page, request }) => {
  test.setTimeout(150_000);
  type Full = { products: { id: string; card_id?: string; variants_full?: { id: string; active: boolean; in_room: boolean }[] }[] };
  const full = JSON.parse(readFileSync(resolve(SITE, '.generated/catalog.full.json'), 'utf8')) as Full;
  const other = full.products.find((p) => p.card_id === 'vase-cj-textured-white-stoneware')!.variants_full!.find((v) => v.active && !v.in_room)!.id;
  const ip = { 'cf-connecting-ip': TAG === 'public' ? '198.51.100.161' : '198.51.100.162' };
  await page.setExtraHTTPHeaders(ip);
  const { id } = (await (await request.post('/api/cart', { headers: ip })).json()) as { id: string };
  expect((await request.put(`/api/cart/${id}/items`, { headers: ip, data: { variant_id: other, qty: 1 } })).status()).toBe(200);
  await page.goto('/cart/');
  await page.evaluate((cart) => localStorage.setItem('hd.cart', cart), id);
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
  const row = page.locator(`.your-room-missing li[data-variant="${other}"]`);
  await expect(row).toBeVisible({ timeout: 20_000 });
  evidence[`order_row`] = {
    lead: await page.locator('#your-room-missing-title').innerText(),
    why: (await row.locator('.your-room-why').count()) ? await row.locator('.your-room-why').innerText() : null,
    img: (await row.locator('img').count()) ? await row.locator('img').getAttribute('src') : null,
    tile: await row.locator('.your-room-noimg').count(),
  };
  for (const [w, h] of SIZES) {
    await page.setViewportSize({ width: w, height: h });
    await shot(page, `${TAG}-order-noimg-${w}`, true);
  }
});
