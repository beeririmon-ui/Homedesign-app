import type { Env, SupplierJob } from './env';
import { app } from './app';
import { processSupplierJob } from './lib/fulfillment';

export default {
  fetch: app.fetch,
  async queue(batch: MessageBatch<SupplierJob>, env: Env): Promise<void> {
    for (const msg of batch.messages) {
      const result = await processSupplierJob(env, msg.body, msg.attempts);
      if (result === 'retry') msg.retry({ delaySeconds: Math.min(600, 30 * 2 ** msg.attempts) });
      else msg.ack();
    }
  },
} satisfies ExportedHandler<Env, SupplierJob>;
