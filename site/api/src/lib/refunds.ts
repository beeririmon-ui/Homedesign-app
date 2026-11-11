/**
 * S13 (launch checklist 2.5): refunds, full or partial, through the provider that took the payment; idempotent like the
 * S12 invoices, and never more than what the order paid.
 *
 * - **The key:** every refund has an id that is its idempotency key (the admin's form carries a fresh one, so a double
 *   click or a resent form is the same refund; a cancellation uses `cancel:<order>`). The same key again returns the first
 *   refund, never a second one; the key is passed on to the provider.
 * - **Never more than paid:** the refund is claimed by one statement that inserts its row only when the order is paid and
 *   the refunds that count (every state but `refused`) plus this one stay within the paid amount. D1 runs one statement
 *   at a time, so two refunds at once can never both pass the check. The provider is told the same numbers, and refuses
 *   too (the mock does).
 * - **After the call:** refunded, the row says so, the order becomes `refunded` once all of it is (a canceled order stays
 *   canceled), the audit log names who asked, and the credit note is queued (lib/invoices `processCreditNoteJob`). A
 *   refusal frees the amount. A failure that may have moved money keeps the claim: the same key again asks again, and a
 *   provider that can neither deduplicate nor be asked leaves it `unresolved` for a person, never a second refund.
 */
import type { Env } from '../env';
import { formatIls } from '@hd/shared/money';
import { INVOICE_LEASE_MS } from './invoices';
import { refundProvider } from './payments';
import { RefundRefused, type IssuedRefund, type PaymentProvider } from './payments/types';
import { log } from './log';

export type RefundRequest = {
  orderId: string;
  /** agorot, or what is left of the payment */
  amount: number | 'rest';
  reason: string;
  /** the idempotency key: 8–80 characters of [A-Za-z0-9:_-] */
  key: string;
  /** who asked: the Access email, `system`, … */
  actor: string;
};
export type RefundResult =
  | { ok: true; refund_id: string; amount_agorot: number; duplicate: boolean }
  | { ok: false; status: 404 | 409 | 422 | 502 | 503; code: string; message_he: string; refund_id?: string };

export const REFUND_KEY = /^[A-Za-z0-9:_-]{8,80}$/;

type OrderRow = { id: string; total_agorot: number; paid_at: string | null; payment_provider: string; payment_session_id: string | null; status: string };
type RefundRow = { id: string; order_id: string; amount_agorot: number; state: string; claimed_at: string; provider_refund_id: string | null };

/** What the order paid, what the refunds that count hold, and what is refunded for real. */
export async function refundTotals(db: D1Database, orderId: string): Promise<{ paid: number; counted: number; refunded: number }> {
  const r = await db
    .prepare(
      `SELECT CASE WHEN o.paid_at IS NULL THEN 0 ELSE o.total_agorot END AS paid,
              (SELECT COALESCE(SUM(amount_agorot), 0) FROM refunds WHERE order_id = o.id AND state != 'refused') AS counted,
              (SELECT COALESCE(SUM(amount_agorot), 0) FROM refunds WHERE order_id = o.id AND state = 'refunded') AS refunded
       FROM orders o WHERE o.id = ?`,
    )
    .bind(orderId)
    .first<{ paid: number; counted: number; refunded: number }>();
  return r ?? { paid: 0, counted: 0, refunded: 0 };
}

const fail = (status: 404 | 409 | 422 | 502 | 503, code: string, message_he: string, refund_id?: string): RefundResult => ({
  ok: false,
  status,
  code,
  message_he,
  ...(refund_id ? { refund_id } : {}),
});

export async function requestRefund(env: Env, req: RefundRequest, opts: { provider?: PaymentProvider; now?: () => number } = {}): Promise<RefundResult> {
  const now = opts.now ?? Date.now;
  const iso = () => new Date(now()).toISOString();
  if (!REFUND_KEY.test(req.key)) return fail(422, 'invalid_key', 'מפתח ההחזר לא תקין. רעננו את הדף ונסו שוב.');
  const order = await env.DB.prepare('SELECT id, total_agorot, paid_at, payment_provider, payment_session_id, status FROM orders WHERE id = ?')
    .bind(req.orderId)
    .first<OrderRow>();
  if (!order) return fail(404, 'order_not_found', 'ההזמנה לא נמצאה.');
  if (!order.paid_at) return fail(409, 'not_paid', 'ההזמנה לא שולמה, ואין מה להחזיר.');

  // the same key again: the first refund, never a second one
  const existing = await env.DB.prepare('SELECT id, order_id, amount_agorot, state, claimed_at, provider_refund_id FROM refunds WHERE id = ?')
    .bind(req.key)
    .first<RefundRow>();
  if (existing) return resume(existing);

  const totals = await refundTotals(env.DB, order.id);
  const left = totals.paid - totals.counted;
  const amount = req.amount === 'rest' ? left : req.amount;
  if (!Number.isInteger(amount) || amount <= 0)
    return req.amount === 'rest' ? fail(409, 'nothing_left', 'כל הסכום כבר הוחזר.') : fail(422, 'invalid_amount', 'הסכום לא תקין.');
  if (amount > left) return fail(422, 'exceeds_paid', `ההחזר גבוה ממה שנשאר להחזיר: נשארו ${formatIls(Math.max(0, left))}.`);

  const provider = opts.provider ?? pick();
  if (!provider) return fail(503, 'provider_unavailable', 'אי אפשר להחזיר דרך הסולק כרגע: ההחזר נעשה ביד אצל הסולק, ונרשם כאן אחר כך.');
  const kind = totals.counted + amount === totals.paid ? 'full' : 'partial';
  const at = iso();
  // the claim: inserted only while the refunds that count, with this one, stay within what the order paid
  const claim = await env.DB.prepare(
    `INSERT INTO refunds (id, order_id, kind, amount_agorot, reason, state, provider, requested_by, claimed_at)
     SELECT ?, o.id, ?, ?, ?, 'claimed', ?, ?, ? FROM orders o
     WHERE o.id = ? AND o.paid_at IS NOT NULL
       AND (SELECT COALESCE(SUM(amount_agorot), 0) FROM refunds WHERE order_id = o.id AND state != 'refused') + ? <= o.total_agorot
     ON CONFLICT(id) DO NOTHING`,
  )
    .bind(req.key, kind, amount, req.reason.slice(0, 300), provider.id, req.actor.slice(0, 200), at, order.id, amount)
    .run();
  if (!claim.meta.changes) {
    const raced = await env.DB.prepare('SELECT id, order_id, amount_agorot, state, claimed_at, provider_refund_id FROM refunds WHERE id = ?')
      .bind(req.key)
      .first<RefundRow>();
    if (raced) return resume(raced);
    const t = await refundTotals(env.DB, order.id);
    return fail(422, 'exceeds_paid', `ההחזר גבוה ממה שנשאר להחזיר: נשארו ${formatIls(Math.max(0, t.paid - t.counted))}.`);
  }
  await audit(env.DB, req.actor, 'refund.requested', order.id, { refund: req.key, amount_agorot: amount, kind, reason: req.reason.slice(0, 300) }, at);
  return call(provider, { id: req.key, order_id: order.id, amount_agorot: amount, state: 'claimed', claimed_at: at, provider_refund_id: null });

  function pick(): PaymentProvider | null {
    const c = refundProvider(env, order!.payment_provider);
    if (!c.ok) log.warn('refund.provider_unavailable', { order_id: order!.id, reason: c.reason });
    return c.ok ? c.provider : null;
  }

  async function resume(row: RefundRow): Promise<RefundResult> {
    if (row.order_id !== req.orderId || (req.amount !== 'rest' && row.amount_agorot !== req.amount))
      return fail(409, 'key_reused', 'המפתח הזה כבר שימש להחזר אחר. רעננו את הדף ונסו שוב.');
    if (row.state === 'refunded') return { ok: true, refund_id: row.id, amount_agorot: row.amount_agorot, duplicate: true };
    if (row.state === 'refused') return fail(422, 'refused', 'הסולק סירב להחזר הזה. רעננו את הדף כדי לנסות החזר חדש.', row.id);
    if (row.state === 'unresolved') return fail(409, 'unresolved', 'ההחזר הזה מחכה לבדיקה של אדם אצל הסולק.', row.id);
    const provider = opts.provider ?? pick();
    if (!provider) return fail(503, 'provider_unavailable', 'אי אפשר להחזיר דרך הסולק כרגע.', row.id);
    if (!provider.refundsIdempotent) {
      // a provider that does not deduplicate is asked first, or a person checks it: never a blind second call
      const found = provider.findRefund ? await provider.findRefund(row.id) : null;
      if (found) return record(row, provider.id, found);
      if (!provider.findRefund) {
        if (now() - Date.parse(row.claimed_at) < INVOICE_LEASE_MS) return fail(409, 'in_progress', 'ההחזר הזה כבר בדרך לסולק.', row.id);
        const reason = `a refund claim of ${row.claimed_at} has no result, and ${provider.id} can neither be asked nor deduplicates: a person checks the provider`;
        await env.DB.prepare("UPDATE refunds SET state = 'unresolved', last_error = ? WHERE id = ? AND state = 'claimed'").bind(reason, row.id).run();
        await audit(env.DB, `payment:${provider.id}`, 'refund.unresolved', row.order_id, { refund: row.id }, iso());
        log.error('refund.unresolved', { order_id: row.order_id, refund_id: row.id });
        return fail(409, 'unresolved', 'ההחזר הזה מחכה לבדיקה של אדם אצל הסולק.', row.id);
      }
    }
    await env.DB.prepare('UPDATE refunds SET attempts = attempts + 1 WHERE id = ?').bind(row.id).run();
    return call(provider, row);
  }

  async function call(provider: PaymentProvider, row: RefundRow): Promise<RefundResult> {
    const before = (await refundTotals(env.DB, row.order_id)).counted - row.amount_agorot;
    let issued: IssuedRefund;
    try {
      issued = await provider.refund!(
        {
          order_id: row.order_id,
          payment_ref: order!.payment_session_id ?? '',
          amount_agorot: row.amount_agorot,
          paid_agorot: order!.total_agorot,
          refunded_before_agorot: Math.max(0, before),
          reason: req.reason.slice(0, 300),
        },
        { idempotency_key: row.id },
      );
    } catch (err) {
      const msg = (err instanceof Error ? err.message : String(err)).slice(0, 500);
      if (err instanceof RefundRefused) {
        await env.DB.batch([
          env.DB.prepare("UPDATE refunds SET state = 'refused', last_error = ?, completed_at = ? WHERE id = ? AND state = 'claimed'").bind(msg, iso(), row.id),
          auditStmt(env.DB, `payment:${provider.id}`, 'refund.refused', row.order_id, { refund: row.id, why: msg }, iso()),
        ]);
        return fail(422, 'refused', 'הסולק סירב להחזר: לא הועבר כסף.', row.id);
      }
      await env.DB.prepare('UPDATE refunds SET last_error = ? WHERE id = ?').bind(msg, row.id).run();
      const error_id = log.error('refund.provider_failed', { order_id: row.order_id, refund_id: row.id }, err);
      return fail(502, 'provider_failed', `הסולק לא ענה. ההחזר שמור, ואפשר לשלוח אותו שוב באותו מפתח (קוד ${error_id}).`, row.id);
    }
    return record(row, provider.id, issued);
  }

  async function record(row: RefundRow, providerId: string, issued: IssuedRefund): Promise<RefundResult> {
    const at = iso();
    const [done] = await env.DB.batch([
      env.DB.prepare(
        "UPDATE refunds SET state = 'refunded', provider_refund_id = ?, completed_at = ?, last_error = NULL WHERE id = ? AND state = 'claimed'",
      ).bind(issued.refund_id, at, row.id),
      // all of it refunded: the order says so (a canceled order stays canceled)
      env.DB.prepare(
        `UPDATE orders SET status = 'refunded', updated_at = ? WHERE id = ? AND status NOT IN ('canceled', 'refunded')
           AND total_agorot <= (SELECT COALESCE(SUM(amount_agorot), 0) FROM refunds WHERE order_id = ? AND state = 'refunded')`,
      ).bind(at, row.order_id, row.order_id),
      // the audit row only for the run that recorded it (the refund's completed_at is this run's)
      env.DB.prepare(
        "INSERT INTO audit_log (at, actor, action, subject, detail) SELECT ?, ?, 'refund.refunded', ?, ? WHERE EXISTS (SELECT 1 FROM refunds WHERE id = ? AND state = 'refunded' AND completed_at = ?)",
      ).bind(
        at,
        req.actor.slice(0, 200),
        row.order_id,
        JSON.stringify({ refund: row.id, amount_agorot: row.amount_agorot, provider_refund: issued.refund_id }),
        row.id,
        at,
      ),
    ]);
    if (done?.meta.changes) await env.SUPPLIER_QUEUE.send({ kind: 'credit-note', order_id: row.order_id, refund_id: row.id });
    log.info('refund.refunded', { order_id: row.order_id, refund_id: row.id, amount_agorot: row.amount_agorot, provider: providerId });
    return { ok: true, refund_id: row.id, amount_agorot: row.amount_agorot, duplicate: !done?.meta.changes };
  }
}

function auditStmt(db: D1Database, actor: string, action: string, subject: string, detail: object, at: string): D1PreparedStatement {
  return db
    .prepare('INSERT INTO audit_log (at, actor, action, subject, detail) VALUES (?, ?, ?, ?, ?)')
    .bind(at, actor.slice(0, 200), action, subject, JSON.stringify(detail));
}
async function audit(db: D1Database, actor: string, action: string, subject: string, detail: object, at: string): Promise<void> {
  await auditStmt(db, actor, action, subject, detail, at).run();
}
