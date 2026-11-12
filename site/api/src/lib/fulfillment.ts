/**
 * Queue consumer: paid order → supplier order (CJ in production, mock outside it). Idempotent per (order, supplier).
 * Only dropship lines go to CJ. Lines with fulfillment_source = il_3pl get their own supplier_shipments row at payment
 * time and are handled by the 3PL adapter once one is chosen (decision E1).
 *
 * S12:
 * - **ת17:** the supplier is the one SUPPLIER_PROVIDER names exactly; a value that is not a provider (or `mock` in
 *   production) submits nothing, says so loudly, and is retried: the order is never marked sent.
 * - **The sets (S11 question 2):** a line of a set of distinct SKUs (the triptych) goes to the supplier as its component
 *   SKUs, one of each per set sold (the composition snapshotted at checkout, `supplier_lines_json`), never as N × the set's
 *   own SKU. A set line without a composition is refused before anything is sent.
 *
 * S17, QA ת48: a send that may have reached the supplier (`reach = 'maybe'`: an earlier call timed out or failed on the
 * way, or a claim whose run died mid-call is taken over) is never repeated blindly. QA's B4d had two orders at the
 * supplier for one of ours (a timeout, a 503, a success). Now, before sending again:
 * - **a supplier that can be asked** (`findOrder`, by our order number): it holds the order → recorded as submitted,
 *   nothing sent; it holds none → sent; no answer → retried later, nothing sent;
 * - **a supplier that cannot be asked:** sent again only when its adapter documents that it deduplicates by our order
 *   number (`dedupesByOrderId`); otherwise nothing is sent: the order goes to supplier_error ("דורש טיפול" in the admin),
 *   and a person checks at the supplier ("בדיקה אצל הספק", lib/cancel.ts `recordSupplierCheck`): "found" records it as
 *   submitted, "none" sends it again (unless a cancellation is waiting on that check).
 */
import type { Env, SupplierJob } from '../env';
import { nowIso } from './http';
import { refuseLoudly } from './config';
import { PROVIDER_CALL_TIMEOUT_MS, withDeadline } from './deadline';
import { supplierClient, type SupplierChoice } from './suppliers';
import { SupplierRefused, type SupplierClient, type SupplierOrderInput } from './suppliers/types';
import { errorCode, log } from './log';
import { CodedError } from './errors';
import { processCreditNoteJob, processInvoiceJob } from './invoices';
import { processNotifyJob } from './notify';

/** S13: a claim on a shipment (`submitting`) older than this is a crash between the claim and the supplier's answer */
export const SUBMIT_LEASE_MS = 10 * 60_000;
/** S14, QA ת31: the supplier call's deadline, far below the lease (lib/deadline.ts) */
export const SUBMIT_CALL_TIMEOUT_MS = PROVIDER_CALL_TIMEOUT_MS;
if (SUBMIT_CALL_TIMEOUT_MS * 5 > SUBMIT_LEASE_MS) throw new Error('the supplier call deadline must stay far below the lease');

type ItemRow = {
  product_id: string;
  variant_id: string;
  qty: number;
  unit_sell_qty: number;
  pack: 'set' | 'unit';
  supplier_sku: string | null;
  supplier_lines_json: string | null;
  set_skus_json: string | null;
  set_incomplete: string | null;
};

/** What one unit sold of a line is at the supplier: its composition, else its SKU × the sale's supplier units. */
export function supplierLines(items: ItemRow[]): SupplierOrderInput['lines'] {
  const out = new Map<string, SupplierOrderInput['lines'][number]>();
  const add = (supplier_sku: string | null, product_id: string, qty: number) => {
    const key = `${product_id}\u0000${supplier_sku ?? ''}`;
    const have = out.get(key);
    if (have) have.qty += qty;
    else out.set(key, { supplier_sku, product_id, qty });
  };
  for (const i of items) {
    // the composition snapshotted at checkout; for an order from before S12, the set's current composition
    const parts = i.supplier_lines_json
      ? (JSON.parse(i.supplier_lines_json) as { supplier_sku: string; qty: number }[])
      : i.pack === 'set' && i.set_skus_json
        ? (JSON.parse(i.set_skus_json) as string[]).map((supplier_sku) => ({ supplier_sku, qty: 1 }))
        : null;
    if (parts) {
      // never N × the same print: a set's parts are distinct SKUs
      if (parts.length > 1 && new Set(parts.map((p) => p.supplier_sku)).size !== parts.length) throw new CodedError('set_parts_not_distinct', i.variant_id);
      for (const p of parts) add(p.supplier_sku, i.product_id, i.qty * p.qty);
    } else if (i.pack === 'set' && i.set_incomplete) throw new CodedError('set_composition_missing', i.variant_id);
    else add(i.supplier_sku, i.product_id, i.qty * i.unit_sell_qty);
  }
  return [...out.values()];
}

export async function processSupplierJob(
  env: Env,
  job: SupplierJob,
  attempt: number,
  /** a test passes its own supplier (as the invoice job takes its provider) and a shorter deadline */
  opts: { callTimeoutMs?: number; client?: SupplierClient } = {},
): Promise<'submitted' | 'skipped' | 'retry'> {
  // S9: the tax invoice rides the same queue (a job after "paid"); S12: it fails per message, never for the batch
  if (job.kind === 'issue-invoice') {
    const r = await processInvoiceJob(env, job.order_id);
    return r === 'invoiced' ? 'submitted' : r === 'retry' ? 'retry' : 'skipped';
  }
  // S13: the credit note of a refund (2.5) and the new-order alert (6.3) ride the same queue
  if (job.kind === 'credit-note') {
    const r = await processCreditNoteJob(env, job.refund_id);
    return r === 'credited' ? 'submitted' : r === 'retry' ? 'retry' : 'skipped';
  }
  if (job.kind === 'notify-order') {
    const r = await processNotifyJob(env, job.order_id, attempt);
    return r === 'sent' ? 'submitted' : r;
  }
  const order = await env.DB.prepare('SELECT id, status, shipping_method, address_json, customer_id FROM orders WHERE id = ?')
    .bind(job.order_id)
    .first<{ id: string; status: string; shipping_method: 'economy' | 'express'; address_json: string; customer_id: string }>();
  if (!order || order.status !== 'paid') return 'skipped';
  const now = nowIso();
  const choice: SupplierChoice = opts.client ? { ok: true, client: opts.client } : supplierClient(env);
  if (!choice.ok) {
    // ת17: no supplier runs; the paid order stays paid (never "sent"), the queued row says why, and the job is retried
    refuseLoudly('the supplier job', choice.reason, order.id);
    // S16 (ת39): the run of failures starts here, for /healthz; nothing was sent, so the shipment's reach is unchanged
    await env.DB.prepare(
      "UPDATE supplier_shipments SET last_error = ?, attempts = ?, failing_since = COALESCE(failing_since, ?), updated_at = ? WHERE order_id = ? AND fulfillment_source = 'dropship_cj' AND status IN ('queued', 'failed')",
    )
      .bind(`config: ${choice.reason}`.slice(0, 500), attempt, now, now, order.id)
      .run();
    if (attempt >= 5)
      await env.DB.prepare("UPDATE orders SET status = 'supplier_error', updated_at = ? WHERE id = ? AND status = 'paid'").bind(now, order.id).run();
    return 'retry';
  }
  const client = choice.client;
  // the row the payment queued while no supplier was configured (routes/payments.ts) is this supplier's now
  await env.DB.prepare(
    "UPDATE supplier_shipments SET supplier = ?, updated_at = ? WHERE order_id = ? AND supplier = 'unconfigured' AND NOT EXISTS (SELECT 1 FROM supplier_shipments WHERE order_id = ? AND supplier = ?)",
  )
    .bind(client.id, now, order.id, order.id, client.id)
    .run();
  await env.DB.prepare(
    `INSERT INTO supplier_shipments (id, order_id, supplier, status, created_at, updated_at) SELECT ?, ?, ?, 'queued', ?, ? WHERE true
     ON CONFLICT(order_id, supplier) DO NOTHING`,
  )
    .bind(crypto.randomUUID(), order.id, client.id, now, now)
    .run();
  // S13: the claim, before the supplier is called, only while the order is paid: a cancellation before the supplier
  // (lib/cancel.ts) cancels only while no shipment is claimed, so the two can never both happen
  const claim = await env.DB.prepare(
    `UPDATE supplier_shipments SET status = 'submitting', attempts = ?, updated_at = ?
     WHERE order_id = ? AND supplier = ? AND status IN ('queued', 'failed') AND EXISTS (SELECT 1 FROM orders WHERE id = ? AND status = 'paid')`,
  )
    .bind(attempt, now, order.id, client.id, order.id)
    .run();
  if (!claim.meta.changes) {
    const row = await env.DB.prepare('SELECT status, updated_at FROM supplier_shipments WHERE order_id = ? AND supplier = ?')
      .bind(order.id, client.id)
      .first<{ status: string; updated_at: string }>();
    // a claim left by a crash is taken over (compare-and-swap); the supplier must deduplicate by our order number
    if (row?.status !== 'submitting' || Date.now() - Date.parse(row.updated_at) < SUBMIT_LEASE_MS) return 'skipped';
    // S17 (ת48): the run that died may have reached the supplier: the takeover counts as a send that may have reached it
    const take = await env.DB.prepare(
      "UPDATE supplier_shipments SET attempts = ?, reach = 'maybe', updated_at = ? WHERE order_id = ? AND supplier = ? AND status = 'submitting' AND updated_at = ?",
    )
      .bind(attempt, now, order.id, client.id, row.updated_at)
      .run();
    if (!take.meta.changes) return 'skipped';
  }
  // S17, QA ת48: a send that may have reached the supplier is never repeated blindly
  const held = await env.DB.prepare('SELECT reach FROM supplier_shipments WHERE order_id = ? AND supplier = ?')
    .bind(order.id, client.id)
    .first<{ reach: string }>();
  if (held?.reach === 'maybe') {
    const r = await beforeSendingAgain(env, order.id, client, attempt, now, opts.callTimeoutMs ?? SUBMIT_CALL_TIMEOUT_MS);
    if (r !== 'send') return r;
  }
  const customer = await env.DB.prepare('SELECT full_name, phone, email FROM customers WHERE id = ?')
    .bind(order.customer_id)
    .first<{ full_name: string; phone: string; email: string }>();
  const { results: items } = await env.DB.prepare(
    `SELECT oi.product_id, oi.variant_id, oi.qty, oi.unit_sell_qty, oi.pack, oi.supplier_sku, oi.supplier_lines_json, v.set_skus_json, v.set_incomplete
     FROM order_items oi LEFT JOIN product_variants v ON v.id = oi.variant_id
     WHERE oi.order_id = ? AND oi.fulfillment_source = 'dropship_cj' ORDER BY oi.line`,
  )
    .bind(order.id)
    .all<ItemRow>();
  try {
    let lines: SupplierOrderInput['lines'];
    try {
      lines = supplierLines(items);
    } catch (err) {
      // a set without its composition (or with repeated parts) is refused here: nothing is sent to the supplier
      throw new SupplierRefused(errorCode(err), err instanceof Error ? err.message : String(err));
    }
    const input = {
      order_id: order.id,
      lines,
      ship_to: { ...customer!, ...(JSON.parse(order.address_json) as { city: string; street: string; house: string; apartment: string; zip: string }) },
      shipping_method: order.shipping_method,
    };
    // S14, QA ת31: the call never outlives the claim's lease (a deadline far below it, lib/deadline.ts)
    const res = await withDeadline(`${client.id} submitOrder`, opts.callTimeoutMs ?? SUBMIT_CALL_TIMEOUT_MS, (signal) => client.submitOrder(input, { signal }));
    // recorded only by the run that holds the claim (`updated_at` is the claim's, this run's `now`)
    const [mine] = await env.DB.batch([
      env.DB.prepare(
        `UPDATE supplier_shipments SET status = 'submitted', supplier_order_id = ?, attempts = ?, request_json = ?, response_json = ?, last_error = NULL, failing_since = NULL, reach = 'none', updated_at = ?
         WHERE order_id = ? AND supplier = ? AND status = 'submitting' AND updated_at = ?`,
      ).bind(
        res.supplier_order_id,
        attempt,
        JSON.stringify({ lines: input.lines.map((l) => [l.supplier_sku, l.qty]), shipping_method: input.shipping_method }),
        JSON.stringify(res.raw),
        now,
        order.id,
        client.id,
        now,
      ),
      env.DB.prepare(
        "UPDATE orders SET status = 'sent_to_supplier', updated_at = ? WHERE id = ? AND status = 'paid' AND EXISTS (SELECT 1 FROM supplier_shipments WHERE order_id = ? AND supplier = ? AND status = 'submitted' AND supplier_order_id = ?)",
      ).bind(now, order.id, order.id, client.id, res.supplier_order_id),
      env.DB.prepare(
        "INSERT INTO audit_log (at, actor, action, subject, detail) SELECT ?, ?, ?, ?, ? WHERE EXISTS (SELECT 1 FROM supplier_shipments WHERE order_id = ? AND supplier = ? AND status = 'submitted' AND supplier_order_id = ? AND updated_at = ?)",
      ).bind(now, 'queue', 'supplier.submitted', order.id, res.supplier_order_id, order.id, client.id, res.supplier_order_id, now),
    ]);
    if (!mine?.meta.changes) {
      // the claim was taken over while this call ran: nothing recorded from here; a person checks for a second order
      const detail = `the claim was taken over by another run before ${client.id} answered (${res.supplier_order_id}): not recorded; check the supplier for a second order`;
      await env.DB.prepare('INSERT INTO audit_log (at, actor, action, subject, detail) VALUES (?, ?, ?, ?, ?)')
        .bind(now, 'queue', 'supplier.claim_lost', order.id, detail)
        .run();
      refuseLoudly('the supplier job', detail, order.id);
      return 'skipped';
    }
    return 'submitted';
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    // S16, QA ת35: a refusal created nothing; any other failure (a timeout, a network or server error) may have created
    // the order at the supplier, and the shipment counts as sent from now on (lib/cancel.ts) until the supplier is asked
    const refused = err instanceof SupplierRefused;
    await env.DB.prepare(
      `UPDATE supplier_shipments SET status = 'failed', attempts = ?, last_error = ?, failing_since = COALESCE(failing_since, ?),
         reach = CASE WHEN ? = 1 THEN reach ELSE 'maybe' END, updated_at = ?
       WHERE order_id = ? AND supplier = ? AND status = 'submitting' AND updated_at = ?`,
    )
      .bind(attempt, msg.slice(0, 500), now, refused ? 1 : 0, now, order.id, client.id, now)
      .run();
    // S16, QA ת39/ת38: one row per failed send, by code only (the text, which may echo the buyer, stays in D1)
    log.error('supplier.submit_failed', { order_id: order.id, supplier: client.id, attempt, code: errorCode(err), may_have_reached: !refused });
    if (attempt >= 5)
      await env.DB.prepare("UPDATE orders SET status = 'supplier_error', updated_at = ? WHERE id = ? AND status = 'paid'").bind(now, order.id).run();
    return 'retry';
  }
}

const audit = (env: Env, at: string, actor: string, action: string, subject: string, detail: object) =>
  env.DB.prepare('INSERT INTO audit_log (at, actor, action, subject, detail) VALUES (?, ?, ?, ?, ?)').bind(at, actor, action, subject, JSON.stringify(detail));

/**
 * S17, QA ת48: before a shipment that may be at the supplier is sent again. The claim (`submitting`, `updated_at = now`)
 * is this run's; every write below holds it (compare-and-swap on `updated_at`).
 */
async function beforeSendingAgain(
  env: Env,
  orderId: string,
  client: SupplierClient,
  attempt: number,
  now: string,
  timeoutMs: number,
): Promise<'send' | 'submitted' | 'skipped' | 'retry'> {
  const mine = "WHERE order_id = ? AND supplier = ? AND status = 'submitting' AND updated_at = ?";
  if (client.findOrder) {
    const find = client.findOrder.bind(client);
    let found: { supplier_order_id: string } | null;
    try {
      found = await withDeadline(`${client.id} findOrder`, timeoutMs, (signal) => find(orderId, { signal }));
    } catch (err) {
      // not answered: nothing is sent; the claim goes back (still maybe), and the queue asks again
      await env.DB.prepare(
        `UPDATE supplier_shipments SET status = 'failed', last_error = ?, failing_since = COALESCE(failing_since, ?), updated_at = ? ${mine}`,
      )
        .bind(`findOrder failed: ${errorCode(err)}`, now, now, orderId, client.id, now)
        .run();
      log.error('supplier.find_failed', { order_id: orderId, supplier: client.id, attempt, code: errorCode(err) });
      if (attempt >= 5)
        await env.DB.prepare("UPDATE orders SET status = 'supplier_error', updated_at = ? WHERE id = ? AND status = 'paid'").bind(now, orderId).run();
      return 'retry';
    }
    if (found) {
      const id = found.supplier_order_id.slice(0, 120);
      const [rec] = await env.DB.batch([
        env.DB.prepare(
          `UPDATE supplier_shipments SET status = 'submitted', supplier_order_id = ?, attempts = ?, reach = 'none', last_error = NULL, failing_since = NULL, updated_at = ? ${mine}`,
        ).bind(id, attempt, now, orderId, client.id, now),
        env.DB.prepare(
          "UPDATE orders SET status = 'sent_to_supplier', updated_at = ? WHERE id = ? AND status = 'paid' AND EXISTS (SELECT 1 FROM supplier_shipments WHERE order_id = ? AND supplier = ? AND status = 'submitted' AND supplier_order_id = ?)",
        ).bind(now, orderId, orderId, client.id, id),
        env.DB.prepare(
          "INSERT INTO audit_log (at, actor, action, subject, detail) SELECT ?, ?, 'supplier.found_by_order', ?, ? WHERE EXISTS (SELECT 1 FROM supplier_shipments WHERE order_id = ? AND supplier = ? AND status = 'submitted' AND supplier_order_id = ? AND updated_at = ?)",
        ).bind(
          now,
          `supplier:${client.id}`,
          orderId,
          JSON.stringify({ supplier: client.id, supplier_order: id, by: 'the supplier job' }),
          orderId,
          client.id,
          id,
          now,
        ),
      ]);
      log.info('supplier.found_by_order', { order_id: orderId, supplier: client.id, attempt });
      return rec?.meta.changes ? 'submitted' : 'skipped';
    }
    // it holds none: the earlier send created nothing, and this one goes
    await env.DB.batch([
      env.DB.prepare(`UPDATE supplier_shipments SET reach = 'checked' ${mine}`).bind(orderId, client.id, now),
      audit(env, now, `supplier:${client.id}`, 'supplier.none_by_order', orderId, { supplier: client.id, by: 'the supplier job' }),
    ]);
    return 'send';
  }
  if (client.dedupesByOrderId) {
    log.info('supplier.resend_deduplicated', { order_id: orderId, supplier: client.id, attempt });
    return 'send';
  }
  // neither asked nor deduplicating: nothing is sent; a person checks at the supplier
  await env.DB.batch([
    env.DB.prepare(
      `UPDATE supplier_shipments SET status = 'failed', reach = 'maybe', failing_since = COALESCE(failing_since, ?), last_error = COALESCE(last_error, ?), updated_at = ? ${mine}`,
    ).bind(now, 'a send that may have reached the supplier: a person checks there', now, orderId, client.id, now),
    env.DB.prepare("UPDATE orders SET status = 'supplier_error', updated_at = ? WHERE id = ? AND status = 'paid'").bind(now, orderId),
    audit(env, now, 'queue', 'supplier.resend_needs_person', orderId, {
      supplier: client.id,
      why: 'a send that may have reached the supplier, which cannot be asked',
    }),
  ]);
  log.warn('supplier.resend_needs_person', { order_id: orderId, supplier: client.id, attempt });
  return 'skipped';
}
