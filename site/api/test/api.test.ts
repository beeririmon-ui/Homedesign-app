import { describe, it, expect, beforeEach, vi } from 'vitest';
import { app } from '../src/app';
import type { Env, SupplierJob } from '../src/env';
import { buildSeedSql } from '../scripts/seed';
import { createD1, migrate } from './d1-shim';
import { processSupplierJob } from '../src/lib/fulfillment';
import { resetAccessCache, verifyAccessJwt } from '../src/lib/access';
import { ORDER_ID, signWebhook } from '@hd/shared';
import { catalog } from './fixture';

const SECRET = 'test-webhook-secret-0123456789';

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
    INVOICE_PROVIDER: 'mock',
    ACCESS_TEAM_DOMAIN: '',
    ACCESS_AUD: '',
    PAYMENT_WEBHOOK_SECRET: SECRET,
  };
});

const req = (path: string, init?: RequestInit) => app.request(`http://localhost${path}`, init, env);
const json = (body: unknown, method = 'POST'): RequestInit => ({ method, headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });

async function cartWith(variant: string, qty: number, pack?: 'set' | 'unit') {
  const created = (await (await req('/api/cart', { method: 'POST' })).json()) as { id: string };
  await req(`/api/cart/${created.id}/items`, json({ variant_id: variant, qty, ...(pack ? { pack } : {}) }, 'PUT'));
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
    // ART6: digits only, no "HD" prefix
    expect(body.order_id).toMatch(ORDER_ID);
  });

  it('the waiting list (PRE1) takes one email for a product or a slot, nothing else', async () => {
    expect((await req('/api/waitlist', json({ email: 'buyer@example.com', product_id: 'vase-a' }))).status).toBe(201);
    expect((await req('/api/waitlist', json({ email: 'buyer@example.com', room: 'living-room', slot: 'vase' }))).status).toBe(201);
    expect((await req('/api/waitlist', json({ email: 'buyer@example.com', product_id: 'nope' }))).status).toBe(404);
    expect((await req('/api/waitlist', json({ email: 'not-an-email', product_id: 'vase-a' }))).status).toBe(422);
    expect((await req('/api/waitlist', json({ email: 'buyer@example.com' }))).status).toBe(422);
    const rows = await env.DB.prepare('SELECT email, product_id, room_id, slot_id FROM waitlist ORDER BY created_at').all();
    expect(rows.results).toEqual([
      { email: 'buyer@example.com', product_id: 'vase-a', room_id: null, slot_id: null },
      { email: 'buyer@example.com', product_id: null, room_id: 'living-room', slot_id: 'vase' },
    ]);
  });

  it('a product that is not sold (PRE1: NL2 or a slot on hold) never enters a cart', async () => {
    await env.DB.prepare("UPDATE products SET availability = 'unavailable', availability_reason = 'nl2-express-only' WHERE id = 'vase-b'").run();
    const created = (await (await req('/api/cart', { method: 'POST' })).json()) as { id: string };
    expect((await req(`/api/cart/${created.id}/items`, json({ variant_id: 'vase-b:default', qty: 1 }, 'PUT'))).status).toBe(404);
    const prices = (await (await req('/api/catalog/prices?ids=vase-a,vase-b')).json()) as { prices: { id: string; available: boolean }[] };
    expect(prices.prices.map((p) => [p.id, p.available])).toEqual([
      ['vase-a', true],
      ['vase-b', false],
    ]);
  });
});

describe('supplier options (2026-10-11)', () => {
  type CartBody = { subtotal_agorot: number; lines: { variant_id: string; name_he: string; option_he: string | null; unit_price_agorot: number }[] };

  it('each option is its own variant with its own price; the cart names the option; out of stock is refused', async () => {
    const id = await cartWith('cushion-a:o-black60', 2);
    const cart = (await (await req(`/api/cart/${id}`)).json()) as CartBody;
    expect(cart.lines).toEqual([
      expect.objectContaining({ variant_id: 'cushion-a:o-black60', name_he: 'ציפית כרית פשתן', option_he: 'שחור, 60×60 ס"מ', unit_price_agorot: 11900 }),
    ]);
    expect(cart.subtotal_agorot).toBe(23800);
    const oos = await req(`/api/cart/${id}/items`, json({ variant_id: 'cushion-a:o-green50', qty: 1 }, 'PUT'));
    expect(oos.status).toBe(404);
    // a product without options keeps its single variant and no option label
    const plain = (await (await req(`/api/cart/${id}/items`, json({ variant_id: 'vase-a:default', qty: 1 }, 'PUT'))).json()) as CartBody;
    expect(plain.lines.find((l) => l.variant_id === 'vase-a:default')?.option_he).toBeNull();
  });

  it("checkout snapshots the option's cost, shipping and supplier SKU, and names the option", async () => {
    const id = await cartWith('cushion-a:o-black60', 1);
    const body = (await (await req('/api/checkout', json(checkoutBody(id)))).json()) as { order_id: string };
    const item = await env.DB.prepare(
      'SELECT name_he, unit_price_agorot, unit_cost_usd_cents, unit_shipping_usd_cents, supplier_sku FROM order_items WHERE order_id = ?',
    )
      .bind(body.order_id)
      .first<Record<string, string | number>>();
    expect(item).toEqual({
      // ת8: the base name without a colour · the option's Hebrew labels (manager's rule), never the product's colour
      name_he: 'ציפית כרית פשתן · שחור, 60×60 ס"מ',
      unit_price_agorot: 11900,
      unit_cost_usd_cents: 1599,
      unit_shipping_usd_cents: 1100,
      supplier_sku: '12000059524978199',
    });
  });
});

describe('set or single piece (P1)', () => {
  type CartBody = {
    subtotal_agorot: number;
    count: number;
    lines: { pack: string; pack_qty: number; qty: number; unit_price_agorot: number; price_provisional: boolean }[];
  };
  const put = async (id: string, body: object) => req(`/api/cart/${id}/items`, json(body, 'PUT'));

  it('the set is the default; a single piece has its own price and its own line', async () => {
    const id = await cartWith('candles-a:default', 1); // no pack given: the set
    let cart = (await (await req(`/api/cart/${id}`)).json()) as CartBody;
    expect(cart.lines).toEqual([expect.objectContaining({ pack: 'set', pack_qty: 2, qty: 1, unit_price_agorot: 34900 })]);
    cart = (await (await put(id, { variant_id: 'candles-a:default', pack: 'unit', qty: 3 })).json()) as CartBody;
    expect(cart.lines).toHaveLength(2);
    expect(cart.lines[1]).toMatchObject({ pack: 'unit', pack_qty: 1, qty: 3, unit_price_agorot: 19900, price_provisional: true });
    expect(cart.subtotal_agorot).toBe(34900 + 3 * 19900);
    // removing the single pieces leaves the set
    cart = (await (await put(id, { variant_id: 'candles-a:default', pack: 'unit', qty: 0 })).json()) as CartBody;
    expect(cart.lines.map((l) => l.pack)).toEqual(['set']);
  });

  it('a product sold only as one unit refuses a single-piece line; an unknown pack is invalid', async () => {
    const id = await cartWith('vase-a:default', 1);
    const res = await put(id, { variant_id: 'vase-a:default', pack: 'unit', qty: 1 });
    expect(res.status).toBe(422);
    expect(await res.json()).toMatchObject({ error: 'pack_unavailable' });
    expect((await put(id, { variant_id: 'candles-a:default', pack: 'pair', qty: 1 })).status).toBe(422);
  });

  it('checkout snapshots the pack and the supplier units; the supplier gets qty × units; the buyer sees the pack', async () => {
    const id = await cartWith('candles-a:default', 1, 'set');
    await put(id, { variant_id: 'candles-a:default', pack: 'unit', qty: 1 });
    const r = (await (await req('/api/checkout', json(checkoutBody(id)))).json()) as { order_id: string; order_token: string };
    const { results } = await env.DB.prepare('SELECT pack, unit_sell_qty, unit_price_agorot FROM order_items WHERE order_id = ? ORDER BY line')
      .bind(r.order_id)
      .all();
    expect(results).toEqual([
      { pack: 'set', unit_sell_qty: 2, unit_price_agorot: 34900 },
      { pack: 'unit', unit_sell_qty: 1, unit_price_agorot: 19900 },
    ]);
    const view = (await (await req(`/api/orders/${r.order_id}`, { headers: { 'x-order-token': r.order_token } })).json()) as { lines: object[] };
    expect(view.lines).toEqual([expect.objectContaining({ pack: 'set', pack_qty: 2, qty: 1 }), expect.objectContaining({ pack: 'unit', pack_qty: 1, qty: 1 })]);
    const supplierUnits = await env.DB.prepare(
      "SELECT SUM(qty * unit_sell_qty) AS n FROM order_items WHERE order_id = ? AND fulfillment_source = 'dropship_cj'",
    )
      .bind(r.order_id)
      .first<{ n: number }>();
    expect(supplierUnits!.n).toBe(3);
  });

  it('live prices include the set size and the single-piece price', async () => {
    const res = (await (await req('/api/catalog/prices?ids=candles-a,vase-a')).json()) as { prices: Record<string, unknown>[] };
    expect(res.prices.find((p) => p.id === 'candles-a')).toMatchObject({
      price_agorot: 34900,
      set_qty: 2,
      unit_price_agorot: 19900,
      unit_price_estimated: true,
    });
    expect(res.prices.find((p) => p.id === 'vase-a')).toMatchObject({ set_qty: null, unit_price_agorot: null });
  });
});

describe('S11: the line, the sets and a line no longer sold (QA S6–S7 ת8, ת9, ת11)', () => {
  type CartBody = { lines: { variant_id: string; name_he: string; option_he: string | null; pack: string }[]; subtotal_agorot: number; removed?: number };
  const put = async (id: string, body: object) => req(`/api/cart/${id}/items`, json(body, 'PUT'));

  it('ת8: the order snapshot and the invoice carry "base · labels", never the colour of the product name', async () => {
    const id = await cartWith('cushion-a:o-beige45', 1);
    const r = (await (await req('/api/checkout', json(checkoutBody(id)))).json()) as { order_id: string; order_token: string };
    const view = (await (await req(`/api/orders/${r.order_id}`, { headers: { 'x-order-token': r.order_token } })).json()) as { lines: { name_he: string }[] };
    expect(view.lines.map((l) => l.name_he)).toEqual(['ציפית כרית פשתן · בז\', 45×45 ס"מ']);
    // the invoice reads the same snapshot (paid first: the job issues only for a paid order, with paid_at: ת18)
    await env.DB.prepare("UPDATE orders SET status = 'paid', paid_at = '2026-11-10T10:00:00Z' WHERE id = ?").bind(r.order_id).run();
    const issued: { lines: { name_he: string }[] }[] = [];
    const { processInvoiceJob } = await import('../src/lib/invoices');
    await processInvoiceJob(env, r.order_id, { id: 'spy', idempotent: false, issue: async (inv) => (issued.push(inv), { invoice_id: 'INV-1', url: null }) });
    expect(issued[0]!.lines.map((l) => l.name_he)).toEqual(['ציפית כרית פשתן · בז\', 45×45 ס"מ']);
  });

  it('ת9: a triptych sells as the set only: a single print (pack unit) and another print of the set are refused with 422', async () => {
    const id = await cartWith('prints-a:1+40x60', 1);
    let cart = (await (await req(`/api/cart/${id}`)).json()) as CartBody;
    expect(cart.lines).toEqual([
      expect.objectContaining({ variant_id: 'prints-a:1+40x60', pack: 'set', name_he: 'שלישיית הדפסים גאומטריים', option_he: '40×60 ס"מ' }),
    ]);
    const unit = await put(id, { variant_id: 'prints-a:1+40x60', pack: 'unit', qty: 1 });
    expect(unit.status).toBe(422);
    expect(await unit.json()).toMatchObject({ error: 'pack_unavailable' });
    for (const part of ['prints-a:2+40x60', 'prints-a:3+40x60'])
      for (const pack of ['set', 'unit'] as const) {
        const res = await put(id, { variant_id: part, pack, qty: 1 });
        expect(res.status, `${part} ${pack}`).toBe(422);
        expect(await res.json()).toMatchObject({ error: 'set_part' });
      }
    cart = (await (await req(`/api/cart/${id}`)).json()) as CartBody;
    expect(cart.lines.map((l) => `${l.variant_id}/${l.pack}`)).toEqual(['prints-a:1+40x60/set']);
    // and the order is the set: three pieces to the supplier
    const r = (await (await req('/api/checkout', json(checkoutBody(id)))).json()) as { order_id: string };
    const item = await env.DB.prepare('SELECT pack, unit_sell_qty, qty FROM order_items WHERE order_id = ?').bind(r.order_id).first();
    expect(item).toEqual({ pack: 'set', unit_sell_qty: 3, qty: 1 });
  });

  it('ת9: a part of a set already in a cart (before the rule) is removed, never charged', async () => {
    const id = await cartWith('prints-a:1+40x60', 1);
    await env.DB.prepare("INSERT INTO cart_items (cart_id, variant_id, pack, qty, added_at) VALUES (?, 'prints-a:2+40x60', 'set', 1, '2026-11-01T00:00:00Z')")
      .bind(id)
      .run();
    await env.DB.prepare("INSERT INTO cart_items (cart_id, variant_id, pack, qty, added_at) VALUES (?, 'prints-a:1+40x60', 'unit', 2, '2026-11-01T00:00:01Z')")
      .bind(id)
      .run();
    const cart = (await (await req(`/api/cart/${id}`)).json()) as CartBody;
    expect(cart.lines.map((l) => `${l.variant_id}/${l.pack}`)).toEqual(['prints-a:1+40x60/set']);
    expect(cart.removed).toBe(2);
    expect(cart.subtotal_agorot).toBe(21900);
  });

  it('ת11: a line that stops being sold leaves the cart with a notice, and is never charged', async () => {
    const id = await cartWith('vase-a:default', 1);
    await put(id, { variant_id: 'cushion-a:o-beige45', qty: 2 });
    let cart = (await (await req(`/api/cart/${id}`)).json()) as CartBody;
    expect(cart.lines).toHaveLength(2);
    expect(cart.removed).toBeUndefined();
    // PRE1 after the add: the cushion is no longer sold
    await env.DB.prepare("UPDATE products SET availability = 'unavailable', availability_reason = 'nl2-above-market' WHERE id = 'cushion-a'").run();
    cart = (await (await req(`/api/cart/${id}`)).json()) as CartBody;
    expect(cart.lines.map((l) => l.variant_id)).toEqual(['vase-a:default']);
    expect(cart.removed).toBe(1);
    expect(cart.subtotal_agorot).toBe(15900);
    // removed for good (it does not come back if the product does), and the cart keeps saying so
    expect((await env.DB.prepare('SELECT COUNT(*) AS n FROM cart_items WHERE cart_id = ?').bind(id).first<{ n: number }>())!.n).toBe(1);
    cart = (await (await put(id, { variant_id: 'vase-a:default', qty: 2 })).json()) as CartBody;
    expect(cart.removed).toBe(1);
    const r = await req('/api/checkout', json(checkoutBody(id)));
    expect(r.status).toBe(201);
    const order = (await r.json()) as { order_id: string };
    const items = await env.DB.prepare('SELECT variant_id FROM order_items WHERE order_id = ?').bind(order.order_id).all();
    expect(items.results).toEqual([{ variant_id: 'vase-a:default' }]);
  });

  it('ת11: a line that stops being sold between the cart and the payment stops the checkout (409), so the order is the one seen', async () => {
    const id = await cartWith('vase-a:default', 1);
    await put(id, { variant_id: 'cushion-a:o-beige45', qty: 1 });
    await env.DB.prepare("UPDATE product_variants SET active = 0 WHERE id = 'cushion-a:o-beige45'").run();
    const r = await req('/api/checkout', json(checkoutBody(id)));
    expect(r.status).toBe(409);
    expect(await r.json()).toMatchObject({ error: 'cart_changed', message_he: expect.stringContaining('פריט אחד כבר לא זמין והוסר') });
    // the buyer sees the cart again (one line, the notice), and the next attempt is the order they saw
    const cart = (await (await req(`/api/cart/${id}`)).json()) as CartBody;
    expect(cart).toMatchObject({ removed: 1, lines: [expect.objectContaining({ variant_id: 'vase-a:default' })] });
    expect((await req('/api/checkout', json(checkoutBody(id)))).status).toBe(201);
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
    const res = (await (await req('/api/checkout', json(checkoutBody(id)))).json()) as { order_id: string; order_token: string };
    const o = await env.DB.prepare('SELECT payment_session_id, total_agorot FROM orders WHERE id = ?')
      .bind(res.order_id)
      .first<{ payment_session_id: string; total_agorot: number }>();
    return { orderId: res.order_id, session: o!.payment_session_id, total: o!.total_agorot, token: res.order_token };
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
    const { orderId, session, total, token } = await pendingOrder();
    const ev = { id: 'evt_00000002', type: 'payment.succeeded', session_id: session, amount_agorot: total };
    expect(await (await post(ev)).json()).toMatchObject({ outcome: 'paid' });
    expect(await (await post(ev)).json()).toMatchObject({ duplicate: true });
    // S9: the supplier job and the tax invoice job (a job after "paid")
    expect(sent).toEqual([
      { kind: 'submit-order', order_id: orderId },
      { kind: 'issue-invoice', order_id: orderId },
    ]);
    const o = await env.DB.prepare('SELECT status FROM orders WHERE id = ?').bind(orderId).first<{ status: string }>();
    expect(o!.status).toBe('paid');
    // ART6: the buyer reads "התקבלה", then "בהכנה" once the order went to the supplier; never "הועברה לספק"
    const view = async () => ((await (await req(`/api/orders/${orderId}`, { headers: { 'x-order-token': token } })).json()) as { status_he: string }).status_he;
    expect(await view()).toBe('התקבלה');
    await processSupplierJob(env, { kind: 'submit-order', order_id: orderId }, 1);
    expect(await view()).toBe('בהכנה');
    // S9: the invoice job issues once (the mock provider), and a retry of the job issues nothing more
    expect(await processSupplierJob(env, { kind: 'issue-invoice', order_id: orderId }, 1)).toBe('submitted');
    expect(await processSupplierJob(env, { kind: 'issue-invoice', order_id: orderId }, 2)).toBe('skipped');
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
