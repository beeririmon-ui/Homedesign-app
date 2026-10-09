/**
 * Queue consumer: paid order → supplier order (CJ in production, mock elsewhere). Idempotent per (order, supplier).
 * Only dropship lines go to CJ (qty × sell_qty supplier units). Lines with fulfillment_source = il_3pl get their own
 * supplier_shipments row at payment time and are handled by the 3PL adapter once one is chosen (decision E1).
 */
import type { Env, SupplierJob } from '../env';
import { nowIso } from './http';
import { supplierClient } from './suppliers';

export async function processSupplierJob(env: Env, job: SupplierJob, attempt: number): Promise<'submitted' | 'skipped' | 'retry'> {
  const client = supplierClient(env);
  const order = await env.DB.prepare('SELECT id, status, shipping_method, address_json, customer_id FROM orders WHERE id = ?')
    .bind(job.order_id)
    .first<{ id: string; status: string; shipping_method: 'economy' | 'express'; address_json: string; customer_id: string }>();
  if (!order || order.status !== 'paid') return 'skipped';
  const existing = await env.DB.prepare('SELECT status FROM supplier_shipments WHERE order_id = ? AND supplier = ?')
    .bind(order.id, client.id)
    .first<{ status: string }>();
  if (existing && existing.status !== 'queued' && existing.status !== 'failed') return 'skipped';
  const customer = await env.DB.prepare('SELECT full_name, phone, email FROM customers WHERE id = ?')
    .bind(order.customer_id)
    .first<{ full_name: string; phone: string; email: string }>();
  const { results: items } = await env.DB.prepare(
    "SELECT product_id, qty * unit_sell_qty AS qty, supplier_sku FROM order_items WHERE order_id = ? AND fulfillment_source = 'dropship_cj' ORDER BY line",
  )
    .bind(order.id)
    .all<{ product_id: string; qty: number; supplier_sku: string | null }>();
  const now = nowIso();
  const input = {
    order_id: order.id,
    lines: items.map((i) => ({ supplier_sku: i.supplier_sku, product_id: i.product_id, qty: i.qty })),
    ship_to: { ...customer!, ...(JSON.parse(order.address_json) as { city: string; street: string; house: string; apartment: string; zip: string }) },
    shipping_method: order.shipping_method,
  };
  try {
    const res = await client.submitOrder(input);
    await env.DB.batch([
      env.DB.prepare(
        `INSERT INTO supplier_shipments (id, order_id, supplier, status, supplier_order_id, attempts, request_json, response_json, created_at, updated_at)
         VALUES (?, ?, ?, 'submitted', ?, ?, ?, ?, ?, ?)
         ON CONFLICT(order_id, supplier) DO UPDATE SET status = 'submitted', supplier_order_id = excluded.supplier_order_id, attempts = excluded.attempts, response_json = excluded.response_json, last_error = NULL, updated_at = excluded.updated_at`,
      ).bind(
        crypto.randomUUID(),
        order.id,
        client.id,
        res.supplier_order_id,
        attempt,
        JSON.stringify({ lines: input.lines.length, shipping_method: input.shipping_method }),
        JSON.stringify(res.raw),
        now,
        now,
      ),
      env.DB.prepare("UPDATE orders SET status = 'sent_to_supplier', updated_at = ? WHERE id = ? AND status = 'paid'").bind(now, order.id),
      env.DB.prepare('INSERT INTO audit_log (at, actor, action, subject, detail) VALUES (?, ?, ?, ?, ?)').bind(
        now,
        'queue',
        'supplier.submitted',
        order.id,
        res.supplier_order_id,
      ),
    ]);
    return 'submitted';
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    await env.DB.prepare(
      `INSERT INTO supplier_shipments (id, order_id, supplier, status, attempts, last_error, created_at, updated_at) VALUES (?, ?, ?, 'failed', ?, ?, ?, ?)
       ON CONFLICT(order_id, supplier) DO UPDATE SET status = 'failed', attempts = excluded.attempts, last_error = excluded.last_error, updated_at = excluded.updated_at`,
    )
      .bind(crypto.randomUUID(), order.id, client.id, attempt, msg.slice(0, 500), now, now)
      .run();
    if (attempt >= 5) await env.DB.prepare("UPDATE orders SET status = 'supplier_error', updated_at = ? WHERE id = ?").bind(now, order.id).run();
    return 'retry';
  }
}
