/**
 * S20, the evidence (qa/reports/2026-11-07-site-track/s20/screens), at 1280 and 400, with axe on each page: the pages that
 * offer contact (QA ת61) as this build has them: with the shop's contact details (a public build whose config names
 * them) or without (the flag build today): the footer, the cancellation page, the delivered order, "אין גישה". The
 * file names carry the build's state (`contact` / `no-contact`). The time of the order page to its line goes to
 * data/s20-timings-<state>.json.
 * Runs only as `HD_SHOTS_DIR=<dir> npx --no-install playwright test --project=evidence e2e/shots-s20.spec.ts`, against the
 * local build with its Worker (npm run preview).
 */
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { openCustomerOrder, placeOrder, supplierSays, waitStatus, type Placed } from './ops';

const DIR = process.env.HD_SHOTS_DIR ?? '';
test.skip(!DIR, 'evidence only: set HD_SHOTS_DIR');
test.describe.configure({ mode: 'serial', timeout: 180_000 });

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const built = JSON.parse(readFileSync(join(SITE, '.generated/copy.he.json'), 'utf8')) as { contact: { email: string } | null };
const STATE = built.contact ? 'contact' : 'no-contact';
const WIDTHS = [1280, 400] as const;
const timings: Record<string, number> = {};
async function shot(page: Page, name: string) {
  mkdirSync(join(DIR, 'screens'), { recursive: true });
  await page.screenshot({ path: join(DIR, 'screens', `${name}-${STATE}.png`), fullPage: true });
}
async function axe(page: Page) {
  const r = await new AxeBuilder({ page } as unknown as ConstructorParameters<typeof AxeBuilder>[0])
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  expect(r.violations.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
}

let delivered: Placed;
test('a delivered order', async ({ request }) => {
  delivered = await placeOrder(request, '10.20.9.1');
  await waitStatus(request, delivered, 'sent_to_supplier');
  await supplierSays(request, delivered, 'shipped');
  await supplierSays(request, delivered, 'delivered');
  await waitStatus(request, delivered, 'delivered');
});

for (const w of WIDTHS)
  test(`the pages that offer contact, ${w}`, async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, locale: 'he-IL' });
    const page = await ctx.newPage();
    await page.goto('/returns/');
    await expect(page.locator('[data-contact]')).toHaveCount(built.contact ? 2 : 0); // the page's block and the footer's
    await axe(page);
    await shot(page, `returns-${w}`);
    await page.goto('/accessibility/');
    await axe(page);
    await shot(page, `accessibility-${w}`);
    const t0 = Date.now();
    await openCustomerOrder(page, delivered);
    await expect(page.locator('.order-sheet > p.small.muted')).toContainText('ההזמנה נמסרה.');
    timings[`order_delivered_line_ms_${w}`] = Date.now() - t0;
    if (built.contact) await expect(page.locator('.order-sheet [data-contact] a[href^="mailto:"]')).toHaveText(built.contact.email);
    await axe(page);
    await shot(page, `order-delivered-${w}`);
    const other = await browser.newContext({ viewport: { width: w, height: 900 }, locale: 'he-IL' });
    const p2 = await other.newPage();
    await p2.goto(`/order/${delivered.id}/`);
    await expect(p2.getByRole('alert')).toBeVisible();
    await expect(p2.locator('.order-no-access-contact')).toHaveCount(built.contact ? 1 : 0);
    await axe(p2);
    await shot(p2, `order-no-access-${w}`);
    await other.close();
    await ctx.close();
  });

test('timings', () => {
  mkdirSync(join(DIR, 'data'), { recursive: true });
  writeFileSync(join(DIR, 'data', `s20-timings-${STATE}.json`), JSON.stringify(timings, null, 1) + '\n');
});
