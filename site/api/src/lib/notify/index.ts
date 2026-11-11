/**
 * S13 (launch checklist 6.3): the new-order alert to the shop's owner. An interface only: the channel (email or
 * Telegram) is the owner's decision, so none is built (NOTIFY_PROVIDER has no real provider yet, lib/config.ts).
 *
 * - **The mock** writes the alert as a log row (development, tests, preview). Production carries `UNDECIDED`: the alert
 *   is skipped with a warning row, and the order is never held up by it.
 * - **What it says:** the order number, the total, how many items, and the link to the order in the admin. No name,
 *   email, phone or address: the alert travels through a third party, and the admin behind Access has the rest.
 * - **Once per order:** claimed in `notifications` before it is sent (a retry after a failure sends it again; a
 *   duplicate job does not).
 */
import { providerOf } from '../config';
import { log } from '../log';

export type NewOrderAlert = { order_id: string; total_agorot: number; items: number; admin_path: string; paid_at: string };

export interface Notifier {
  readonly id: string;
  notify(alert: NewOrderAlert): Promise<void>;
}

/** Development, tests and preview: the alert is a log row (Workers Logs), nothing is sent anywhere. */
export const mockNotifier: Notifier = {
  id: 'mock',
  async notify(alert) {
    log.info('notify.new_order', { channel: 'mock', ...alert });
  },
};

export type NotifierChoice = { ok: true; notifier: Notifier } | { ok: false; reason: string };

export function notifier(env: { ENVIRONMENT?: string; NOTIFY_PROVIDER?: string }): NotifierChoice {
  const c = providerOf(env, 'NOTIFY_PROVIDER');
  if (!c.ok) return c;
  if (c.mock) return { ok: true, notifier: mockNotifier };
  return { ok: false, reason: `notify provider "${c.id}" is not built yet` };
}

/** how many times a failing alert is tried before it is given up (loudly): an alert never blocks an order */
export const NOTIFY_MAX_ATTEMPTS = 3;

export async function processNotifyJob(
  env: { DB: D1Database; ENVIRONMENT?: string; NOTIFY_PROVIDER?: string },
  orderId: string,
  attempt: number,
  given?: Notifier,
): Promise<'sent' | 'skipped' | 'retry'> {
  let n = given;
  if (!n) {
    const c = notifier(env);
    if (!c.ok) {
      log.warn('notify.skipped', { order_id: orderId, reason: c.reason });
      return 'skipped';
    }
    n = c.notifier;
  }
  const o = await env.DB.prepare(
    'SELECT o.id, o.total_agorot, o.paid_at, (SELECT COALESCE(SUM(qty), 0) FROM order_items WHERE order_id = o.id) AS items FROM orders o WHERE o.id = ? AND o.paid_at IS NOT NULL',
  )
    .bind(orderId)
    .first<{ id: string; total_agorot: number; paid_at: string; items: number }>();
  if (!o) return 'skipped';
  const at = new Date().toISOString();
  const claim = await env.DB.prepare(
    `INSERT INTO notifications (kind, order_id, state, provider, attempts, claimed_at) VALUES ('new_order', ?, 'claimed', ?, 1, ?)
     ON CONFLICT(kind, order_id) DO UPDATE SET state = 'claimed', attempts = attempts + 1, claimed_at = excluded.claimed_at WHERE notifications.state = 'failed'`,
  )
    .bind(orderId, n.id, at)
    .run();
  if (!claim.meta.changes) return 'skipped'; // sent, or another run holds it
  try {
    await n.notify({ order_id: o.id, total_agorot: o.total_agorot, items: o.items, admin_path: `/admin/orders/${o.id}`, paid_at: o.paid_at });
  } catch (err) {
    await env.DB.prepare("UPDATE notifications SET state = 'failed', last_error = ? WHERE kind = 'new_order' AND order_id = ?")
      .bind((err instanceof Error ? err.message : String(err)).slice(0, 300), orderId)
      .run();
    log.error('notify.failed', { order_id: orderId, provider: n.id, attempt }, err);
    return attempt >= NOTIFY_MAX_ATTEMPTS ? 'skipped' : 'retry';
  }
  await env.DB.prepare("UPDATE notifications SET state = 'sent', sent_at = ?, last_error = NULL WHERE kind = 'new_order' AND order_id = ?")
    .bind(new Date().toISOString(), orderId)
    .run();
  return 'sent';
}
