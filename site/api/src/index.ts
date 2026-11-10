import type { Env, SupplierJob } from './env';
import { app } from './app';
import { processSupplierJob } from './lib/fulfillment';

export default {
  fetch: app.fetch,
  /**
   * S12, ת19: each message on its own. A message that throws is retried alone (and reaches the DLQ after its own
   * retries), loudly; the messages after it in the batch are processed as usual.
   */
  async queue(batch: MessageBatch<SupplierJob>, env: Env): Promise<void> {
    for (const msg of batch.messages) {
      let result: Awaited<ReturnType<typeof processSupplierJob>>;
      try {
        result = await processSupplierJob(env, msg.body, msg.attempts);
      } catch (err) {
        console.error(`[queue] ${msg.body?.kind ?? 'message'} for order ${msg.body?.order_id ?? '?'} failed (attempt ${msg.attempts}):`, err);
        result = 'retry';
      }
      if (result === 'retry') msg.retry({ delaySeconds: Math.min(600, 30 * 2 ** msg.attempts) });
      else msg.ack();
    }
  },
} satisfies ExportedHandler<Env, SupplierJob>;
