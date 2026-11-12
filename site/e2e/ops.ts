/**
 * S13: helpers for the operations specs (operations.spec.ts, a11y.spec.ts). An order is placed through the public API and
 * paid on the mock payment page, as a customer would; the admin is reached with the local preview's dev token (api/.dev.vars
 * `ADMIN_DEV_TOKEN`, honoured only by a local run: lib/access.ts), the e2e suite's stand-in for Cloudflare Access.
 */
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, type APIRequestContext, type Page } from '@playwright/test';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');

/** the local preview's admin token; the suite fails loudly without it (npm run db:reset adds one, CI writes one) */
export function devToken(): string {
  let vars = '';
  try {
    vars = readFileSync(resolve(SITE, 'api/.dev.vars'), 'utf8');
  } catch {
    /* reported below */
  }
  const t = /^ADMIN_DEV_TOKEN=(.{24,})$/m.exec(vars)?.[1]?.trim();
  if (!t) throw new Error('api/.dev.vars has no ADMIN_DEV_TOKEN: run `npm run db:reset -w @hd/api` (or see docs/ops/deploy-runbook.md, CI)');
  return t;
}
export const adminHeaders = (): Record<string, string> => ({ 'x-hd-dev-admin': devToken() });

export type Placed = { id: string; token: string; total: number };

/** a paid order through the public API and the mock payment page; `ip` keeps the rate limits per test; `consents.marketing`
 * as the request says it (S20, ת57: the Worker records it only where a provider sends marketing email) */
export async function placeOrder(request: APIRequestContext, ip: string, variant = 'vase', consents: { marketing?: boolean } = {}): Promise<Placed> {
  const h = { 'cf-connecting-ip': ip };
  const catalog = JSON.parse(readFileSync(resolve(SITE, '.generated/catalog.public.json'), 'utf8')) as {
    products: { id: string; slot: string; price_agorot: number | null; variants: { id: string }[]; availability: { status: string } }[];
  };
  // a product the room sells, in the room's own option (the first variant)
  const p = catalog.products.find((x) => x.slot === variant && x.price_agorot && x.availability.status === 'available')!;
  const cart = (await (await request.post('/api/cart', { headers: h })).json()) as { id: string };
  expect((await request.put(`/api/cart/${cart.id}/items`, { headers: h, data: { variant_id: p.variants[0]!.id, qty: 1 } })).status()).toBe(200);
  const res = await request.post('/api/checkout', {
    headers: h,
    data: {
      cart_id: cart.id,
      customer: { full_name: 'נועה כהן', email: 'noa.ops@example.com', phone: '050-1234567' },
      address: { city: 'חיפה', street: 'הנמל', house: '12' },
      shipping_method: 'express',
      consents: { terms: true, marketing: consents.marketing ?? false },
    },
  });
  expect(res.status()).toBe(201);
  const co = (await res.json()) as { order_id: string; order_token: string; redirect_url: string };
  const session = new URL(co.redirect_url).pathname.split('/').pop()!;
  const done = await request.post(`/mock-pay/${session}/complete`, { headers: h, form: { outcome: 'success' }, maxRedirects: 0 });
  expect(done.status()).toBe(303);
  const view = (await (await request.get(`/api/orders/${co.order_id}`, { headers: { 'x-order-token': co.order_token } })).json()) as { total_agorot: number };
  return { id: co.order_id, token: co.order_token, total: view.total_agorot };
}

/** waits until the customer's view of the order reaches a status (the queue consumer runs in the local preview) */
export async function waitStatus(request: APIRequestContext, o: Placed, status: string): Promise<void> {
  await expect
    .poll(async () => ((await (await request.get(`/api/orders/${o.id}`, { headers: { 'x-order-token': o.token } })).json()) as { status: string }).status, {
      timeout: 30_000,
      intervals: [500, 1000, 2000],
    })
    .toBe(status);
}

/** the mock supplier's answer, played through the Admin API */
export async function supplierSays(request: APIRequestContext, o: Placed, event: 'accepted' | 'shipped' | 'delivered' | 'cancel_confirmed' | 'cancel_refused') {
  const r = await request.post(`/api/admin/orders/${o.id}/mock-supplier`, { headers: adminHeaders(), data: { event } });
  expect(r.status(), await r.text()).toBe(200);
}

/** the customer's order page in this browser: the order's token is where the checkout leaves it */
export async function openCustomerOrder(page: Page, o: Placed): Promise<void> {
  await page.addInitScript(([id, token]) => localStorage.setItem(`hd.order.${id}`, token!), [o.id, o.token]);
  await page.goto(`/order/${o.id}/`);
  await expect(page.locator('.order-sheet')).toBeVisible({ timeout: 15_000 });
}
