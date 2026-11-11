import type { Env, SupplierJob } from './env';
import { app } from './app';
import { processSupplierJob } from './lib/fulfillment';
import { log } from './lib/log';
import { supplierClient } from './lib/suppliers';
import { syncShipments } from './lib/shipments';

export default {
  fetch: app.fetch,
  /**
   * S12, ת19: each message on its own. A message that throws is retried alone (and reaches the DLQ after its own
   * retries), loudly; the messages after it in the batch are processed as usual. S13: the row is structured, no PII.
   */
  async queue(batch: MessageBatch<SupplierJob>, env: Env): Promise<void> {
    for (const msg of batch.messages) {
      let result: Awaited<ReturnType<typeof processSupplierJob>>;
      try {
        result = await processSupplierJob(env, msg.body, msg.attempts);
      } catch (err) {
        log.error('queue.job_failed', { kind: msg.body?.kind ?? 'message', order_id: msg.body?.order_id ?? null, attempt: msg.attempts }, err);
        result = 'retry';
      }
      if (result === 'retry') msg.retry({ delaySeconds: Math.min(600, 30 * 2 ** msg.attempts) });
      else msg.ack();
    }
  },
  /**
   * S13 (3.3): the cron (wrangler.jsonc `triggers`) asks the configured supplier about the shipments it holds, when its
   * client has a tracking call (CJ's is not in the repo's documentation yet, and the mock never reports on its own).
   */
  async scheduled(_controller: ScheduledController, env: Env): Promise<void> {
    const c = supplierClient(env);
    if (!c.ok || !c.client.tracking) return;
    const r = await syncShipments(env, c.client);
    if (r.asked) log.info('shipment.sync', { supplier: c.client.id, ...r });
  },
} satisfies ExportedHandler<Env, SupplierJob>;
