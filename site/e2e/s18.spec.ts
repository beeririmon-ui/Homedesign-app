/**
 * S18: with no email provider (EMAIL_PROVIDER=UNDECIDED), nothing the customer reads promises an email, an SMS, a message
 * or an update, as the pages render in a browser (tools/lib/promises.ts says what a promise is; tools/check-promises.ts
 * checks the build's files). The lines are master-designer's (site/copy/promises.he.json), as this build chose them
 * (.generated/copy.he.json).
 */
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type Page } from '@playwright/test';
import { ORDER_DELAY_HE } from '@hd/shared/constants';
import { shopPath } from '@hd/shared/product-url';
import { promiseFindings } from '../tools/lib/promises';
import { openCustomerOrder, placeOrder, supplierSays, waitStatus, type Placed } from './ops';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const built = JSON.parse(readFileSync(join(SITE, '.generated/copy.he.json'), 'utf8')) as { sends: boolean; strings: Record<string, string | null> };
const line = (k: string): string => {
  const l = built.strings[k];
  if (typeof l !== 'string') throw new Error(`the copy has no line ${k}`);
  return l;
};
const catalog = JSON.parse(readFileSync(join(SITE, '.generated/catalog.public.json'), 'utf8')) as {
  products: { id: string; slot: string; price_agorot: number | null; variants: { id: string }[]; availability: { status: string } }[];
};

/** the preview's own D1 (api: wrangler dev --persist-to ../.wrangler-state) */
function d1(sql: string) {
  execFileSync('npx', ['--no-install', 'wrangler', 'd1', 'execute', 'DB', '--local', '--persist-to', '../.wrangler-state', '--command', sql], {
    cwd: join(SITE, 'api'),
    stdio: 'pipe',
  });
}
/** what the page says, as a person reads it after hydration, and every promise in it */
async function promisesOn(page: Page): Promise<string[]> {
  const texts = await page.evaluate(() => [
    document.body.innerText,
    ...Array.from(document.querySelectorAll('[aria-label], [title], [placeholder], img[alt]')).flatMap((el) =>
      ['aria-label', 'title', 'placeholder', 'alt'].map((a) => el.getAttribute(a) ?? ''),
    ),
  ]);
  return texts.flatMap((t) => promiseFindings(t).map((f) => `${f.rule}: "${f.sentence}"`));
}

test.describe.configure({ mode: 'serial', timeout: 120_000 });

test('the build has no email provider: the wording without an email', () => {
  expect(built.sends).toBe(false);
  for (const k of ['checkout.marketing_consent', 'order.delay.followup', 'waitlist.offer']) expect(built.strings[k], k).toBeNull();
});

test('the checkout: what the address is for, the total with VAT, no marketing box, no promise', async ({ page, request }) => {
  const h = { 'cf-connecting-ip': '10.18.0.1' };
  const p = catalog.products.find((x) => x.slot === 'vase' && x.price_agorot && x.availability.status === 'available')!;
  const cart = (await (await request.post('/api/cart', { headers: h })).json()) as { id: string };
  expect((await request.put(`/api/cart/${cart.id}/items`, { headers: h, data: { variant_id: p.variants[0]!.id, qty: 1 } })).status()).toBe(200);
  await page.addInitScript((id) => localStorage.setItem('hd.cart', id), cart.id);
  await page.goto('/checkout/');
  await expect(page.getByLabel('אימייל')).toBeVisible();
  await expect(page.locator('#h-email')).toHaveText(line('checkout.email_hint'));
  await expect(page.getByLabel('אימייל')).toHaveAttribute('aria-describedby', 'h-email');
  // the terms, and nothing else: no box asks for marketing email that nobody sends
  await expect(page.getByRole('checkbox')).toHaveCount(1);
  await expect(page.getByRole('checkbox', { name: /קראתי ואני מסכים/ })).toBeVisible();
  await expect(page.locator('.summary .small.muted')).toHaveText(line('checkout.total_note'));
  expect(await promisesOn(page)).toEqual([]);
});

let paid: Placed;
test('the order page after payment: the order is on this page, in this browser; no email', async ({ page, request }) => {
  paid = await placeOrder(request, '10.18.0.2');
  await openCustomerOrder(page, paid);
  await expect(page.locator('.order-sheet > p.small.muted')).toHaveText(line('order.next.received'));
  expect(await promisesOn(page)).toEqual([]);
  // in another browser (no token here): the honest reason, no "we emailed you"
  const other = await page.context().browser()!.newContext({ locale: 'he-IL' });
  const p2 = await other.newPage();
  await p2.goto(`/order/${paid.id}/`);
  await expect(p2.getByRole('alert')).toHaveText(line('order.no_access'));
  expect(await promisesOn(p2)).toEqual([]);
  await other.close();
});

test('the delayed order: §7 in two sentences, without the third (the email one)', async ({ page, request }) => {
  const stuck = await placeOrder(request, '10.18.0.3');
  await waitStatus(request, stuck, 'sent_to_supplier');
  d1(
    `UPDATE supplier_shipments SET status = 'failed', supplier_order_id = NULL, reach = 'none', attempts = 5, last_error = 'refused' WHERE order_id = '${stuck.id}'; UPDATE orders SET status = 'supplier_error' WHERE id = '${stuck.id}';`,
  );
  await openCustomerOrder(page, stuck);
  await expect(page.locator('.order-delay')).toHaveText(ORDER_DELAY_HE);
  expect(await promisesOn(page)).toEqual([]);
});

test('shipped: "מספר המשלוח למעלה" only when there is a number above', async ({ page, request }) => {
  await waitStatus(request, paid, 'sent_to_supplier');
  await supplierSays(request, paid, 'shipped');
  await waitStatus(request, paid, 'shipped');
  await openCustomerOrder(page, paid);
  await expect(page.locator('.order-sheet > p.small.muted')).toHaveText(line('order.next.shipped'));
  d1(`UPDATE supplier_shipments SET tracking_number = NULL, tracking_url = NULL WHERE order_id = '${paid.id}';`);
  await page.reload();
  await expect(page.locator('.order-sheet > p.small.muted')).toHaveText(line('order.next.shipped_no_number'));
  await expect(page.locator('.order-sheet')).not.toContainText('מספר המשלוח למעלה');
});

test('a product on hold: "המלאי אינו זמין כעת" alone; no form, no address asked for, no promise', async ({ page }) => {
  const held = catalog.products.filter((p) => p.availability.status !== 'available');
  expect(held.length).toBeGreaterThan(0);
  for (const p of held) {
    await page.goto(shopPath(p.id));
    await expect(page.locator('.waitlist-status')).toHaveText('המלאי אינו זמין כעת');
    await expect(page.locator('.waitlist button, .waitlist input')).toHaveCount(0);
    await expect(page.getByRole('button', { name: /עדכנו/ })).toHaveCount(0);
    expect(await promisesOn(page), p.id).toEqual([]);
  }
});

test('every page in the sitemap, the cart, the empty checkout and 404: no promise of an email', async ({ page, request }) => {
  const sitemap = await (await request.get('/sitemap.xml')).text();
  const paths = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => {
    const u = new URL(m[1]!.replace(/&amp;/g, '&'));
    return `${u.pathname}${u.search}`;
  });
  expect(paths.length).toBeGreaterThan(40);
  const found: string[] = [];
  for (const path of [...paths, '/cart/', '/checkout/', '/no-such-page/']) {
    await page.goto(path, { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle', { timeout: 8_000 }).catch(() => undefined);
    for (const f of await promisesOn(page)) found.push(`${path} ${f}`);
  }
  expect(found).toEqual([]);
});
