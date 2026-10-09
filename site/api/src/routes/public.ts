/** Public API: catalog, cart, checkout, order status. */
import { Hono } from 'hono';
import { z } from 'zod';
import {
  CartItemInputSchema,
  CheckoutRequestSchema,
  ORDER_STATUS_HE,
  customerShippingAgorot,
  randomToken,
  sha256Hex,
  timingSafeEqualHex,
  type CheckoutResponse,
  type OrderStatus,
  type OrderView,
} from '@hd/shared';
import type { AppEnv } from '../env';
import { HttpError, clientKey, nowIso, orderId, rateLimit, readJson } from '../lib/http';
import { createCart, economics, openCartOr404, readCart, setCartItem, shippingOptions } from '../lib/store';
import { paymentProvider } from '../lib/payments';

export const publicApi = new Hono<AppEnv>();

publicApi.get('/health', async (c) => {
  const meta = await c.env.DB.prepare("SELECT value FROM catalog_meta WHERE key = 'catalog_version'").first<{ value: string }>();
  return c.json({ ok: true, environment: c.env.ENVIRONMENT, catalog_version: meta?.value ?? null });
});

// ---------- catalog (live prices; the site bundles the descriptive catalog) ----------
const IdsSchema = z.string().regex(/^[a-z0-9:,-]{1,2000}$/);

publicApi.get('/catalog/prices', async (c) => {
  const ids = IdsSchema.safeParse(c.req.query('ids') ?? '');
  if (!ids.success) throw new HttpError(400, 'invalid_ids');
  const list = [...new Set(ids.data.split(',').filter(Boolean))].slice(0, 100);
  if (!list.length) return c.json({ prices: [] });
  const placeholders = list.map(() => '?').join(',');
  const { results } = await c.env.DB.prepare(
    `SELECT id, retail_agorot AS price_agorot, compare_at_agorot, price_provisional, visible FROM products WHERE id IN (${placeholders})`,
  )
    .bind(...list)
    .all<{ id: string; price_agorot: number | null; compare_at_agorot: number | null; price_provisional: number; visible: number }>();
  c.header('Cache-Control', 'public, max-age=60');
  return c.json({
    prices: results.map((r) => ({
      id: r.id,
      price_agorot: r.visible ? r.price_agorot : null,
      compare_at_agorot: r.visible ? r.compare_at_agorot : null,
      price_provisional: r.price_provisional === 1,
      available: r.visible === 1 && r.price_agorot !== null,
    })),
  });
});

publicApi.get('/catalog/rooms/:room', async (c) => {
  const room = c.req.param('room');
  const r = await c.env.DB.prepare('SELECT id, name_he, style, frame, slots_version, built FROM rooms WHERE id = ?').bind(room).first();
  if (!r) throw new HttpError(404, 'room_not_found');
  const { results: slots } = await c.env.DB.prepare(
    `SELECT s.id, s.name_he, s.z, s.hotspot, s.zoom_frame,
            json_group_array(json_object('position', o.position, 'product_id', o.product_id, 'placeholder', o.placeholder, 'is_default', o.is_default)) AS options
     FROM slots s LEFT JOIN slot_options o ON o.room_id = s.room_id AND o.slot_id = s.id
     WHERE s.room_id = ? GROUP BY s.room_id, s.id ORDER BY s.z`,
  )
    .bind(room)
    .all<{ id: string; name_he: string; z: number; hotspot: string | null; zoom_frame: string | null; options: string }>();
  c.header('Cache-Control', 'public, max-age=60');
  return c.json({
    room: r,
    slots: slots.map((s) => ({
      ...s,
      hotspot: s.hotspot ? JSON.parse(s.hotspot) : null,
      zoom_frame: s.zoom_frame ? JSON.parse(s.zoom_frame) : null,
      options: JSON.parse(s.options),
    })),
  });
});

// ---------- cart ----------
publicApi.post('/cart', async (c) => {
  await rateLimit(c.env.RL_WRITE, `cart:${clientKey(c)}`);
  const id = randomToken(24);
  await createCart(c.env.DB, id);
  return c.json(await readCart(c.env.DB, id), 201);
});

publicApi.get('/cart/:id', async (c) => {
  const id = c.req.param('id');
  await openCartOr404(c.env.DB, id);
  return c.json(await readCart(c.env.DB, id));
});

publicApi.put('/cart/:id/items', async (c) => {
  await rateLimit(c.env.RL_WRITE, `cart:${clientKey(c)}`);
  const id = c.req.param('id');
  await openCartOr404(c.env.DB, id);
  const body = await readJson(c, CartItemInputSchema);
  await setCartItem(c.env.DB, id, body.variant_id, body.qty);
  return c.json(await readCart(c.env.DB, id));
});

// ---------- checkout ----------
publicApi.post('/checkout', async (c) => {
  await rateLimit(c.env.RL_CHECKOUT, `checkout:${clientKey(c)}`);
  const req = await readJson(c, CheckoutRequestSchema);
  await openCartOr404(c.env.DB, req.cart_id);
  const cart = await readCart(c.env.DB, req.cart_id);
  if (!cart.lines.length) throw new HttpError(409, 'cart_empty', 'הסל ריק.');

  const ship = (await shippingOptions(c.env.DB)).find((s) => s.id === req.shipping_method);
  if (!ship) throw new HttpError(422, 'shipping_unavailable');
  const econ = await economics(c.env.DB);
  const subtotal = cart.subtotal_agorot;
  // price from D1 settings, never from the client: economy is free at or above the threshold
  const shippingAgorot = customerShippingAgorot(req.shipping_method, subtotal, {
    shipping_fee_economy_ils: econ.shipping_fee_economy_agorot / 100,
    shipping_fee_express_ils: econ.shipping_fee_express_agorot / 100,
    free_shipping_threshold_ils: econ.free_shipping_threshold_agorot === null ? null : econ.free_shipping_threshold_agorot / 100,
  });
  const total = subtotal + shippingAgorot;
  const vat = total - Math.round(total / (1 + econ.vat_rate));
  const now = nowIso();
  const id = orderId();
  const token = randomToken(24);
  const customerId = crypto.randomUUID();

  // cost snapshots for real per-order margin
  const { results: costs } = await c.env.DB.prepare(
    `SELECT v.id AS variant_id, p.cost_usd_cents, p.shipping_usd_cents, p.sell_qty, v.fulfillment_source, v.supplier_sku
     FROM product_variants v JOIN products p ON p.id = v.product_id
     WHERE v.id IN (${cart.lines.map(() => '?').join(',')})`,
  )
    .bind(...cart.lines.map((l) => l.variant_id))
    .all<{
      variant_id: string;
      cost_usd_cents: number;
      shipping_usd_cents: number;
      sell_qty: number;
      fulfillment_source: string;
      supplier_sku: string | null;
    }>();
  const costOf = new Map(costs.map((r) => [r.variant_id, r]));

  const provider = paymentProvider(c.env, new URL(c.req.url).origin);
  const origin = new URL(c.req.url).origin;
  const session = await provider.createSession({
    order_id: id,
    amount_agorot: total,
    description_he: `הזמנה ${id}`,
    customer: req.customer,
    return_url: `${origin}/order/${id}/`,
    cancel_url: `${origin}/checkout/?canceled=1`,
    webhook_url: `${origin}/api/webhooks/payment/${provider.id}`,
  });

  const stmts = [
    c.env.DB.prepare(
      'INSERT INTO customers (id, email, phone, full_name, marketing_consent, marketing_consent_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
    ).bind(
      customerId,
      req.customer.email,
      req.customer.phone,
      req.customer.full_name,
      req.consents.marketing ? 1 : 0,
      req.consents.marketing ? now : null,
      now,
    ),
    c.env.DB.prepare(
      `INSERT INTO orders (id, token_hash, cart_id, customer_id, status, subtotal_agorot, shipping_method, shipping_agorot, total_agorot, vat_agorot, vat_rate, fx_usd_ils_at_order, address_json, terms_accepted_at, payment_provider, payment_session_id, created_at, updated_at)
       VALUES (?, ?, ?, ?, 'pending_payment', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    ).bind(
      id,
      await sha256Hex(token),
      req.cart_id,
      customerId,
      subtotal,
      req.shipping_method,
      shippingAgorot,
      total,
      vat,
      econ.vat_rate,
      econ.fx_usd_ils,
      JSON.stringify(req.address),
      now,
      provider.id,
      session.session_id,
      now,
      now,
    ),
    ...cart.lines.map((l, i) => {
      const cost = costOf.get(l.variant_id);
      return c.env.DB.prepare(
        `INSERT INTO order_items (order_id, line, product_id, variant_id, name_he, qty, unit_price_agorot, unit_cost_usd_cents, unit_shipping_usd_cents, unit_sell_qty, fulfillment_source, supplier_sku)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      ).bind(
        id,
        i + 1,
        l.product_id,
        l.variant_id,
        l.name_he,
        l.qty,
        l.unit_price_agorot,
        cost?.cost_usd_cents ?? 0,
        cost?.shipping_usd_cents ?? 0,
        cost?.sell_qty ?? 1,
        cost?.fulfillment_source ?? 'dropship_cj',
        cost?.supplier_sku ?? null,
      );
    }),
    c.env.DB.prepare("UPDATE carts SET status = 'converted', updated_at = ? WHERE id = ?").bind(now, req.cart_id),
    c.env.DB.prepare('INSERT INTO audit_log (at, actor, action, subject, detail) VALUES (?, ?, ?, ?, ?)').bind(
      now,
      'system',
      'order.created',
      id,
      JSON.stringify({ total, provider: provider.id }),
    ),
  ];
  await c.env.DB.batch(stmts);

  const res: CheckoutResponse = { order_id: id, order_token: token, redirect_url: session.redirect_url };
  return c.json(res, 201);
});

// ---------- order status (buyer) ----------
publicApi.get('/orders/:id', async (c) => {
  const id = c.req.param('id');
  const token = c.req.header('x-order-token') ?? '';
  if (!/^HD-[A-Z0-9]{8}$/.test(id) || token.length < 16) throw new HttpError(404, 'order_not_found');
  const o = await c.env.DB.prepare('SELECT id, token_hash, status, created_at, total_agorot, shipping_method FROM orders WHERE id = ?')
    .bind(id)
    .first<{ id: string; token_hash: string; status: OrderStatus; created_at: string; total_agorot: number; shipping_method: 'economy' | 'express' }>();
  if (!o || !timingSafeEqualHex(o.token_hash, await sha256Hex(token))) throw new HttpError(404, 'order_not_found');
  const { results } = await c.env.DB.prepare('SELECT name_he, qty, unit_price_agorot FROM order_items WHERE order_id = ? ORDER BY line')
    .bind(id)
    .all<{ name_he: string; qty: number; unit_price_agorot: number }>();
  const view: OrderView = {
    id: o.id,
    status: o.status,
    status_he: ORDER_STATUS_HE[o.status],
    created_at: o.created_at,
    total_agorot: o.total_agorot,
    shipping_method: o.shipping_method,
    lines: results.map((r) => ({ name_he: r.name_he, qty: r.qty, line_total_agorot: r.qty * r.unit_price_agorot })),
  };
  return c.json(view);
});
