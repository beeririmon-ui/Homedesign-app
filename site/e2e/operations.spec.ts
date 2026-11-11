/**
 * S13, operations, on the local preview (wrangler dev, mock payment and mock supplier, the queue consumer running):
 *  - /healthz says ok, and nothing else;
 *  - the admin is closed without permission (403), the screen and the API alike;
 *  - delivery statuses for the customer: an order paid, sent to the supplier, shipped with a tracking number and a generic
 *    link, delivered, as the order page shows them at 400 px;
 *  - the admin screen at 1280: the list with search, an order with its three tracks, a partial refund from the form (the
 *    customer sees it), and a cancellation after the supplier: requested, then confirmed (canceled and refunded).
 * Screens for the evidence when HD_SHOTS_DIR is set.
 */
import { test, expect, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { adminHeaders, openCustomerOrder, placeOrder, supplierSays, waitStatus } from './ops';

const SHOTS = process.env.HD_SHOTS_DIR ?? null;
async function shot(page: Page, name: string) {
  if (!SHOTS) return;
  mkdirSync(SHOTS, { recursive: true });
  await page.screenshot({ path: join(SHOTS, `${name}.png`), fullPage: true });
}

test('/healthz: D1 and the queue are ok, and the answer carries no internal detail', async ({ request }) => {
  const r = await request.get('/healthz');
  expect(r.status()).toBe(200);
  expect(r.headers()['cache-control']).toBe('no-store');
  expect(await r.json()).toEqual({ ok: true, checks: { db: 'ok', queue: 'ok', supplier: 'ok' } });
});

test('the admin without permission: 403 for the screen and the API, reads and actions', async ({ request }) => {
  for (const path of ['/admin/', '/admin', '/admin/orders/1234567890', '/api/admin/orders', '/api/admin/overview']) {
    const r = await request.get(path);
    expect(r.status(), path).toBe(403);
  }
  expect((await request.get('/api/admin/orders', { headers: { 'x-hd-dev-admin': 'not-the-token-not-the-token-x' } })).status()).toBe(403);
  expect((await request.get('/api/admin/orders', { headers: { 'cf-access-jwt-assertion': 'a.b.c' } })).status()).toBe(403);
  const post = await request.post('/api/admin/orders/1234567890/refund', { data: { amount_agorot: 100, reason: 'x y', key: 'rf_e2e_forbidden' } });
  expect(post.status()).toBe(403);
  expect(await (await request.get('/admin/')).text()).toContain('אין גישה');
});

test('delivery statuses for the customer: בהכנה, then נשלחה with its number and a generic link, then נמסרה', async ({ page, request }) => {
  test.setTimeout(90_000);
  const o = await placeOrder(request, '198.51.100.131');
  await waitStatus(request, o, 'sent_to_supplier');
  await page.setViewportSize({ width: 400, height: 860 });
  await openCustomerOrder(page, o);
  const steps = page.locator('.order-steps');
  await expect(steps.locator('[aria-current="step"]')).toHaveText('בהכנה');
  await expect(page.locator('.order-tracking')).toHaveCount(0);

  await supplierSays(request, o, 'accepted');
  await supplierSays(request, o, 'shipped');
  await page.reload();
  await expect(steps.locator('[aria-current="step"]')).toHaveText('נשלחה');
  const line = page.locator('.order-tracking li');
  await expect(line).toHaveCount(1);
  await expect(line).toContainText('מספר משלוח:');
  await expect(line.locator('.num')).toHaveText(/^IL\d{8}TRK$/);
  const link = line.getByRole('link', { name: /מעקב אחרי המשלוח/ });
  await expect(link).toHaveAttribute('href', /^https:\/\/parcelsapp\.com\//);
  await expect(link).toHaveAttribute('rel', /noopener/);
  await expect(page.getByText('ההזמנה בדרך אליכם.')).toBeVisible();
  // nothing on the customer's page names the supplier
  expect(await page.locator('main').innerText()).not.toMatch(/mock|\bcj\b|cjdropshipping|aliexpress|zendrop/i);
  await shot(page, 'order-shipped-400');

  await supplierSays(request, o, 'delivered');
  await page.reload();
  await expect(steps.locator('[aria-current="step"]')).toHaveText('נמסרה');
  await expect(line).toContainText('נמסרה');
  await shot(page, 'order-delivered-400');
});

test('the admin screen: the list and search, an order with its tracks, a partial refund from the form', async ({ page, request }) => {
  test.setTimeout(90_000);
  const o = await placeOrder(request, '198.51.100.132');
  await waitStatus(request, o, 'sent_to_supplier');
  await page.setExtraHTTPHeaders(adminHeaders());
  await page.setViewportSize({ width: 1280, height: 900 });

  await page.goto('/admin/');
  await expect(page.getByRole('heading', { level: 1, name: 'הזמנות' })).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  await expect(page.getByRole('link', { name: o.id })).toBeVisible();
  await page.getByLabel('מספר הזמנה').fill(o.id.slice(0, 6));
  await page.getByRole('button', { name: 'סינון' }).click();
  await expect(page).toHaveURL(new RegExp(`q=${o.id.slice(0, 6)}`));
  await expect(page.getByRole('link', { name: o.id })).toBeVisible();
  await shot(page, 'admin-list-search-1280');

  await page.getByRole('link', { name: o.id }).click();
  await expect(page.getByRole('heading', { level: 1 })).toContainText(o.id);
  for (const t of ['תשלום', 'חשבונית', 'ספק ומשלוח']) await expect(page.getByRole('region', { name: t })).toBeVisible();
  await expect(page.getByRole('region', { name: 'ספק ומשלוח' })).toContainText('נשלחה לספק');
  await expect(page.getByRole('region', { name: 'חשבונית' })).toContainText('הופקה', { timeout: 15_000 });

  const refund = page.locator('form[action$="/refund"]');
  const key = await refund.locator('input[name="key"]').inputValue();
  await refund.getByLabel(/סכום בשקלים/).fill('25');
  await refund.getByLabel(/סיבה/).fill('שריטה קטנה, פיצוי');
  await refund.getByRole('button', { name: 'ביצוע החזר' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'ההחזר בוצע' })).toBeVisible();
  await expect(page.locator('table').filter({ hasText: 'חלקי' })).toContainText('dev-token');
  // the same form sent again (back and resend): the same key, so the same refund, never a second one
  const again = await request.post(`/admin/orders/${o.id}/refund`, {
    headers: { ...adminHeaders(), origin: new URL(page.url()).origin },
    form: { amount: '25', reason: 'שריטה קטנה, פיצוי', key },
    maxRedirects: 0,
  });
  expect(again.status()).toBe(303);
  expect(again.headers()['location']).toContain('done=refund_duplicate');
  await shot(page, 'admin-order-refunded-1280');
  const view = (await (await request.get(`/api/orders/${o.id}`, { headers: { 'x-order-token': o.token } })).json()) as { refunded_agorot: number };
  expect(view.refunded_agorot).toBe(2500);
});

test('the cancellation after the supplier: requested (a clear status), then confirmed: canceled and refunded in full', async ({ page, request }) => {
  test.setTimeout(90_000);
  const o = await placeOrder(request, '198.51.100.133');
  await waitStatus(request, o, 'sent_to_supplier');
  await page.setExtraHTTPHeaders(adminHeaders());
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/admin/orders/${o.id}`);
  const cancel = page.locator('form[action$="/cancel"]');
  await expect(cancel).toContainText('אחרי שליחה לספק');
  await cancel.getByLabel(/סיבה/).fill('הלקוחה התחרטה');
  await cancel.getByRole('button', { name: 'שליחת בקשת ביטול לספק' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'בקשת הביטול נשלחה לספק' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'ספק ומשלוח' })).toContainText('בקשת ביטול נשלחה לספק, ממתינה לתשובה');
  // the request is not sent again while it waits on the supplier
  await expect(cancel.getByRole('button')).toHaveCount(0);
  await expect(cancel).toContainText('הבקשה אצל הספק');
  await shot(page, 'admin-cancel-requested-1280');

  await page.getByRole('button', { name: 'הספק אישר את הביטול' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toContainText('בוטלה');
  await expect(page.getByRole('region', { name: 'תשלום' })).toContainText('הוחזר במלואו');
  await shot(page, 'admin-canceled-1280');

  const customer = await page
    .context()
    .browser()!
    .newPage({ viewport: { width: 400, height: 860 } });
  await openCustomerOrder(customer, o);
  await expect(customer.getByRole('heading', { level: 1 })).toHaveText('ההזמנה בוטלה.');
  await expect(customer.locator('.order-refund')).toContainText('הוחזרו לאמצעי התשלום');
  await shot(customer, 'order-canceled-400');
  await customer.close();

  // the list after the three orders of this file: delivered, partly refunded, canceled; and the "needs a person" filter
  await page.goto('/admin/');
  await expect(page.getByRole('link', { name: o.id })).toBeVisible();
  await shot(page, 'admin-list-1280');
  await page.getByLabel('מצב').selectOption('canceled');
  await page.getByRole('button', { name: 'סינון' }).click();
  await expect(page.getByRole('link', { name: o.id })).toBeVisible();
  await expect(page.locator('tbody tr')).toHaveCount(1);
});
