/**
 * S16 evidence (qa/reports/2026-11-07-site-track/s16/screens/), at 400 and 1280:
 * - the admin's "בדיקה אצל הספק" on an order whose submit may have reached the supplier (ת35);
 * - the customer's page of an order in supplier_error: "מתעכבת" and its line (ה7, ת39);
 * - the stage while the poster is on its way: the inlined placeholder (ה1);
 * - the order page with the server's message and code (ת37).
 * Runs only as `HD_SHOTS_DIR=<dir> npx playwright test --project=evidence e2e/shots-s16.spec.ts`, against the local
 * preview (it marks one order's shipment as failed in the preview's own D1, through wrangler).
 */
import { execFileSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type Page } from '@playwright/test';
import { adminHeaders, openCustomerOrder, placeOrder, waitStatus, type Placed } from './ops';

const DIR = process.env.HD_SHOTS_DIR ?? '';
const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
test.skip(!DIR, 'evidence only: set HD_SHOTS_DIR');
test.describe.configure({ mode: 'serial', timeout: 180_000 });

const WIDTHS = [1280, 400] as const;
async function shot(page: Page, name: string, full = true) {
  mkdirSync(join(DIR, 'screens'), { recursive: true });
  await page.screenshot({ path: join(DIR, 'screens', `${name}.png`), fullPage: full });
}
/** the preview's own D1 (api: wrangler dev --persist-to ../.wrangler-state) */
function d1(sql: string) {
  execFileSync('npx', ['wrangler', 'd1', 'execute', 'DB', '--local', '--persist-to', '../.wrangler-state', '--command', sql], {
    cwd: join(SITE, 'api'),
    stdio: 'pipe',
  });
}

let maybe: Placed;
let stuck: Placed;
test('setup: an order whose submit timed out (maybe at the supplier), and one in supplier_error', async ({ request }) => {
  maybe = await placeOrder(request, '10.16.0.1');
  stuck = await placeOrder(request, '10.16.0.2');
  for (const o of [maybe, stuck]) await waitStatus(request, o, 'sent_to_supplier');
  const ago = new Date(Date.now() - 40 * 60_000).toISOString();
  const fail = (o: Placed, reach: string, order: string) =>
    d1(
      `UPDATE supplier_shipments SET status = 'failed', supplier_order_id = NULL, reach = '${reach}', attempts = 5, failing_since = '${ago}', last_error = 'mock submitOrder: no answer within 60 s (aborted; it may still have been done at the provider)' WHERE order_id = '${o.id}'; UPDATE orders SET status = '${order}' WHERE id = '${o.id}';`,
    );
  fail(maybe, 'maybe', 'paid');
  fail(stuck, 'none', 'supplier_error');
  const h = await request.get('/healthz');
  expect(h.status()).toBe(503);
  expect(await h.json()).toEqual({ ok: false, checks: { db: 'ok', queue: 'ok', supplier: 'degraded' } });
});

for (const w of WIDTHS)
  test(`the admin's supplier check, ${w}`, async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, extraHTTPHeaders: adminHeaders(), locale: 'he-IL' });
    const page = await ctx.newPage();
    await page.goto(`/admin/orders/${maybe.id}`);
    await expect(page.getByRole('heading', { name: /בדיקה אצל הספק/ })).toBeVisible();
    await shot(page, `admin-supplier-check-${w}`);
    await ctx.close();
  });

for (const w of WIDTHS)
  test(`the customer's page of an order in supplier_error, ${w}`, async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, locale: 'he-IL' });
    const page = await ctx.newPage();
    await openCustomerOrder(page, stuck);
    await expect(page.locator('.order-delay')).toBeVisible();
    await expect(page.locator('.order-steps')).toHaveAttribute('aria-label', 'מצב ההזמנה: מתעכבת');
    await shot(page, `order-delayed-${w}`);
    await ctx.close();
  });

test('clean-up: the two orders are canceled through the admin (a person checked: none at the supplier)', async ({ request }) => {
  for (const o of [maybe, stuck]) {
    const c = await request.post(`/api/admin/orders/${o.id}/supplier-check`, { headers: adminHeaders(), data: { outcome: 'none', note: 'צילומי S16' } });
    expect(c.status(), await c.text()).toBe(200);
    expect((await request.post(`/api/admin/orders/${o.id}/cancel`, { headers: adminHeaders(), data: { reason: 'צילומי S16' } })).status()).toBe(200);
  }
  expect((await request.get('/healthz')).status()).toBe(200);
});

for (const w of WIDTHS)
  test(`the stage while the poster is on its way, ${w}`, async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: { width: w, height: w === 400 ? 860 : 800 }, deviceScaleFactor: w === 400 ? 3 : 1, locale: 'he-IL' });
    const page = await ctx.newPage();
    let release!: () => void;
    const held = new Promise<void>((r) => (release = r));
    await page.route(/\/poster\/default\.\d+\.(avif|webp)$/, async (route) => {
      await held;
      await route.continue().catch(() => undefined);
    });
    await page.goto('/rooms/living-room/?style=warm-modern', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(400);
    await shot(page, `stage-placeholder-${w}`, false);
    release();
    await expect
      .poll(() => page.locator('.stage img.poster').evaluate((i) => (i as HTMLImageElement).complete && (i as HTMLImageElement).naturalWidth > 0))
      .toBe(true);
    await page.waitForTimeout(300);
    await shot(page, `stage-poster-${w}`, false);
    await ctx.close();
  });

test('the order page with the server’s message and code, 400', async ({ browser }) => {
  const ctx = await browser.newContext({ viewport: { width: 400, height: 860 }, locale: 'he-IL' });
  const page = await ctx.newPage();
  const id = '1234567890';
  await page.addInitScript(([orderId]) => localStorage.setItem(`hd.order.${orderId}`, 'tok-s16-0123456789abcdef'), [id]);
  await page.route(`**/api/orders/${id}`, (r) =>
    r.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({
        error: 'internal_error',
        error_id: 'E-7K2M9QX4',
        message_he: 'משהו השתבש אצלנו. נסו שוב בעוד רגע. אם זה חוזר, כתבו לנו וציינו את הקוד E-7K2M9QX4.',
      }),
    }),
  );
  await page.goto(`/order/${id}/`);
  await expect(page.locator('main [role="alert"]')).toContainText('E-7K2M9QX4');
  await shot(page, 'order-error-code-400');
  await ctx.close();
});
