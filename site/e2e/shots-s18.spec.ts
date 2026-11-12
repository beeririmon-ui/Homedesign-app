/**
 * S18, the evidence (qa/reports/2026-11-07-site-track/s18/screens), at 1280 and 400, with axe on each page:
 * - the checkout: the address's line, no marketing box, the total "כולל מע"מ.";
 * - the order page after payment, and the same order in another browser;
 * - a product on hold: "המלאי אינו זמין כעת" alone, no form;
 * - the privacy policy's two lines.
 * Runs only as `HD_SHOTS_DIR=<dir> npx --no-install playwright test --project=evidence e2e/shots-s18.spec.ts`, against the
 * local build with its Worker (npm run preview).
 */
import { mkdirSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { shopPath } from '@hd/shared/product-url';
import { openCustomerOrder, placeOrder, type Placed } from './ops';

const DIR = process.env.HD_SHOTS_DIR ?? '';
const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
test.skip(!DIR, 'evidence only: set HD_SHOTS_DIR');
test.describe.configure({ mode: 'serial', timeout: 180_000 });

const catalog = JSON.parse(readFileSync(join(SITE, '.generated/catalog.public.json'), 'utf8')) as {
  products: { id: string; slot: string; price_agorot: number | null; variants: { id: string }[]; availability: { status: string } }[];
};
const WIDTHS = [1280, 400] as const;
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

let order: Placed;
test('setup: a paid order', async ({ request }) => {
  order = await placeOrder(request, '10.18.1.1');
});

for (const w of WIDTHS)
  test(`the pages without an email promise, ${w}`, async ({ browser, request }) => {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, locale: 'he-IL' });
    const page = await ctx.newPage();
    // the checkout, with a vase in the cart
    const h = { 'cf-connecting-ip': `10.18.1.${w === 400 ? 2 : 3}` };
    const p = catalog.products.find((x) => x.slot === 'vase' && x.price_agorot && x.availability.status === 'available')!;
    const cart = (await (await request.post('/api/cart', { headers: h })).json()) as { id: string };
    await request.put(`/api/cart/${cart.id}/items`, { headers: h, data: { variant_id: p.variants[0]!.id, qty: 1 } });
    await page.addInitScript((id) => localStorage.setItem('hd.cart', id), cart.id);
    await page.goto('/checkout/');
    await expect(page.locator('#h-email')).toBeVisible();
    await axe(page);
    await shot(page, `checkout-${w}`);
    // the order page, in the browser that ordered
    await openCustomerOrder(page, order);
    await expect
      .poll(() =>
        page.locator('figure.your-room img').evaluateAll((is) => is.every((i) => (i as HTMLImageElement).complete && (i as HTMLImageElement).naturalWidth > 0)),
      )
      .toBe(true);
    await axe(page);
    await shot(page, `order-${w}`);
    // the same order in another browser
    const other = await browser.newContext({ viewport: { width: w, height: 900 }, locale: 'he-IL' });
    const p2 = await other.newPage();
    await p2.goto(`/order/${order.id}/`);
    await expect(p2.getByRole('alert')).toBeVisible();
    await axe(p2);
    await shot(p2, `order-other-browser-${w}`);
    await other.close();
    // a product on hold
    const held = catalog.products.find((x) => x.availability.status !== 'available')!;
    await page.goto(shopPath(held.id));
    await expect(page.locator('.waitlist-status')).toBeVisible();
    await axe(page);
    await shot(page, `product-on-hold-${w}`);
    // the privacy policy
    await page.goto('/privacy/');
    await expect(page.locator('#legal-title')).toBeVisible();
    await axe(page);
    await shot(page, `privacy-${w}`);
    await ctx.close();
  });
