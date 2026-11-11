/**
 * Admin API, behind Cloudflare Access (lib/access.ts `requireAdmin`, re-verified here). The studio and the admin screen
 * (routes/admin-ui.ts) read and act through it (docs/architecture.md, "Admin API").
 *
 * S13 (launch checklist 6.3, 2.5): the order operations. The list filters by status (or "needs a person") and searches by
 * the public order number; an order carries its tracks from the audit log; and the actions are the cancellation
 * procedure (lib/cancel.ts), refunds (lib/refunds.ts), "checked by a person" for an unresolved invoice, and, outside
 * production with the mock supplier, the supplier's answers played by a person. Every action writes the actor (the
 * Access email) to the audit log.
 */
import { Hono, type Context } from 'hono';
import { z } from 'zod';
import { ORDER_ID } from '@hd/shared';
import type { AppEnv } from '../env';
import { HttpError, readJson } from '../lib/http';
import { requireAdmin } from '../lib/access';
import { economics } from '../lib/store';
import { FILTERS, checkInvoice, listOrders, orderDetail } from '../lib/admin-orders';
import { cancelOrder } from '../lib/cancel';
import { REFUND_KEY, requestRefund } from '../lib/refunds';
import { applySupplierUpdate } from '../lib/shipments';
import { isProduction } from '../lib/config';
import type { SupplierUpdate } from '../lib/suppliers/types';

export const admin = new Hono<AppEnv>();

admin.use('*', requireAdmin);

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

export const ListQuery = z.object({
  status: z.enum(FILTERS).optional(),
  /** the public order number, or its start */
  q: z
    .string()
    .trim()
    .regex(/^\d{1,10}$/)
    .optional(),
  limit: z.coerce.number().int().min(1).max(200).default(50),
});

admin.get('/orders', async (c) => {
  const q = ListQuery.safeParse(Object.fromEntries(Object.entries(c.req.query()).filter(([, v]) => v !== '')));
  if (!q.success) throw new HttpError(400, 'invalid_query');
  return c.json({ orders: await listOrders(c.env.DB, { filter: q.data.status, search: q.data.q, limit: q.data.limit }) });
});

const orderIdOf = (c: Context<AppEnv>): string => {
  const id = c.req.param('id') ?? '';
  if (!ORDER_ID.test(id)) throw new HttpError(404, 'order_not_found');
  return id;
};

admin.get('/orders/:id', async (c) => {
  const d = await orderDetail(c.env.DB, orderIdOf(c));
  if (!d) throw new HttpError(404, 'order_not_found');
  return c.json(d);
});

const Reason = z.string().trim().min(2).max(300);
export const CancelBody = z.object({ reason: Reason });
export const RefundBody = z.object({
  /** agorot, or "rest": what is left of the payment */
  amount_agorot: z.union([z.number().int().positive().max(100_000_000), z.literal('rest')]),
  reason: Reason,
  key: z.string().regex(REFUND_KEY),
});
export const InvoiceCheckBody = z.discriminatedUnion('outcome', [
  z.object({
    outcome: z.literal('found'),
    invoice_number: z
      .string()
      .trim()
      .regex(/^[A-Za-z0-9/_-]{1,40}$/),
    note: Reason,
  }),
  z.object({ outcome: z.literal('none'), note: Reason }),
]);
export const MOCK_SUPPLIER_EVENTS = ['accepted', 'shipped', 'delivered', 'cancel_confirmed', 'cancel_refused'] as const;
export const MockSupplierBody = z.object({ event: z.enum(MOCK_SUPPLIER_EVENTS) });

/** the mock supplier's answer, as the supplier would send it */
export function mockUpdate(event: (typeof MOCK_SUPPLIER_EVENTS)[number], orderId: string): SupplierUpdate {
  switch (event) {
    case 'shipped':
      return { status: 'shipped', tracking_number: `IL${orderId.slice(-8)}TRK`, tracking_url: `https://parcelsapp.com/he/tracking/IL${orderId.slice(-8)}TRK` };
    case 'delivered':
      return { status: 'delivered' };
    case 'cancel_confirmed':
      return { status: 'canceled' };
    case 'cancel_refused':
      return { status: 'accepted', cancel: 'refused' };
    default:
      return { status: 'accepted' };
  }
}
/** the mock supplier's answers are played only outside production, with the mock supplier configured */
export const mockSupplierOpen = (env: AppEnv['Bindings']): boolean => env.SUPPLIER_PROVIDER === 'mock' && !isProduction(env);

admin.post('/orders/:id/cancel', async (c) => {
  const id = orderIdOf(c);
  const body = await readJson(c, CancelBody);
  const r = await cancelOrder(c.env, id, c.get('actor'), body.reason);
  if ('error' in r) return c.json({ error: r.code, message_he: r.message_he }, r.status);
  return c.json(r);
});

admin.post('/orders/:id/refund', async (c) => {
  const id = orderIdOf(c);
  const body = await readJson(c, RefundBody);
  const r = await requestRefund(c.env, { orderId: id, amount: body.amount_agorot, reason: body.reason, key: body.key, actor: c.get('actor') });
  if (!r.ok) return c.json({ error: r.code, message_he: r.message_he, refund_id: r.refund_id }, r.status);
  return c.json(r);
});

admin.post('/orders/:id/invoice-check', async (c) => {
  const id = orderIdOf(c);
  const body = await readJson(c, InvoiceCheckBody);
  const r = await checkInvoice(c.env, id, c.get('actor'), body);
  if (!r.ok) return c.json({ error: r.code, message_he: r.message_he }, r.status);
  return c.json(r);
});

admin.post('/orders/:id/mock-supplier', async (c) => {
  if (!mockSupplierOpen(c.env)) throw new HttpError(404, 'not_found');
  const id = orderIdOf(c);
  const body = await readJson(c, MockSupplierBody);
  const outcome = await applySupplierUpdate(c.env, {
    orderId: id,
    supplier: 'mock',
    update: mockUpdate(body.event, id),
    actor: `mock-supplier (${c.get('actor')})`,
  });
  if (outcome === 'unknown_shipment') throw new HttpError(409, 'no_mock_shipment', 'להזמנה הזו אין משלוח אצל הספק המדומה.');
  return c.json({ outcome });
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
