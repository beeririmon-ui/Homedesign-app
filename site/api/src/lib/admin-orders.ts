/**
 * S13 (launch checklist 6.3): what the admin reads about orders, for the JSON API (routes/admin.ts) and the screen
 * (routes/admin-ui.ts) alike: the list with filters and search by the public order number, and one order with its items
 * (house and variant), its payment, invoice and supplier tracks from the audit log, its refunds and its cancellation.
 * Behind Cloudflare Access only: this is where a customer's details are shown, never in a log.
 */
import { refundTotals } from './refunds';

export const ADMIN_STATUS_HE: Record<string, string> = {
  pending_payment: 'ממתינה לתשלום',
  paid: 'שולמה',
  payment_failed: 'התשלום נכשל',
  canceled: 'בוטלה',
  sent_to_supplier: 'אצל הספק',
  supplier_error: 'תקלה מול הספק',
  shipped: 'נשלחה',
  delivered: 'נמסרה',
  refunded: 'זוכתה',
};
export const SHIPMENT_STATUS_HE: Record<string, string> = {
  queued: 'בתור',
  submitting: 'נשלחת לספק',
  submitted: 'התקבלה אצל הספק',
  accepted: 'בהכנה אצל הספק',
  failed: 'השליחה לספק נכשלה',
  shipped: 'נשלחה',
  delivered: 'נמסרה',
  cancel_requested: 'בקשת ביטול ממתינה לספק',
  canceled: 'בוטלה',
};
export const INVOICE_STATE_HE: Record<string, string> = {
  none: 'טרם הופקה',
  claimed: 'בהפקה',
  issued: 'הופקה',
  unresolved: 'לבדיקה של אדם',
};
export const REFUND_STATE_HE: Record<string, string> = {
  claimed: 'בדרך לסולק',
  refunded: 'הוחזר',
  refused: 'הסולק סירב',
  unresolved: 'לבדיקה של אדם',
};
export const CREDIT_STATE_HE: Record<string, string> = {
  pending: 'ממתינה',
  claimed: 'בהפקה',
  issued: 'הופקה',
  not_needed: 'לא נדרשת (לא הופקה חשבונית)',
  unresolved: 'לבדיקה של אדם',
};
export const CANCEL_STATE_HE: Record<string, string> = {
  requested: 'בקשת ביטול נשלחה לספק, ממתינה לתשובה',
  canceled: 'בוטלה',
  refused: 'הספק סירב לבטל: ההזמנה ממשיכה',
};
export const CANCEL_STAGE_HE: Record<string, string> = {
  before_payment: 'לפני התשלום',
  before_supplier: 'לפני השליחה לספק',
  after_supplier: 'אחרי השליחה לספק',
  after_payment_late: 'תשלום שהגיע אחרי הביטול',
};
export const AUDIT_HE: Record<string, string> = {
  'order.created': 'ההזמנה נוצרה',
  'order.paid': 'שולמה',
  'order.paid_after_cancel': 'תשלום הגיע אחרי הביטול',
  'order.canceled': 'בוטלה',
  'order.cancel_requested': 'נשלחה בקשת ביטול לספק',
  'order.cancel_refused': 'הספק סירב לבטל',
  'order.invoiced': 'חשבונית מס הופקה',
  'invoice.unresolved': 'חשבונית: לבדיקה של אדם',
  'invoice.checked': 'חשבונית: נבדקה ידנית',
  'supplier.submitted': 'נשלחה לספק',
  'supplier.accepted': 'הספק מכין',
  'supplier.shipped': 'יצאה למשלוח',
  'supplier.delivered': 'נמסרה',
  'supplier.canceled': 'בוטלה אצל הספק',
  'supplier.cancel_requested': 'הספק קיבל את בקשת הביטול',
  'supplier.cancel_canceled': 'הספק ביטל מיד',
  'supplier.cancel_refused': 'הספק סירב לבטל',
  'refund.requested': 'בקשת החזר',
  'refund.refunded': 'הכסף הוחזר',
  'refund.refused': 'הסולק סירב להחזר',
  'refund.unresolved': 'החזר: לבדיקה של אדם',
  'refund.credit_note': 'חשבונית זיכוי הופקה',
  'refund.credit_not_needed': 'זיכוי לא נדרש (לא הופקה חשבונית)',
  'refund.credit_unresolved': 'זיכוי: לבדיקה של אדם',
};
/** which track an audit row belongs to on the order page */
export function trackOf(action: string): 'payment' | 'invoice' | 'supplier' {
  if (action === 'order.invoiced' || action.startsWith('invoice.') || action.startsWith('refund.credit')) return 'invoice';
  if (action.startsWith('supplier.') || action.startsWith('order.cancel') || action === 'order.canceled') return 'supplier';
  return 'payment';
}

/** the list's filters: a status, or "needs a person" */
export const FILTERS = ['attention', ...Object.keys(ADMIN_STATUS_HE)] as const;
export type Filter = (typeof FILTERS)[number];
/** an order a person should look at: a supplier error, an invoice or refund for a person, a cancellation waiting */
const ATTENTION_SQL = `(o.status = 'supplier_error'
  OR EXISTS (SELECT 1 FROM invoices i WHERE i.order_id = o.id AND i.state = 'unresolved')
  OR EXISTS (SELECT 1 FROM refunds r WHERE r.order_id = o.id AND (r.state IN ('claimed', 'unresolved') OR r.credit_state = 'unresolved'))
  OR EXISTS (SELECT 1 FROM cancellations x WHERE x.order_id = o.id AND x.state = 'requested'))`;

export type ListRow = {
  id: string;
  status: string;
  total_agorot: number;
  created_at: string;
  paid_at: string | null;
  full_name: string;
  email: string;
  items: number;
  invoice_state: string | null;
  refunded_agorot: number;
  cancel_state: string | null;
  shipments: string | null;
  attention: number;
};

export async function listOrders(db: D1Database, q: { filter?: Filter; search?: string; limit: number }): Promise<ListRow[]> {
  const where: string[] = [];
  const args: unknown[] = [];
  if (q.filter === 'attention') where.push(ATTENTION_SQL);
  else if (q.filter) {
    where.push('o.status = ?');
    args.push(q.filter);
  }
  if (q.search) {
    // the public order number, or its start (digits only, validated by the caller)
    where.push('o.id LIKE ?');
    args.push(`${q.search}%`);
  }
  const { results } = await db
    .prepare(
      `SELECT o.id, o.status, o.total_agorot, o.created_at, o.paid_at, c.full_name, c.email,
              (SELECT COALESCE(SUM(qty), 0) FROM order_items WHERE order_id = o.id) AS items,
              (SELECT state FROM invoices WHERE order_id = o.id) AS invoice_state,
              (SELECT COALESCE(SUM(amount_agorot), 0) FROM refunds WHERE order_id = o.id AND state = 'refunded') AS refunded_agorot,
              (SELECT state FROM cancellations WHERE order_id = o.id) AS cancel_state,
              (SELECT group_concat(status) FROM supplier_shipments WHERE order_id = o.id) AS shipments,
              CASE WHEN ${ATTENTION_SQL} THEN 1 ELSE 0 END AS attention
       FROM orders o JOIN customers c ON c.id = o.customer_id
       ${where.length ? `WHERE ${where.join(' AND ')}` : ''}
       ORDER BY o.created_at DESC LIMIT ?`,
    )
    .bind(...args, q.limit)
    .all<ListRow>();
  return results;
}

export type AuditRow = { id: number; at: string; actor: string; action: string; detail: string | null };

export async function orderDetail(db: D1Database, id: string) {
  const order = await db
    .prepare('SELECT o.*, c.full_name, c.email, c.phone, c.marketing_consent FROM orders o JOIN customers c ON c.id = o.customer_id WHERE o.id = ?')
    .bind(id)
    .first<Record<string, unknown>>();
  if (!order) return null;
  delete order.token_hash;
  const [items, payments, supplier, invoice, refunds, cancellation, audit, totals] = await Promise.all([
    db
      .prepare(
        `SELECT oi.line, oi.product_id, oi.variant_id, oi.name_he, oi.qty, oi.unit_price_agorot, oi.unit_cost_usd_cents, oi.unit_shipping_usd_cents,
                oi.pack, oi.unit_sell_qty, oi.fulfillment_source, oi.house, oi.supplier_sku, oi.supplier_lines_json
         FROM order_items oi WHERE oi.order_id = ? ORDER BY oi.line`,
      )
      .bind(id)
      .all<{
        line: number;
        product_id: string;
        variant_id: string;
        name_he: string;
        qty: number;
        unit_price_agorot: number;
        unit_cost_usd_cents: number;
        unit_shipping_usd_cents: number;
        pack: string;
        unit_sell_qty: number;
        fulfillment_source: string;
        house: string | null;
        supplier_sku: string | null;
        supplier_lines_json: string | null;
      }>(),
    db
      .prepare('SELECT provider, provider_event_id, type, amount_agorot, received_at, outcome FROM payment_events WHERE order_id = ? ORDER BY received_at')
      .bind(id)
      .all(),
    db
      .prepare(
        'SELECT supplier, fulfillment_source, status, supplier_order_id, tracking_number, tracking_url, attempts, last_error, shipped_at, delivered_at, updated_at FROM supplier_shipments WHERE order_id = ? ORDER BY created_at',
      )
      .bind(id)
      .all<{
        supplier: string;
        fulfillment_source: string;
        status: string;
        supplier_order_id: string | null;
        tracking_number: string | null;
        tracking_url: string | null;
        attempts: number;
        last_error: string | null;
        shipped_at: string | null;
        delivered_at: string | null;
        updated_at: string;
      }>(),
    db
      .prepare(
        'SELECT state, provider, provider_invoice_id, url, attempts, claimed_at, issued_at, last_error, checked_by, checked_at FROM invoices WHERE order_id = ?',
      )
      .bind(id)
      .first<{
        state: string;
        provider: string;
        provider_invoice_id: string | null;
        url: string | null;
        attempts: number;
        claimed_at: string;
        issued_at: string | null;
        last_error: string | null;
        checked_by: string | null;
        checked_at: string | null;
      }>(),
    db
      .prepare(
        'SELECT id, kind, amount_agorot, reason, state, provider, provider_refund_id, requested_by, claimed_at, completed_at, last_error, credit_state, credit_note_id FROM refunds WHERE order_id = ? ORDER BY claimed_at',
      )
      .bind(id)
      .all<{
        id: string;
        kind: string;
        amount_agorot: number;
        reason: string;
        state: string;
        provider: string;
        provider_refund_id: string | null;
        requested_by: string;
        claimed_at: string;
        completed_at: string | null;
        last_error: string | null;
        credit_state: string;
        credit_note_id: string | null;
      }>(),
    db.prepare('SELECT stage, state, reason, requested_by, requested_at, resolved_at, refund_id FROM cancellations WHERE order_id = ?').bind(id).first<{
      stage: string;
      state: string;
      reason: string;
      requested_by: string;
      requested_at: string;
      resolved_at: string | null;
      refund_id: string | null;
    }>(),
    db.prepare('SELECT id, at, actor, action, detail FROM audit_log WHERE subject = ? ORDER BY id').bind(id).all<AuditRow>(),
    refundTotals(db, id),
  ]);
  const fx = order.fx_usd_ils_at_order as number;
  const cogs = items.results.reduce((s, i) => s + Math.round((i.unit_cost_usd_cents + i.unit_shipping_usd_cents) * fx) * i.qty, 0);
  const net = (order.total_agorot as number) - (order.vat_agorot as number);
  const tracks = { payment: [] as AuditRow[], invoice: [] as AuditRow[], supplier: [] as AuditRow[] };
  for (const a of audit.results) tracks[trackOf(a.action)].push(a);
  return {
    order: { ...order, address: JSON.parse(order.address_json as string) as Record<string, string>, address_json: undefined },
    items: items.results,
    payments: payments.results,
    supplier_shipments: supplier.results,
    invoice: invoice ?? null,
    refunds: refunds.results,
    cancellation: cancellation ?? null,
    audit: audit.results,
    tracks,
    money: {
      paid_agorot: totals.paid,
      refunded_agorot: totals.refunded,
      counted_agorot: totals.counted,
      refundable_agorot: Math.max(0, totals.paid - totals.counted),
    },
    margin: { net_agorot: net, cogs_agorot: cogs, gross_profit_agorot: net - cogs, note: 'before payment fees, returns reserve and CAC' },
  };
}
export type OrderDetail = NonNullable<Awaited<ReturnType<typeof orderDetail>>>;

/**
 * S13: the "checked by a person" action on an invoice left `unresolved` (S12, ת16). The person looked at the provider:
 * - `found`: the provider has the order's invoice; its number is recorded as the order's invoice;
 * - `none`: the provider has none; the claim is released and the invoice job runs again (one invoice, never two).
 * Either way the audit log says who checked, when, and what they found.
 */
export async function checkInvoice(
  env: { DB: D1Database; SUPPLIER_QUEUE: Queue<{ kind: 'issue-invoice'; order_id: string }> },
  orderId: string,
  actor: string,
  input: { outcome: 'found'; invoice_number: string; note: string } | { outcome: 'none'; note: string },
): Promise<{ ok: true } | { ok: false; status: 404 | 409; code: string; message_he: string }> {
  const inv = await env.DB.prepare('SELECT state, provider FROM invoices WHERE order_id = ?').bind(orderId).first<{ state: string; provider: string }>();
  if (!inv) return { ok: false, status: 404, code: 'no_invoice_claim', message_he: 'אין להזמנה הזו חשבונית בבדיקה.' };
  if (inv.state !== 'unresolved') return { ok: false, status: 409, code: 'invoice_not_unresolved', message_he: 'החשבונית של ההזמנה הזו לא מחכה לבדיקה.' };
  const at = new Date().toISOString();
  const detail = JSON.stringify(
    input.outcome === 'found' ? { outcome: 'found', invoice_number: input.invoice_number, note: input.note } : { outcome: 'none', note: input.note },
  );
  // first in the batch, and only while the claim is still for a person: the row says who checked, once
  const log = env.DB.prepare(
    "INSERT INTO audit_log (at, actor, action, subject, detail) SELECT ?, ?, 'invoice.checked', ?, ? WHERE EXISTS (SELECT 1 FROM invoices WHERE order_id = ? AND state = 'unresolved')",
  ).bind(at, actor.slice(0, 200), orderId, detail, orderId);
  if (input.outcome === 'found') {
    const [, done] = await env.DB.batch([
      log,
      env.DB.prepare(
        "UPDATE invoices SET state = 'issued', provider_invoice_id = ?, issued_at = ?, checked_by = ?, checked_at = ?, last_error = NULL WHERE order_id = ? AND state = 'unresolved'",
      ).bind(input.invoice_number, at, actor.slice(0, 200), at, orderId),
      env.DB.prepare(
        "UPDATE orders SET invoice_provider = ?, invoice_number = ?, updated_at = ? WHERE id = ? AND EXISTS (SELECT 1 FROM invoices WHERE order_id = ? AND state = 'issued' AND checked_at = ?)",
      ).bind(inv.provider, input.invoice_number, at, orderId, orderId, at),
      env.DB.prepare(
        "INSERT INTO audit_log (at, actor, action, subject, detail) SELECT ?, ?, 'order.invoiced', ?, ? WHERE NOT EXISTS (SELECT 1 FROM audit_log WHERE action = 'order.invoiced' AND subject = ?)",
      ).bind(at, actor.slice(0, 200), orderId, JSON.stringify({ invoice_id: input.invoice_number, checked: true }), orderId),
    ]);
    if (!done?.meta.changes) return { ok: false, status: 409, code: 'invoice_not_unresolved', message_he: 'החשבונית של ההזמנה הזו לא מחכה לבדיקה.' };
    return { ok: true };
  }
  const [, done] = await env.DB.batch([log, env.DB.prepare("DELETE FROM invoices WHERE order_id = ? AND state = 'unresolved'").bind(orderId)]);
  if (!done?.meta.changes) return { ok: false, status: 409, code: 'invoice_not_unresolved', message_he: 'החשבונית של ההזמנה הזו לא מחכה לבדיקה.' };
  await env.SUPPLIER_QUEUE.send({ kind: 'issue-invoice', order_id: orderId });
  return { ok: true };
}
