/**
 * QA S18, question 4b: the email-mode test build (EMAIL_PROVIDER=qa-test, a test provider added to the closed list in
 * this copy only), rendered: do the email lines come back where they belong, and does the waiting-list form work again?
 * Run: cd <email copy>/site && HD_BASE_URL=http://127.0.0.1:8796 QA_OUT=<dir> npx --no-install playwright test --config=qa18/qa18-email.config.ts
 */
import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';
import { ORDER_DELAY_HE } from '@hd/shared/constants';
import { shopPath } from '@hd/shared/product-url';
import { placeOrder, waitStatus, openCustomerOrder } from '../e2e/ops';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const OUT = process.env.QA_OUT!;
mkdirSync(join(OUT, 'shots'), { recursive: true });
const built = JSON.parse(readFileSync(join(SITE, '.generated/copy.he.json'), 'utf8')) as { sends: boolean; email_provider: string; strings: Record<string, string> };
const catalog = JSON.parse(readFileSync(join(SITE, '.generated/catalog.public.json'), 'utf8')) as {
  products: { id: string; slot: string; price_agorot: number | null; variants: { id: string }[]; availability: { status: string } }[];
};
const results: Record<string, unknown> = { email_provider: built.email_provider, sends: built.sends };
const note = (k: string, v: unknown) => {
  results[k] = v;
  writeFileSync(join(OUT, 'qa-s18-email.json'), JSON.stringify(results, null, 1) + '\n');
};
function d1(sql: string) {
  execFileSync('node', ['../node_modules/wrangler/wrangler-dist/qasrv18.js', 'd1', 'execute', 'DB', '--local', '--persist-to', '../.wrangler-state', '--command', sql], { cwd: join(SITE, 'api'), stdio: 'pipe' });
}
test.describe.configure({ mode: 'serial', timeout: 180_000 });

test('E1 checkout: the email hint, the marketing box, the invoice note', async ({ page, request }) => {
  const h = { 'cf-connecting-ip': '10.18.28.1' };
  const p = catalog.products.find((x) => x.slot === 'vase' && x.price_agorot && x.availability.status === 'available')!;
  const cart = (await (await request.post('/api/cart', { headers: h })).json()) as { id: string };
  await request.put(`/api/cart/${cart.id}/items`, { headers: h, data: { variant_id: p.variants[0]!.id, qty: 1 } });
  await page.addInitScript((id) => localStorage.setItem('hd.cart', id), cart.id);
  await page.goto('/checkout/');
  await expect(page.getByLabel('אימייל')).toBeVisible();
  const r = {
    email_hint: await page.locator('#h-email').innerText(),
    checkboxes: await page.getByRole('checkbox').count(),
    marketing_box: await page.getByRole('checkbox', { name: built.strings['checkout.marketing_consent'] }).count(),
    total_note: await page.locator('.summary .small.muted').innerText(),
  };
  await page.screenshot({ path: join(OUT, 'shots', 'email-mode-checkout-1280.png'), fullPage: true });
  note('E1', r);
  expect(r.email_hint).toBe(built.strings['checkout.email_hint']);
  expect(r.marketing_box).toBe(1);
  expect(r.total_note).toBe(built.strings['checkout.total_note']);
});

test('E2 the order page: received, another browser, the delay\'s third sentence', async ({ page, request }) => {
  const o = await placeOrder(request, '10.18.28.2');
  await openCustomerOrder(page, o);
  const received = await page.locator('.order-sheet > p.small.muted').innerText();
  await page.screenshot({ path: join(OUT, 'shots', 'email-mode-order-1280.png'), fullPage: true });
  const other = await page.context().browser()!.newContext({ locale: 'he-IL' });
  const p2 = await other.newPage();
  await p2.goto(`/order/${o.id}/`);
  const noAccess = await p2.getByRole('alert').innerText();
  await other.close();
  const stuck = await placeOrder(request, '10.18.28.3');
  await waitStatus(request, stuck, 'sent_to_supplier');
  d1(`UPDATE supplier_shipments SET status = 'failed', supplier_order_id = NULL, reach = 'none', attempts = 5, last_error = 'refused' WHERE order_id = '${stuck.id}'; UPDATE orders SET status = 'supplier_error' WHERE id = '${stuck.id}';`);
  await openCustomerOrder(page, stuck);
  await expect(page.locator('.order-delay')).not.toHaveText('', { timeout: 5_000 });
  const delay = await page.locator('.order-delay').innerText();
  note('E2', { received, noAccess, delay });
  expect(received).toBe(built.strings['order.next.received']);
  expect(noAccess).toBe(built.strings['order.no_access']);
  expect(delay).toBe(`${ORDER_DELAY_HE} ${built.strings['order.delay.followup']}`);
});

test('E3 a product on hold: the waiting-list form is back, and it posts', async ({ page }) => {
  const held = catalog.products.find((x) => x.availability.status !== 'available')!;
  await page.goto(shopPath(held.id));
  const offer = page.getByRole('button', { name: built.strings['waitlist.offer'] });
  await expect(offer).toBeVisible();
  await offer.click();
  const why = await page.locator('.waitlist-form p.small.muted').innerText();
  await page.getByLabel('אימייל').fill('qa18.email-mode@example.com');
  await page.getByRole('button', { name: built.strings['waitlist.submit'] }).click();
  await expect(page.getByRole('status')).toHaveText(built.strings['waitlist.done']);
  await page.screenshot({ path: join(OUT, 'shots', 'email-mode-waitlist-1280.png'), fullPage: true });
  note('E3', { product: held.id, why, done: await page.getByRole('status').innerText() });
  expect(why).toBe(built.strings['waitlist.why']);
});

test('E4 the privacy policy: the email wording', async ({ page }) => {
  await page.goto('/privacy/');
  const text = await page.locator('main, .page').first().innerText();
  note('E4', { processors: text.includes(built.strings['privacy.processors']), marketing: text.includes(built.strings['privacy.marketing']) });
  expect(text).toContain(built.strings['privacy.processors']);
  expect(text).toContain(built.strings['privacy.marketing']);
});
