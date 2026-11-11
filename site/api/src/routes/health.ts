/**
 * S13 (launch checklist 6.2): `/healthz` for the external uptime clock (an owner step, docs/ops/deploy-runbook.md).
 *
 * - **What it checks:** D1 answers a read; the queue binding is there, and the queue is draining: no paid order has
 *   waited more than 30 minutes with its supplier shipment still queued or being sent (the consumer would have taken it).
 * - **S16, QA ת39, the supplier:** `degraded` when a paid order has been failing at the supplier for more than 30 minutes
 *   (its shipment's run of failed sends started before then: `failing_since`, migration 0007), or is in supplier_error
 *   from before S16 without that time. Why 30: the queue retries a failed send after 1, 2, 4, 8 and 10 minutes (index.ts:
 *   min(600 s, 30 s × 2^attempt), `max_retries` 5), so its sixth and last delivery is about 25 minutes after the first
 *   failure. A failure the retries can still fix alerts nobody; one that outlived every retry does, within 5 minutes.
 * - **What it says:** `ok` and one word per check, nothing else: no environment, version, provider, count, time or error
 *   text. 200 when every check is ok, 503 otherwise, never cached.
 */
import { Hono } from 'hono';
import type { AppEnv } from '../env';
import { log } from '../lib/log';

export const health = new Hono<AppEnv>();

/** how long a paid order's shipment may wait in the queue before the queue is called stalled */
export const QUEUE_STALL_MS = 30 * 60_000;
/** S16 (ת39): how long a paid order may fail at the supplier before the supplier check says `degraded` */
export const SUPPLIER_FAILING_MS = 30 * 60_000;

health.get('/', async (c) => {
  let db: 'ok' | 'fail' = 'ok';
  let queue: 'ok' | 'stalled' | 'fail' = c.env.SUPPLIER_QUEUE && typeof c.env.SUPPLIER_QUEUE.send === 'function' ? 'ok' : 'fail';
  let supplier: 'ok' | 'degraded' | 'fail' = 'ok';
  try {
    await c.env.DB.prepare('SELECT 1 AS ok').first();
    const cutoff = new Date(Date.now() - QUEUE_STALL_MS).toISOString();
    const stalled = await c.env.DB.prepare(
      `SELECT 1 AS y FROM supplier_shipments s JOIN orders o ON o.id = s.order_id
       WHERE s.status IN ('queued', 'submitting') AND s.fulfillment_source = 'dropship_cj' AND o.status = 'paid' AND o.paid_at < ? AND s.last_error IS NULL LIMIT 1`,
    )
      .bind(cutoff)
      .first();
    if (stalled && queue === 'ok') queue = 'stalled';
    const failing = await c.env.DB.prepare(
      `SELECT 1 AS y FROM supplier_shipments s JOIN orders o ON o.id = s.order_id
       WHERE o.paid_at IS NOT NULL AND o.status IN ('paid', 'supplier_error') AND s.status IN ('queued', 'failed')
         AND (s.failing_since < ? OR (s.failing_since IS NULL AND o.status = 'supplier_error')) LIMIT 1`,
    )
      .bind(new Date(Date.now() - SUPPLIER_FAILING_MS).toISOString())
      .first();
    if (failing) supplier = 'degraded';
  } catch (err) {
    db = 'fail';
    supplier = 'fail';
    log.error('healthz.db_failed', {}, err);
  }
  const ok = db === 'ok' && queue === 'ok' && supplier === 'ok';
  if (!ok) log.warn('healthz.not_ok', { db, queue, supplier });
  return c.json({ ok, checks: { db, queue, supplier } }, ok ? 200 : 503, { 'cache-control': 'no-store' });
});
