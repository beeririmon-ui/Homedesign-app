/**
 * Admin API, read-only in this phase. Behind Cloudflare Access (see lib/access.ts) and re-verified here.
 * This is the API the studio will call instead of its patch layer (docs/architecture.md, "Admin API").
 */
import { Hono } from 'hono';
import { z } from 'zod';
import type { AppEnv } from '../env';
import { HttpError } from '../lib/http';
import { devBypassAllowed, verifyAccessJwt } from '../lib/access';
import { economics } from '../lib/store';

export const admin = new Hono<AppEnv>();

admin.use('*', async (c, next) => {
  if (devBypassAllowed(c.env)) {
    c.set('actor', 'dev-bypass');
    return next();
  }
  const token = c.req.header('cf-access-jwt-assertion');
  if (!token || !c.env.ACCESS_TEAM_DOMAIN || !c.env.ACCESS_AUD) throw new HttpError(403, 'forbidden');
  const v = await verifyAccessJwt(token, { domain: c.env.ACCESS_TEAM_DOMAIN, aud: c.env.ACCESS_AUD, nowSec: Math.floor(Date.now() / 1000) });
  if (!v.ok) throw new HttpError(403, 'forbidden');
  c.set('actor', v.email);
  return next();
});

admin.get('/overview', async (c) => {
  const [byStatus, meta, settings, counts] = await Promise.all([
    c.env.DB.prepare('SELECT status, COUNT(*) AS n, SUM(total_agorot) AS total_agorot FROM orders GROUP BY status').all(),
    c.env.DB.prepare('SELECT key, value FROM catalog_meta').all<{ key: string; value: string }>(),
    economics(c.env.DB),
    c.env.DB.prepare(
      'SELECT COUNT(*) AS products, SUM(visible) AS visible, SUM(price_provisional) AS provisional, SUM(shipping_from_default) AS shipping_defaulted FROM products',
    ).first(),
  ]);
  const m = Object.fromEntries(
    meta.results.map((r) => [r.key, r.key.endsWith('_options') || r.key.endsWith('_products') || r.key.endsWith('_cards') ? JSON.parse(r.value) : r.value]),
  );
  return c.json({
    actor: c.get('actor'),
    orders_by_status: byStatus.results,
    catalog: m,
    economics: { ...settings, defaults_used: JSON.parse(settings.defaults_used) },
    products: counts,
  });
});

const ListQuery = z.object({
  status: z
    .string()
    .regex(/^[a-z_]{1,32}$/)
    .optional(),
  limit: z.coerce.number().int().min(1).max(200).default(50),
});

admin.get('/orders', async (c) => {
  const q = ListQuery.safeParse(c.req.query());
  if (!q.success) throw new HttpError(400, 'invalid_query');
  const where = q.data.status ? 'WHERE o.status = ?' : '';
  const stmt = c.env.DB.prepare(
    `SELECT o.id, o.status, o.total_agorot, o.shipping_method, o.payment_provider, o.created_at, o.paid_at, c.full_name, c.email
     FROM orders o JOIN customers c ON c.id = o.customer_id ${where} ORDER BY o.created_at DESC LIMIT ?`,
  );
  const { results } = await (q.data.status ? stmt.bind(q.data.status, q.data.limit) : stmt.bind(q.data.limit)).all();
  return c.json({ orders: results });
});

admin.get('/orders/:id', async (c) => {
  const id = c.req.param('id');
  const order = await c.env.DB.prepare(
    'SELECT o.*, c.full_name, c.email, c.phone, c.marketing_consent FROM orders o JOIN customers c ON c.id = o.customer_id WHERE o.id = ?',
  )
    .bind(id)
    .first<Record<string, unknown>>();
  if (!order) throw new HttpError(404, 'order_not_found');
  delete order.token_hash;
  const [items, payments, supplier] = await Promise.all([
    c.env.DB.prepare('SELECT * FROM order_items WHERE order_id = ? ORDER BY line').bind(id).all<{
      qty: number;
      unit_price_agorot: number;
      unit_cost_usd_cents: number;
      unit_shipping_usd_cents: number;
    }>(),
    c.env.DB.prepare(
      'SELECT provider, provider_event_id, type, amount_agorot, received_at, outcome FROM payment_events WHERE order_id = ? ORDER BY received_at',
    )
      .bind(id)
      .all(),
    c.env.DB.prepare('SELECT * FROM supplier_shipments WHERE order_id = ?').bind(id).all(),
  ]);
  const fx = order.fx_usd_ils_at_order as number;
  const cogs = items.results.reduce((s, i) => s + Math.round((i.unit_cost_usd_cents + i.unit_shipping_usd_cents) * fx) * i.qty, 0);
  const net = (order.total_agorot as number) - (order.vat_agorot as number);
  return c.json({
    order: { ...order, address: JSON.parse(order.address_json as string), address_json: undefined },
    items: items.results,
    payments: payments.results,
    supplier_shipments: supplier.results,
    margin: { net_agorot: net, cogs_agorot: cogs, gross_profit_agorot: net - cogs, note: 'before payment fees, returns reserve and CAC' },
  });
});

admin.get('/products', async (c) => {
  const { results } = await c.env.DB.prepare(
    `SELECT e.*, p.supplier_name, p.supplier_url, p.supplier_sku, p.source_path,
            (SELECT group_concat(DISTINCT v.fulfillment_source) FROM product_variants v WHERE v.product_id = p.id AND v.active = 1) AS fulfillment_sources
     FROM v_product_economics e JOIN products p ON p.id = e.id
     ORDER BY e.slot_id, e.id`,
  ).all();
  return c.json({ products: results });
});

admin.get('/supplier-shipments', async (c) => {
  const { results } = await c.env.DB.prepare('SELECT * FROM supplier_shipments ORDER BY updated_at DESC LIMIT 200').all();
  return c.json({ supplier_shipments: results });
});

admin.get('/economics', async (c) => {
  const s = await economics(c.env.DB);
  return c.json({ ...s, defaults_used: JSON.parse(s.defaults_used) });
});
