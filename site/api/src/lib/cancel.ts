/**
 * S13 (launch checklist 6.3): the cancellation procedure. Every step is in the audit log, with who did it.
 *
 * - **Before payment** (`pending_payment`, `payment_failed`): the order is canceled; nothing was paid. A payment that
 *   still arrives for it is refunded at once (routes/payments.ts).
 * - **Before the supplier** (`paid`, nothing sent): one statement cancels the order only while no shipment is being
 *   sent or was sent; the supplier job claims a shipment only while the order is paid (lib/fulfillment.ts). D1 runs one
 *   statement at a time, so a cancellation and a submission can never both win. Then the whole payment is refunded
 *   through the payment provider (lib/refunds.ts, key `cancel:<order>`).
 * - **After the supplier** (sent, not shipped): a cancellation request to the supplier. Its answer is the status: canceled
 *   (the order is canceled and refunded), requested (the order shows "בקשת ביטול נשלחה לספק" until the supplier answers,
 *   lib/shipments.ts), or refused (the order goes on; a return after delivery is the way).
 * - **Shipped or delivered:** no cancellation; a refund, full or partial, once the item is back.
 * - **Again:** asking again resumes what is left (a cancellation whose refund did not complete), never a second refund.
 *   S16, QA ת42: a request already waiting on the supplier returns its state, without asking the supplier again.
 * - **S16, QA ת35, maybe at the supplier:** a submit that failed in a way that may have created the order (`reach =
 *   'maybe'`: a timeout, a network or server error), or any failed submit of an order in `supplier_error`, counts as
 *   sent: never a silent full refund. The supplier is asked by our order number (`findOrder`, when its client has it):
 *   it holds the order → the after-supplier path; it holds none → the before-supplier path. A supplier that cannot be
 *   asked leaves it to a person (409 `supplier_check_needed`): they check at the supplier and record what they found
 *   (`recordSupplierCheck`, the admin's "בדיקה אצל הספק"), and the cancellation then takes the matching path.
 */
import type { Env } from '../env';
import { requestRefund, refundTotals, type RefundResult } from './refunds';
import { supplierClient } from './suppliers';
import type { SupplierClient } from './suppliers/types';
import type { PaymentProvider } from './payments/types';
import { errorCode, log } from './log';
import { PROVIDER_CALL_TIMEOUT_MS, withDeadline } from './deadline';

export type CancelResult = {
  outcome: 'canceled' | 'requested' | 'refused';
  stage: 'before_payment' | 'before_supplier' | 'after_supplier' | 'after_payment_late';
  refund?: RefundResult;
  message_he: string;
};
export type CancelError = { error: true; status: 404 | 409 | 503; code: string; message_he: string };

/** shipments that are with the supplier, or on their way to it */
const SENT = "('submitting', 'submitted', 'accepted', 'cancel_requested', 'shipped', 'delivered')";
/**
 * S16, QA ת35: a failed submit that may be at the supplier: one whose failure may have created the order, or any failed
 * submit of an order in supplier_error (whatever its last error said), unless the supplier or a person said it holds none.
 * `o` is the order's alias in the statement.
 */
const MAYBE_SENT = "(s.status = 'failed' AND s.supplier_order_id IS NULL AND (s.reach = 'maybe' OR (s.reach = 'none' AND o.status = 'supplier_error')))";

const audit = (db: D1Database, at: string, actor: string, action: string, subject: string, detail: object) =>
  db
    .prepare('INSERT INTO audit_log (at, actor, action, subject, detail) VALUES (?, ?, ?, ?, ?)')
    .bind(at, actor.slice(0, 200), action, subject, JSON.stringify(detail));

export async function cancelOrder(
  env: Env,
  orderId: string,
  actor: string,
  reason: string,
  opts: { supplier?: SupplierClient; payment?: PaymentProvider; now?: () => number; callTimeoutMs?: number; asked?: boolean } = {},
): Promise<CancelResult | CancelError> {
  const iso = () => new Date((opts.now ?? Date.now)()).toISOString();
  const why = reason.trim().slice(0, 300);
  const order = await env.DB.prepare('SELECT id, status, paid_at FROM orders WHERE id = ?')
    .bind(orderId)
    .first<{ id: string; status: string; paid_at: string | null }>();
  if (!order) return { error: true, status: 404, code: 'order_not_found', message_he: 'ההזמנה לא נמצאה.' };

  // already canceled: finish what is left (the refund of a cancellation that did not complete), never twice
  if (order.status === 'canceled') {
    const c = await env.DB.prepare('SELECT stage FROM cancellations WHERE order_id = ?').bind(orderId).first<{ stage: CancelResult['stage'] }>();
    const stage = c?.stage ?? 'before_supplier';
    return finishCanceled(env, orderId, stage, actor, why, opts.payment);
  }

  if (order.status === 'pending_payment' || order.status === 'payment_failed') {
    const at = iso();
    const r = await env.DB.prepare("UPDATE orders SET status = 'canceled', updated_at = ? WHERE id = ? AND status IN ('pending_payment', 'payment_failed')")
      .bind(at, orderId)
      .run();
    if (!r.meta.changes) return cancelOrder(env, orderId, actor, reason, opts); // paid a moment ago: the paid path
    await env.DB.batch([
      env.DB.prepare(
        "INSERT INTO cancellations (order_id, stage, state, reason, requested_by, requested_at, resolved_at) VALUES (?, 'before_payment', 'canceled', ?, ?, ?, ?) ON CONFLICT(order_id) DO NOTHING",
      ).bind(orderId, why, actor.slice(0, 200), at, at),
      audit(env.DB, at, actor, 'order.canceled', orderId, { stage: 'before_payment', reason: why }),
    ]);
    return { outcome: 'canceled', stage: 'before_payment', message_he: 'ההזמנה בוטלה. לא שולם עליה דבר.' };
  }

  if (order.status === 'shipped' || order.status === 'delivered' || order.status === 'refunded')
    return {
      error: true,
      status: 409,
      code: order.status === 'refunded' ? 'already_refunded' : 'already_shipped',
      message_he: order.status === 'refunded' ? 'ההזמנה כבר זוכתה במלואה.' : 'ההזמנה כבר נשלחה. אי אפשר לבטל; אפשר להחזיר כסף (מלא או חלקי) אחרי שהפריט חוזר.',
    };

  // paid (or a supplier error) and nothing with the supplier, nor maybe with it (ת35): canceled in one statement, then refunded
  const at = iso();
  const before = await env.DB.prepare(
    `UPDATE orders AS o SET status = 'canceled', updated_at = ? WHERE o.id = ? AND o.status IN ('paid', 'supplier_error')
       AND NOT EXISTS (SELECT 1 FROM supplier_shipments s WHERE s.order_id = o.id AND (s.status IN ${SENT} OR ${MAYBE_SENT}))`,
  )
    .bind(at, orderId)
    .run();
  if (before.meta.changes) {
    await env.DB.batch([
      env.DB.prepare("UPDATE supplier_shipments SET status = 'canceled', updated_at = ? WHERE order_id = ? AND status IN ('queued', 'failed')").bind(
        at,
        orderId,
      ),
      env.DB.prepare(
        "INSERT INTO cancellations (order_id, stage, state, reason, requested_by, requested_at, resolved_at) VALUES (?, 'before_supplier', 'canceled', ?, ?, ?, ?) ON CONFLICT(order_id) DO NOTHING",
      ).bind(orderId, why, actor.slice(0, 200), at, at),
      audit(env.DB, at, actor, 'order.canceled', orderId, { stage: 'before_supplier', reason: why }),
    ]);
    return finishCanceled(env, orderId, 'before_supplier', actor, why, opts.payment);
  }

  // with the supplier: one being sent right now cannot be canceled from here yet
  const { results: ships } = await env.DB.prepare(
    `SELECT s.supplier, s.status, s.supplier_order_id, s.updated_at, ${MAYBE_SENT} AS maybe FROM supplier_shipments s JOIN orders o ON o.id = s.order_id WHERE s.order_id = ?`,
  )
    .bind(orderId)
    .all<{ supplier: string; status: string; supplier_order_id: string | null; updated_at: string; maybe: number }>();
  if (ships.some((s) => s.status === 'submitting'))
    return { error: true, status: 409, code: 'supplier_submit_in_progress', message_he: 'ההזמנה נשלחת לספק ממש עכשיו. נסו שוב בעוד דקה.' };
  if (ships.some((s) => s.status === 'shipped' || s.status === 'delivered'))
    return { error: true, status: 409, code: 'already_shipped', message_he: 'חלק מההזמנה כבר נשלח. אי אפשר לבטל; אפשר להחזיר כסף על מה שחוזר.' };

  let client = opts.supplier ?? null;
  const pickClient = (): CancelError | null => {
    if (client) return null;
    const c = supplierClient(env);
    if (!c.ok) return { error: true, status: 503, code: 'supplier_not_configured', message_he: 'אין חיבור לספק: בטלו אצל הספק ביד.' };
    client = c.client;
    return null;
  };

  // S16, QA ת35: maybe at the supplier (a submit that may have created the order): asked first, never refunded blindly
  const maybe = ships.filter((s) => s.maybe);
  if (maybe.length) {
    if (opts.asked || pickClient() || !client!.findOrder) return needsPerson(env, orderId, actor, iso());
    const c = client!;
    const find = c.findOrder!.bind(c);
    for (const s of maybe.filter((x) => x.supplier === c.id)) {
      // the last call ended a moment ago: the supplier may still be creating the order
      if ((opts.now ?? Date.now)() - Date.parse(s.updated_at) < (opts.callTimeoutMs ?? PROVIDER_CALL_TIMEOUT_MS))
        return { error: true, status: 409, code: 'supplier_submit_in_progress', message_he: 'ההזמנה נשלחה לספק לפני רגע ולא נענתה. נסו שוב בעוד דקה.' };
      let found: { supplier_order_id: string } | null;
      try {
        found = await withDeadline(`${c.id} findOrder`, opts.callTimeoutMs ?? PROVIDER_CALL_TIMEOUT_MS, (signal) => find(orderId, { signal }));
      } catch (err) {
        const error_id = log.error('cancel.supplier_find_failed', { order_id: orderId, supplier: c.id, code: errorCode(err) });
        return { error: true, status: 503, code: 'supplier_failed', message_he: `הספק לא ענה על השאלה אם ההזמנה אצלו. לא הוחזר כסף. נסו שוב (קוד ${error_id}).` };
      }
      await supplierHolds(env, orderId, c.id, found, `supplier:${c.id}`, iso());
    }
    if (maybe.some((s) => s.supplier !== c.id)) return needsPerson(env, orderId, actor, iso());
    return cancelOrder(env, orderId, actor, reason, { ...opts, asked: true });
  }

  const open = ships.filter((s) => s.status === 'submitted' || s.status === 'accepted' || s.status === 'cancel_requested');
  if (!open.length) return { error: true, status: 409, code: 'not_cancelable', message_he: `אי אפשר לבטל הזמנה במצב ${order.status}.` };

  // S16, QA ת42: a request already waiting on the supplier: its state, without asking the supplier again
  const waitingOn = await env.DB.prepare('SELECT state FROM cancellations WHERE order_id = ?').bind(orderId).first<{ state: string }>();
  if (waitingOn?.state === 'requested' && open.every((s) => s.status === 'cancel_requested'))
    return {
      outcome: 'requested',
      stage: 'after_supplier',
      message_he: 'בקשת הביטול כבר נשלחה לספק, ועוד לא ענה. ההזמנה תבוטל ותזוכה כשהספק יאשר.',
    };

  const missing = pickClient();
  if (missing) return missing;
  if (!client.cancelOrder)
    return {
      error: true,
      status: 503,
      code: 'supplier_cancel_not_built',
      message_he: 'אין לספק הזה קריאת ביטול עדיין: בטלו אצלו ביד, ותנו החזר כאן כשהוא מאשר.',
    };
  await env.DB.batch([
    env.DB.prepare(
      "INSERT INTO cancellations (order_id, stage, state, reason, requested_by, requested_at) VALUES (?, 'after_supplier', 'requested', ?, ?, ?) ON CONFLICT(order_id) DO NOTHING",
    ).bind(orderId, why, actor.slice(0, 200), at),
    audit(env.DB, at, actor, 'order.cancel_requested', orderId, { stage: 'after_supplier', reason: why, supplier: client.id }),
  ]);
  const answers: string[] = [];
  for (const s of open.filter((x) => x.supplier === client!.id && x.supplier_order_id && x.status !== 'cancel_requested')) {
    let outcome: 'canceled' | 'requested' | 'refused';
    try {
      outcome = (await client.cancelOrder(s.supplier_order_id!)).outcome;
    } catch (err) {
      // S16, QA ת38: a provider's error by its code only
      const error_id = log.error('cancel.supplier_failed', { order_id: orderId, supplier: client.id, code: errorCode(err) });
      return { error: true, status: 503, code: 'supplier_failed', message_he: `הספק לא ענה לבקשת הביטול. נסו שוב (קוד ${error_id}).` };
    }
    answers.push(outcome);
    const t = iso();
    const next = outcome === 'canceled' ? 'canceled' : outcome === 'requested' ? 'cancel_requested' : null;
    await env.DB.batch([
      ...(next
        ? [env.DB.prepare('UPDATE supplier_shipments SET status = ?, updated_at = ? WHERE order_id = ? AND supplier = ?').bind(next, t, orderId, s.supplier)]
        : []),
      audit(env.DB, t, `supplier:${client.id}`, `supplier.cancel_${outcome}`, orderId, { supplier_order: s.supplier_order_id }),
    ]);
  }
  if (answers.includes('refused')) {
    const t = iso();
    await env.DB.batch([
      env.DB.prepare("UPDATE cancellations SET state = 'refused', resolved_at = ? WHERE order_id = ? AND state = 'requested'").bind(t, orderId),
      // a shipment the request had marked goes back to being prepared
      env.DB.prepare("UPDATE supplier_shipments SET status = 'accepted', updated_at = ? WHERE order_id = ? AND status = 'cancel_requested'").bind(t, orderId),
      audit(env.DB, t, `supplier:${client.id}`, 'order.cancel_refused', orderId, {}),
    ]);
    return { outcome: 'refused', stage: 'after_supplier', message_he: 'הספק סירב לבטל: ההזמנה ממשיכה. אחרי המסירה אפשר להחזיר כסף על מה שחוזר.' };
  }
  const settled = await settleCanceled(env, orderId, actor, why, opts.payment);
  if (settled) return settled;
  return {
    outcome: 'requested',
    stage: 'after_supplier',
    message_he: 'בקשת הביטול נשלחה לספק. ההזמנה תבוטל ותזוכה כשהספק יאשר.',
  };
}

/** S16 (ת35): the cancellation of an order that may be at the supplier, left to a person: nothing refunded, said so. */
async function needsPerson(env: Env, orderId: string, actor: string, at: string): Promise<CancelError> {
  await audit(env.DB, at, actor, 'order.cancel_needs_person', orderId, { why: 'a submit may have reached the supplier' }).run();
  log.warn('cancel.supplier_check_needed', { order_id: orderId });
  return {
    error: true,
    status: 409,
    code: 'supplier_check_needed',
    message_he: `ייתכן שההזמנה הגיעה לספק (שליחה שלא נענתה). לא הוחזר כסף. בדקו אצל הספק לפי מספר ההזמנה ${orderId} ורשמו כאן מה מצאתם ("בדיקה אצל הספק"); אחר כך הביטול ימשיך במסלול הנכון.`,
  };
}

/**
 * S16 (ת35): what the supplier holds for our order number, recorded: an order (its id) → the shipment is submitted and
 * the order is with the supplier; none → the shipment is `checked`, and the order no longer counts as sent.
 */
async function supplierHolds(
  env: Env,
  orderId: string,
  supplier: string,
  found: { supplier_order_id: string } | null,
  actor: string,
  at: string,
  note?: string,
): Promise<void> {
  if (found)
    await env.DB.batch([
      env.DB.prepare(
        `UPDATE supplier_shipments SET status = 'submitted', supplier_order_id = ?, reach = 'none', failing_since = NULL, last_error = NULL, updated_at = ?
         WHERE order_id = ? AND supplier = ? AND status = 'failed' AND supplier_order_id IS NULL`,
      ).bind(found.supplier_order_id.slice(0, 120), at, orderId, supplier),
      env.DB.prepare("UPDATE orders SET status = 'sent_to_supplier', updated_at = ? WHERE id = ? AND status IN ('paid', 'supplier_error')").bind(at, orderId),
      audit(env.DB, at, actor, 'supplier.found_by_order', orderId, { supplier, supplier_order: found.supplier_order_id.slice(0, 120), ...(note ? { note } : {}) }),
    ]);
  else
    await env.DB.batch([
      env.DB.prepare(
        "UPDATE supplier_shipments SET reach = 'checked', updated_at = ? WHERE order_id = ? AND supplier = ? AND status = 'failed' AND supplier_order_id IS NULL",
      ).bind(at, orderId, supplier),
      audit(env.DB, at, actor, 'supplier.none_by_order', orderId, { supplier, ...(note ? { note } : {}) }),
    ]);
}

/**
 * S16 (ת35): a person's check at the supplier for a shipment that may be there (the admin's "בדיקה אצל הספק"): `found`
 * with the supplier's order id, or `none`. Only for a shipment that counts as maybe sent.
 */
export async function recordSupplierCheck(
  env: Env,
  orderId: string,
  actor: string,
  check: { outcome: 'found'; supplier_order_id: string; note: string } | { outcome: 'none'; note: string },
): Promise<{ ok: true } | { ok: false; status: 404 | 409; code: string; message_he: string }> {
  const { results } = await env.DB.prepare(
    `SELECT s.supplier FROM supplier_shipments s JOIN orders o ON o.id = s.order_id WHERE s.order_id = ? AND ${MAYBE_SENT}`,
  )
    .bind(orderId)
    .all<{ supplier: string }>();
  if (!results.length) return { ok: false, status: 409, code: 'no_supplier_check_needed', message_he: 'אין בהזמנה הזו משלוח שצריך לבדוק אצל הספק.' };
  const at = new Date().toISOString();
  for (const r of results)
    await supplierHolds(env, orderId, r.supplier, check.outcome === 'found' ? { supplier_order_id: check.supplier_order_id } : null, actor, at, check.note.slice(0, 300));
  return { ok: true };
}

/**
 * Every shipment canceled at the supplier: the order is canceled and the payment refunded. Null while any shipment is
 * still with the supplier. Used by the cancellation and by the supplier's answers (lib/shipments.ts).
 */
export async function settleCanceled(env: Env, orderId: string, actor: string, reason: string, payment?: PaymentProvider): Promise<CancelResult | null> {
  const left = await env.DB.prepare("SELECT COUNT(*) AS n FROM supplier_shipments WHERE order_id = ? AND status != 'canceled'")
    .bind(orderId)
    .first<{ n: number }>();
  if ((left?.n ?? 0) > 0) return null;
  const at = new Date().toISOString();
  const r = await env.DB.prepare(
    "UPDATE orders SET status = 'canceled', updated_at = ? WHERE id = ? AND status IN ('paid', 'sent_to_supplier', 'supplier_error')",
  )
    .bind(at, orderId)
    .run();
  if (r.meta.changes)
    await env.DB.batch([
      env.DB.prepare(
        "INSERT INTO cancellations (order_id, stage, state, reason, requested_by, requested_at, resolved_at) VALUES (?, 'after_supplier', 'canceled', ?, ?, ?, ?) ON CONFLICT(order_id) DO UPDATE SET state = 'canceled', resolved_at = excluded.resolved_at",
      ).bind(orderId, reason, actor.slice(0, 200), at, at),
      audit(env.DB, at, actor, 'order.canceled', orderId, { stage: 'after_supplier' }),
    ]);
  return finishCanceled(env, orderId, 'after_supplier', actor, reason, payment);
}

/** A canceled order: the rest of its payment refunded (once: the key is the order's), the cancellation marked done. */
async function finishCanceled(
  env: Env,
  orderId: string,
  stage: CancelResult['stage'],
  actor: string,
  reason: string,
  payment?: PaymentProvider,
): Promise<CancelResult> {
  const t = await refundTotals(env.DB, orderId);
  const key = `cancel:${orderId}`;
  const mine = await env.DB.prepare('SELECT state FROM refunds WHERE id = ?').bind(key).first<{ state: string }>();
  // nothing paid, or all of it refunded already (and not by this cancellation): nothing to refund
  if (t.paid === 0 || (!mine && t.counted >= t.paid))
    return { outcome: 'canceled', stage, message_he: t.paid === 0 ? 'ההזמנה בוטלה. לא שולם עליה דבר.' : 'ההזמנה בוטלה. כל הסכום כבר הוחזר.' };
  const refund = await requestRefund(env, { orderId, amount: 'rest', reason: reason || 'ביטול הזמנה', key, actor }, { provider: payment });
  if (refund.ok)
    await env.DB.prepare('UPDATE cancellations SET refund_id = ?, resolved_at = COALESCE(resolved_at, ?) WHERE order_id = ?')
      .bind(refund.refund_id, new Date().toISOString(), orderId)
      .run();
  return {
    outcome: 'canceled',
    stage,
    refund,
    message_he: refund.ok ? 'ההזמנה בוטלה, והתשלום הוחזר במלואו.' : `ההזמנה בוטלה, אבל ההחזר לא הושלם: ${refund.message_he}`,
  };
}
