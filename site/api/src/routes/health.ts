/**
 * S13 (launch checklist 6.2): `/healthz` for the external uptime clock (an owner step, docs/ops/deploy-runbook.md).
 *
 * - **What it checks:** D1 answers a read; the queue binding is there, and the queue is draining: no paid order has
 *   waited more than 30 minutes with its supplier shipment still queued or being sent (the consumer would have taken it).
 * - **What it says:** `ok` and one word per check, nothing else: no environment, version, provider, count, time or error
 *   text. 200 when every check is ok, 503 otherwise, never cached.
 */
import { Hono } from 'hono';
import type { AppEnv } from '../env';
import { log } from '../lib/log';

export const health = new Hono<AppEnv>();

/** how long a paid order's shipment may wait in the queue before the queue is called stalled */
export const QUEUE_STALL_MS = 30 * 60_000;

health.get('/', async (c) => {
  let db: 'ok' | 'fail' = 'ok';
  let queue: 'ok' | 'stalled' | 'fail' = c.env.SUPPLIER_QUEUE && typeof c.env.SUPPLIER_QUEUE.send === 'function' ? 'ok' : 'fail';
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
  } catch (err) {
    db = 'fail';
    log.error('healthz.db_failed', {}, err);
  }
  const ok = db === 'ok' && queue === 'ok';
  if (!ok) log.warn('healthz.not_ok', { db, queue });
  return c.json({ ok, checks: { db, queue } }, ok ? 200 : 503, { 'cache-control': 'no-store' });
});
