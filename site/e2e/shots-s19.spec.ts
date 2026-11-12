/**
 * S19, the evidence (qa/reports/2026-11-07-site-track/s19/screens), at 1280 and 400, with axe on each page: the cart and
 * the checkout as a customer reaches them by the site's links from the room (QA ת55), each a document of its own: the
 * timing of each move (the full load of the cart and the checkout, the in-site move to the product) goes to
 * data/s19-timings.json.
 * Runs only as `HD_SHOTS_DIR=<dir> npx --no-install playwright test --project=evidence e2e/shots-s19.spec.ts`, against the
 * local build with its Worker (npm run preview).
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

const DIR = process.env.HD_SHOTS_DIR ?? '';
test.skip(!DIR, 'evidence only: set HD_SHOTS_DIR');
test.describe.configure({ mode: 'serial', timeout: 180_000 });

const WIDTHS = [1280, 400] as const;
const timings: Record<string, Record<string, number>> = {};
async function shot(page: Page, name: string) {
  mkdirSync(join(DIR, 'screens'), { recursive: true });
  await page.screenshot({ path: join(DIR, 'screens', `${name}.png`), fullPage: true });
}
async function axe(page: Page) {
  const r = await new AxeBuilder({ page } as unknown as ConstructorParameters<typeof AxeBuilder>[0])
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  expect(r.violations.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
}
const navigation = (page: Page) =>
  page.evaluate(() => {
    const n = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined;
    return { name: n?.name ?? '', domContentLoaded: Math.round(n?.domContentLoadedEventEnd ?? 0), load: Math.round(n?.loadEventEnd ?? 0) };
  });

for (const w of WIDTHS)
  test(`room → product → cart → checkout by the site’s links, ${w}`, async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, locale: 'he-IL' });
    const page = await ctx.newPage();
    const t: Record<string, number> = {};
    await page.goto('/rooms/living-room/');
    let t0 = Date.now();
    await page
      .getByRole('link', { name: /^אגרטל/ })
      .first()
      .click();
    await expect(page.locator('#product-title')).toBeVisible();
    t['in-site move to the product (ms)'] = Date.now() - t0;
    await page.getByRole('button', { name: 'הוספה לסל' }).click();
    await expect(page.locator('.cart-count')).toHaveText('1');
    t0 = Date.now();
    await page.getByRole('link', { name: /^סל הקניות/ }).click();
    await expect(page.getByRole('heading', { name: 'סל הקניות' })).toBeVisible();
    await expect(page.locator('.cart-line').first()).toBeVisible();
    t['full load of the cart, click to its first line (ms)'] = Date.now() - t0;
    const cart = await navigation(page);
    expect(cart.name).toMatch(/\/cart\/$/);
    t['the cart document: DOMContentLoaded (ms)'] = cart.domContentLoaded;
    await axe(page);
    await shot(page, `cart-in-site-${w}`);
    t0 = Date.now();
    await page.getByRole('link', { name: 'להמשך לתשלום' }).click();
    await expect(page.getByLabel('שם מלא')).toBeVisible();
    t['full load of the checkout, click to its form (ms)'] = Date.now() - t0;
    const checkout = await navigation(page);
    expect(checkout.name).toMatch(/\/checkout\/$/);
    t['the checkout document: DOMContentLoaded (ms)'] = checkout.domContentLoaded;
    await axe(page);
    await shot(page, `checkout-in-site-${w}`);
    timings[String(w)] = t;
    mkdirSync(join(DIR, 'data'), { recursive: true });
    writeFileSync(join(DIR, 'data', 's19-timings.json'), JSON.stringify(timings, null, 1));
    await ctx.close();
  });
