/**
 * The evidence of S6 (the shop in the magazine language, art direction §9): screenshots at 400 and 1280 and the
 * opening timings, against the local production build with its API (the cart, the checkout and an order need it).
 * Runs only as `HD_SHOTS_DIR=<dir> npx --no-install playwright test --project=evidence`; never part of e2e, never a tracked file
 * unless the directory given is.
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test, type Page } from '@playwright/test';
import { productPath } from '@hd/shared/product-url';

const DIR = process.env.HD_SHOTS_DIR ?? '';
const timings: Record<string, unknown> = {};
const PRODUCT = productPath('vase-cj-textured-white-stoneware');

test.skip(!DIR, 'evidence only: set HD_SHOTS_DIR');

async function shot(page: Page, name: string, full = false): Promise<void> {
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(500);
  await page.screenshot({ path: join(DIR, 'screens', `${name}.png`), fullPage: full });
}
async function timed(page: Page, url: string, key: string): Promise<void> {
  await page.goto(url, { waitUntil: 'load' });
  await page.waitForTimeout(1200);
  timings[key] = await page.evaluate(() => {
    const nav = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined;
    const fcp = performance.getEntriesByName('first-contentful-paint')[0]?.startTime ?? null;
    const bytes = performance.getEntriesByType('resource').reduce((n, r) => n + ((r as PerformanceResourceTiming).transferSize || 0), nav?.transferSize ?? 0);
    return {
      fcp_ms: fcp && Math.round(fcp),
      dcl_ms: nav && Math.round(nav.domContentLoadedEventEnd),
      load_ms: nav && Math.round(nav.loadEventEnd),
      kb: Math.round(bytes / 102.4) / 10,
    };
  });
}

test.afterAll(() => {
  if (DIR) writeFileSync(join(DIR, 'timings.json'), JSON.stringify(timings, null, 1));
});

for (const [w, h, tag] of [
  [1280, 800, 'desk'],
  [400, 860, 'phone'],
] as const) {
  test(`the shop at ${w}`, async ({ page }) => {
    test.setTimeout(180_000);
    mkdirSync(join(DIR, 'screens'), { recursive: true });
    await page.setViewportSize({ width: w, height: h });
    await timed(page, '/', `home_${tag}`);
    await shot(page, `${tag}-1-home`);
    await timed(page, '/rooms/living-room/', `room_${tag}`);
    await expect(page.locator('button.hotspot').first()).toBeAttached({ timeout: 20_000 });
    await shot(page, `${tag}-2-room`);
    await page.locator('button.hotspot[data-slot="vase"]').click({ force: true });
    await expect(page.locator('.arc')).toBeVisible({ timeout: 20_000 });
    await page.waitForTimeout(1200);
    await shot(page, `${tag}-3-wheel`);
    await page.keyboard.press('Escape');
    await timed(page, PRODUCT, `product_${tag}`);
    await shot(page, `${tag}-4-product`);
    await shot(page, `${tag}-5-product-full`, true);
    await page.getByRole('button', { name: 'הוספה לסל' }).first().click();
    await expect(page.locator('.cart-count')).toHaveText('1');
    await shot(page, `${tag}-6-added`);
    if (tag === 'phone') {
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(600);
      await shot(page, `${tag}-6b-buy-bar`);
    }
    await page.goto('/cart/');
    await expect(page.locator('.cart-line')).toHaveCount(1);
    await shot(page, `${tag}-7-cart`);
    await page.getByRole('link', { name: 'להמשך לתשלום' }).click();
    await page.getByRole('button', { name: 'מעבר לתשלום מאובטח' }).click();
    await expect(page.locator('.error-summary')).toBeVisible();
    await shot(page, `${tag}-8-checkout-errors`, true);
    await page.getByLabel('שם מלא').fill('ישראלה ישראלי');
    await page.getByLabel('אימייל').fill('buyer@example.com');
    await page.getByLabel('טלפון').fill('050-1234567');
    await page.getByLabel('עיר').fill('תל אביב');
    await page.getByLabel('רחוב').fill('הרצל');
    await page.getByLabel('מספר בית').fill('10');
    await page.getByRole('checkbox', { name: /קראתי ואני מסכים/ }).check();
    await page.getByRole('button', { name: 'מעבר לתשלום מאובטח' }).click();
    await expect(page).toHaveURL(/\/mock-pay\/ms_/);
    await page.getByRole('button', { name: 'אישור תשלום (מדומה)' }).click();
    await expect(page.locator('.order-steps [aria-current="step"]')).toHaveText(/התקבלה|בהכנה/, { timeout: 20_000 });
    await shot(page, `${tag}-9-order`);
    await page.goto('/cart/');
    await expect(page.locator('.cart-empty')).toBeVisible();
    await shot(page, `${tag}-10-cart-empty`);
  });
}
