/**
 * Zero axe violations (WCAG 2.0/2.1 A + AA, the basis of ת"י 5568) on every page type, in light and dark,
 * including the open variant wheel, a filled cart and the checkout with errors showing.
 */
import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'];

async function audit(page: Page, label: string) {
  // @axe-core/playwright pins its own playwright-core types; the runtime Page is the same object
  const r = await new AxeBuilder({ page } as unknown as ConstructorParameters<typeof AxeBuilder>[0]).withTags(TAGS).analyze();
  const summary = r.violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.length} × ${v.nodes[0]?.target.join(' ')} — ${v.help}`);
  expect(summary, `${label}\n${summary.join('\n')}`).toEqual([]);
}

async function addVase(page: Page) {
  await page.goto('/rooms/living-room/');
  await page
    .getByRole('link', { name: /^אגרטל/ })
    .first()
    .click();
  await page.getByRole('button', { name: 'הוספה לסל' }).click();
  await expect(page.locator('.cart-count')).toHaveText(/[1-9]/);
}

for (const scheme of ['light', 'dark'] as const) {
  test.describe(scheme, () => {
    test.use({ colorScheme: scheme });

    for (const path of ['/', '/accessibility/', '/terms/', '/returns/', '/privacy/', '/cart/', '/no-such-page/']) {
      test(`page ${path}`, async ({ page }) => {
        await page.goto(path);
        await page.locator('h1').first().waitFor();
        await audit(page, `${scheme} ${path}`);
      });
    }

    test('room, then the open variant wheel', async ({ page }) => {
      await page.goto('/rooms/living-room/');
      await expect(page.locator('button.hotspot:visible').first()).toBeVisible({ timeout: 20_000 });
      await audit(page, `${scheme} room`);
      await page.locator('button.hotspot[data-slot="vase"]').click();
      await expect(page.getByRole('dialog')).toBeVisible();
      await page.waitForTimeout(400);
      await audit(page, `${scheme} wheel`);
    });

    test('a set product (set or single piece), and its wheel', async ({ page }) => {
      await page.goto('/p/candle-holders-cj-travertine-pedestal/');
      await expect(page.getByRole('radiogroup', { name: 'איך לקנות' })).toBeVisible();
      await page.getByRole('radio', { name: /^יחידה אחת/ }).check();
      await audit(page, `${scheme} set product`);
      await page.goto('/rooms/living-room/');
      await expect(page.locator('button.hotspot:visible').first()).toBeVisible({ timeout: 20_000 });
      await page.locator('button.hotspot[data-slot="candle-holders"]').click();
      await expect(page.getByRole('dialog').getByRole('radiogroup', { name: 'איך לקנות' })).toBeVisible();
      await page.waitForTimeout(400);
      await audit(page, `${scheme} wheel with set or single piece`);
    });

    test('product, filled cart, checkout with errors', async ({ page }) => {
      await addVase(page);
      await audit(page, `${scheme} product`);
      // the gallery (FR-I) on its second picture, the supplier photo
      await page.getByRole('region', { name: 'תמונות המוצר' }).getByRole('button', { name: 'התמונה הבאה' }).click();
      await expect(page.locator('.gallery-slide').nth(1)).toBeInViewport({ ratio: 0.9 });
      await audit(page, `${scheme} product gallery, supplier photo`);
      await page.goto('/cart/');
      await expect(page.locator('.cart-line').first()).toBeVisible();
      await audit(page, `${scheme} cart`);
      await page.goto('/checkout/');
      await page.getByRole('button', { name: 'מעבר לתשלום מאובטח' }).click();
      await expect(page.locator('.error-summary')).toBeVisible();
      await audit(page, `${scheme} checkout errors`);
    });
  });
}
