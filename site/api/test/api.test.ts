import { describe, it, expect, beforeEach, vi } from 'vitest';
import { app } from '../src/app';
import type { Env, SupplierJob } from '../src/env';
import { buildSeedSql } from '../scripts/seed';
import { createD1, migrate } from './d1-shim';
import { processSupplierJob } from '../src/lib/fulfillment';
import { resetAccessCache, verifyAccessJwt } from '../src/lib/access';
import { DEFAULT_SETTINGS, signWebhook, unitEconomics, type FullCatalog, type FullProduct } from '@hd/shared';

const SECRET = 'test-webhook-secret-0123456789';

function product(id: string, slot: string, price: number, cost: number): FullProduct {
  const base = {
    id,
    room: 'living-room',
    slot,
    name_he: `מוצר ${id}`,
    name_provisional: true,
    description_he: 'תיאור',
    price_agorot: price,
    compare_at_agorot: null,
    price_provisional: true,
    materials_he: ['פשתן'],
    dimensions_cm: { width: 10, depth: null, height: 20 },
    color_hex: '#F4F1EC',
    shipping_days: [12, 30] as [number, number],
    notes_he: [],
    set_of: null,
    variants: [{ id: `${id}:default`, label_he: 'ברירת מחדל' }],
  };
  return {
    ...base,
    name_supplier: 'Supplier name',
    category: null,
    status: 'candidate',
    source_path: `data/products/${slot}/${id}.json`,
    supplier: { name: 'CJ Dropshipping', url: 'https://example.invalid/p', sku: 'SKU1' },
    cost_usd_cents: cost,
    shipping_usd_cents: 1000,
    shipping_from_default: false,
    shipping_source: 'cj',
    sell_qty: 1,
    fulfillment_source: 'dropship_cj',
    fx_usd_ils: DEFAULT_SETTINGS.fx_usd_ils,
    nordic_score: 8,
    economics: unitEconomics(
      { retail_agorot: price, cost_usd_cents: cost, shipping_usd_cents: 1000, fx_usd_ils: DEFAULT_SETTINGS.fx_usd_ils },
      DEFAULT_SETTINGS,
    ),
  };
}

const catalog: FullCatalog = {
  version: 'testcatalog01',
  built_at: '2026-10-09T00:00:00.000Z',
  git_commit: 'test',
  mode: 'provisional',
  styles: [{ id: 'nordic', name_he: 'נורדי', available: true }],
  rooms: [
    {
      id: 'living-room',
      house_room_id: 'living',
      name_he: 'סלון',
      style: 'nordic',
      frame: 'M0',
      slots_version: '1.3.3',
      base_layers: [{ id: 'shell', z: 0, blend: 'normal' }],
      light_slots: [],
      exits: [],
      built: true,
      slots: [
        {
          id: 'vase',
          name_he: 'אגרטל',
          category: 'ceramics-tableware',
          placement: 'sill',
          z: 16,
          set_of: null,
          has_light: false,
          has_shadow: true,
          fillers_he: [],
          hotspot: { u: 0.25, v: 0.5, provisional: true, visible: true },
          zoom_frame: [0.1, 0.4, 0.3, 0.6],
          options: [
            { position: 1, product_id: 'vase-a', placeholder: false, label_he: 'א', is_default: true },
            { position: 2, product_id: 'vase-b', placeholder: false, label_he: 'ב', is_default: false },
            { position: 3, product_id: null, placeholder: true, label_he: 'ג', is_default: false },
          ],
        },
      ],
    },
  ],
  products: [product('vase-a', 'vase', 15900, 1624), product('vase-b', 'vase', 25900, 2405)],
  shipping: [
    { id: 'economy', label_he: 'חסכוני', price_agorot: 2900, free_over_agorot: 29900, days_he: '', provisional: true, is_default: true },
    { id: 'express', label_he: 'מהיר', price_agorot: 5900, free_over_agorot: null, days_he: '', provisional: true, is_default: false },
  ],
  vat_rate: 0.18,
  hidden: [],
  invalid_cards: [],
  economics: { settings: DEFAULT_SETTINGS, defaults_used: ['fx_usd_ils'], sources: { settings: null, products: null, freight: null } },
};

let env: Env;
let sent: SupplierJob[];

beforeEach(() => {
  const DB = createD1();
  migrate(DB, buildSeedSql(catalog));
  sent = [];
  env = {
    DB,
    SUPPLIER_QUEUE: { send: vi.fn(async (m: SupplierJob) => void sent.push(m)), sendBatch: vi.fn() } as unknown as Queue<SupplierJob>,
    ENVIRONMENT: 'test',
    PAYMENT_PROVIDER: 'mock',
    SUPPLIER_PROVIDER: 'mock',
    ACCESS_TEAM_DOMAIN: '',
    ACCESS_AUD: '',
    PAYMENT_WEBHOOK_SECRET: SECRET,
  };
});

const req = (path: string, init?: RequestInit) => app.request(`http://localhost${path}`, init, env);
const json = (body: unknown, method = 'POST'): RequestInit => ({ method, headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });

async function cartWith(variant: string, qty: number) {
  const created = (await (await req('/api/cart', { method: 'POST' })).json()) as { id: string };
  await req(`/api/cart/${created.id}/items`, json({ variant_id: variant, qty }, 'PUT'));
  return created.id;
}

const checkoutBody = (cart_id: string) => ({
  cart_id,
  customer: { full_name: 'ישראלה ישראלי', email: 'buyer@example.com', phone: '050-1234567' },
  address: { city: 'תל אביב', street: 'הרצל', house: '10' },
  shipping_method: 'express',
  consents: { terms: true, marketing: false },
});

describe('public api', () => {
  it('health reports the seeded catalog version and sets security headers', async () => {
    const res = await req('/api/health');
    expect(res.status).toBe(200);
    expect(await res.json()).toMatchObject({ ok: true, catalog_version: 'testcatalog01' });
    expect(res.headers.get('x-content-type-options')).toBe('nosniff');
    expect(res.headers.get('content-security-policy')).toContain("default-src 'none'");
  });

  it('prices come from D1 and unknown variants are rejected', async () => {
    const id = await cartWith('vase-a:default', 2);
    const cart = (await (await req(`/api/cart/${id}`)).json()) as { subtotal_agorot: number; count: number };
    expect(cart).toMatchObject({ subtotal_agorot: 31800, count: 2 });
    const bad = await req(`/api/cart/${id}/items`, json({ variant_id: 'nope:default', qty: 1 }, 'PUT'));
    expect(bad.status).toBe(404);
    const removed = (await (await req(`/api/cart/${id}/items`, json({ variant_id: 'vase-a:default', qty: 0 }, 'PUT'))).json()) as { count: number };
    expect(removed.count).toBe(0);
  });

  it('rejects malformed carts and bodies', async () => {
    expect((await req('/api/cart/short')).status).toBe(404);
    const id = await cartWith('vase-a:default', 1);
    expect((await req(`/api/cart/${id}/items`, json({ variant_id: 'vase-a:default', qty: 99 }, 'PUT'))).status).toBe(422);
    expect((await req(`/api/cart/${id}/items`, { method: 'PUT', body: 'x' })).status).toBe(400);
  });

  it('checkout validates input, snapshots costs and redirects to the hosted page', async () => {
    const id = await cartWith('vase-b:default', 1);
    const invalid = await req('/api/checkout', json({ ...checkoutBody(id), consents: { terms: false } }));
    expect(invalid.status).toBe(422);
    const res = await req('/api/checkout', json(checkoutBody(id)));
    expect(res.status).toBe(201);
    const body = (await res.json()) as { order_id: string; order_token: string; redirect_url: string };
    expect(body.redirect_url).toMatch(/\/mock-pay\/ms_/);
    const order = await env.DB.prepare('SELECT * FROM orders WHERE id = ?').bind(body.order_id).first<Record<string, number | string>>();
    expect(order).toMatchObject({ status: 'pending_payment', subtotal_agorot: 25900, shipping_agorot: 5900, total_agorot: 31800 });
    expect(order!.vat_agorot).toBe(31800 - Math.round(31800 / 1.18));
    const item = await env.DB.prepare('SELECT unit_cost_usd_cents FROM order_items WHERE order_id = ?')
      .bind(body.order_id)
      .first<{ unit_cost_usd_cents: number }>();
    expect(item!.unit_cost_usd_cents).toBe(2405);
    // cart is closed after checkout
    expect((await req(`/api/cart/${id}`)).status).toBe(409);
    // buyer status needs the token
    expect((await req(`/api/orders/${body.order_id}`, { headers: { 'x-order-token': 'x'.repeat(32) } })).status).toBe(404);
    const view = (await (await req(`/api/orders/${body.order_id}`, { headers: { 'x-order-token': body.order_token } })).json()) as { status_he: string };
    expect(view.status_he).toBe('ממתינה לתשלום');
  });
});

describe('customer shipping fees (settings, decision E1)', () => {
  it('economy is charged below the free-shipping threshold and free at or above it; express is always charged', async () => {
    const below = await cartWith('vase-b:default', 1); // 259
    const r1 = (await (await req('/api/checkout', json({ ...checkoutBody(below), shipping_method: 'economy' }))).json()) as { order_id: string };
    const o1 = await env.DB.prepare('SELECT shipping_agorot, total_agorot FROM orders WHERE id = ?').bind(r1.order_id).first();
    expect(o1).toMatchObject({ shipping_agorot: 2900, total_agorot: 28800 });
    const above = await cartWith('vase-a:default', 2); // 318
    const r2 = (await (await req('/api/checkout', json({ ...checkoutBody(above), shipping_method: 'economy' }))).json()) as { order_id: string };
    const o2 = await env.DB.prepare('SELECT shipping_agorot, total_agorot FROM orders WHERE id = ?').bind(r2.order_id).first();
    expect(o2).toMatchObject({ shipping_agorot: 0, total_agorot: 31800 });
    const item = await env.DB.prepare('SELECT fulfillment_source, unit_sell_qty FROM order_items WHERE order_id = ?').bind(r2.order_id).first();
    expect(item).toMatchObject({ fulfillment_source: 'dropship_cj', unit_sell_qty: 1 });
  });
});

describe('payment webhook', () => {
  async function pendingOrder() {
    const id = await cartWith('vase-a:default', 1);
    const res = (await (await req('/api/checkout', json(checkoutBody(id)))).json()) as { order_id: string };
    const o = await env.DB.prepare('SELECT payment_session_id, total_agorot FROM orders WHERE id = ?')
      .bind(res.order_id)
      .first<{ payment_session_id: string; total_agorot: number }>();
    return { orderId: res.order_id, session: o!.payment_session_id, total: o!.total_agorot };
  }
  async function post(event: object, secret = SECRET, ts = Math.floor(Date.now() / 1000)) {
    const body = JSON.stringify(event);
    return req('/api/webhooks/payment/mock', {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'x-mock-signature': await signWebhook(secret, body, ts) },
      body,
    });
  }

  it('rejects bad and stale signatures', async () => {
    const { session, total } = await pendingOrder();
    const ev = { id: 'evt_00000001', type: 'payment.succeeded', session_id: session, amount_agorot: total };
    expect((await post(ev, 'wrong-secret')).status).toBe(401);
    expect((await post(ev, SECRET, Math.floor(Date.now() / 1000) - 3600)).status).toBe(401);
  });

  it('marks the order paid once, enqueues the supplier job, and ignores duplicates', async () => {
    const { orderId, session, total } = await pendingOrder();
    const ev = { id: 'evt_00000002', type: 'payment.succeeded', session_id: session, amount_agorot: total };
    expect(await (await post(ev)).json()).toMatchObject({ outcome: 'paid' });
    expect(await (await post(ev)).json()).toMatchObject({ duplicate: true });
    expect(sent).toEqual([{ kind: 'submit-order', order_id: orderId }]);
    const o = await env.DB.prepare('SELECT status FROM orders WHERE id = ?').bind(orderId).first<{ status: string }>();
    expect(o!.status).toBe('paid');
  });

  it('does not mark paid when the amount differs', async () => {
    const { orderId, session, total } = await pendingOrder();
    expect(await (await post({ id: 'evt_00000003', type: 'payment.succeeded', session_id: session, amount_agorot: total - 100 })).json()).toMatchObject({
      outcome: 'amount_mismatch',
    });
    const o = await env.DB.prepare('SELECT status FROM orders WHERE id = ?').bind(orderId).first<{ status: string }>();
    expect(o!.status).toBe('pending_payment');
  });

  it('mock hosted page completes the payment through the signed webhook', async () => {
    const { orderId, session } = await pendingOrder();
    const page = await req(`/mock-pay/${session}`);
    expect(page.status).toBe(200);
    expect(await page.text()).toContain('תשלום מדומה');
    const done = await req(`/mock-pay/${session}/complete`, {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: 'outcome=success',
    });
    expect(done.status).toBe(303);
    expect(done.headers.get('location')).toBe(`/order/${orderId}/`);
    const o = await env.DB.prepare('SELECT status FROM orders WHERE id = ?').bind(orderId).first<{ status: string }>();
    expect(o!.status).toBe('paid');
  });

  it('mock payments are refused in production', async () => {
    env.ENVIRONMENT = 'production';
    expect((await req('/mock-pay/ms_anything')).status).toBe(404);
  });

  it('queue consumer submits to the supplier once', async () => {
    const { orderId, session, total } = await pendingOrder();
    await post({ id: 'evt_00000004', type: 'payment.succeeded', session_id: session, amount_agorot: total });
    expect(await processSupplierJob(env, { kind: 'submit-order', order_id: orderId }, 1)).toBe('submitted');
    expect(await processSupplierJob(env, { kind: 'submit-order', order_id: orderId }, 2)).toBe('skipped');
    const so = await env.DB.prepare('SELECT status, supplier_order_id FROM supplier_shipments WHERE order_id = ?').bind(orderId).first();
    expect(so).toMatchObject({ status: 'submitted', supplier_order_id: `MOCK-${orderId}` });
  });
});

describe('admin', () => {
  it('is closed without Cloudflare Access and open with the local dev bypass', async () => {
    expect((await req('/api/admin/overview')).status).toBe(403);
    env.ADMIN_DEV_BYPASS = '1';
    const res = await req('/api/admin/products');
    expect(res.status).toBe(200);
    const { products } = (await res.json()) as { products: { id: string; contribution_agorot: number; margin_rate: number }[] };
    // the D1 view agrees with shared/src/pricing.ts
    for (const p of catalog.products) {
      const row = products.find((r) => r.id === p.id)!;
      expect(row.contribution_agorot).toBe(p.economics.contribution_agorot);
      expect(row.margin_rate).toBeCloseTo(p.economics.margin_rate, 3);
    }
  });

  it('dev bypass is ignored in preview', async () => {
    env.ADMIN_DEV_BYPASS = '1';
    env.ENVIRONMENT = 'preview';
    expect((await req('/api/admin/overview')).status).toBe(403);
  });

  it('verifies Access JWTs (signature, aud, iss, exp)', async () => {
    resetAccessCache();
    const { privateKey, publicKey } = (await crypto.subtle.generateKey(
      { name: 'RSASSA-PKCS1-v1_5', modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: 'SHA-256' },
      true,
      ['sign', 'verify'],
    )) as CryptoKeyPair;
    const jwk = { ...(await crypto.subtle.exportKey('jwk', publicKey)), kid: 'k1' };
    const fetcher = (async () => new Response(JSON.stringify({ keys: [jwk] }))) as unknown as typeof fetch;
    const b64 = (o: object | ArrayBuffer) =>
      Buffer.from(o instanceof ArrayBuffer ? new Uint8Array(o) : new TextEncoder().encode(JSON.stringify(o))).toString('base64url');
    const now = Math.floor(Date.now() / 1000);
    const sign = async (payload: object) => {
      const head = `${b64({ alg: 'RS256', kid: 'k1' })}.${b64(payload)}`;
      return `${head}.${b64(await crypto.subtle.sign('RSASSA-PKCS1-v1_5', privateKey, new TextEncoder().encode(head)))}`;
    };
    const opts = { domain: 'team.cloudflareaccess.com', aud: 'aud-1', nowSec: now, fetcher };
    const good = { aud: ['aud-1'], iss: 'https://team.cloudflareaccess.com', exp: now + 60, email: 'owner@example.com' };
    expect(await verifyAccessJwt(await sign(good), opts)).toEqual({ ok: true, email: 'owner@example.com' });
    expect(await verifyAccessJwt(await sign({ ...good, aud: ['other'] }), opts)).toMatchObject({ ok: false, reason: 'aud' });
    expect(await verifyAccessJwt(await sign({ ...good, exp: now - 1 }), opts)).toMatchObject({ ok: false, reason: 'expired' });
    const tampered = (await sign(good)).replace(/\.[^.]+\./, `.${b64({ ...good, email: 'attacker@example.com' })}.`);
    expect(await verifyAccessJwt(tampered, opts)).toMatchObject({ ok: false, reason: 'signature' });
  });
});
