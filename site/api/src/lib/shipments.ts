/**
 * S13 (launch checklist 3.3): the supplier's word on an order (accepted, shipped with a tracking number, delivered,
 * canceled) becomes the shipment's state, the order's state, and what the customer sees: "התקבלה · בהכנה · נשלחה ·
 * נמסרה" (ART6). Never a step back (a late "accepted" after "shipped" changes nothing), and every change is in the audit
 * log with who reported it (the supplier, or a person playing the mock supplier in development and preview).
 *
 * - **The order's state** follows its shipments: shipped once every shipment still going has left, delivered once every
 *   one has arrived; canceled (and refunded, lib/cancel.ts) once every one was canceled at the supplier.
 * - **The customer's tracking link** is the supplier's only when it is a generic tracker and names no supplier
 *   (`customerTrackingUrl`); otherwise the customer gets the number alone.
 * - **Where updates come from:** the cron asks the supplier (`syncShipments`, when its client has a tracking call), and a
 *   person plays the mock supplier from the admin outside production.
 */
import type { Env } from '../env';
import type { SupplierClient, SupplierUpdate } from './suppliers/types';
import { settleCanceled } from './cancel';
import { log } from './log';

/** generic trackers a customer may be sent to: they track any carrier's number and name no seller */
const GENERIC_TRACKERS = new Set([
  '17track.net',
  'www.17track.net',
  't.17track.net',
  'parcelsapp.com',
  'www.parcelsapp.com',
  'israelpost.co.il',
  'www.israelpost.co.il',
  'mypost.israelpost.co.il',
  'track.aftership.com',
]);
/** a supplier (or its marketplace or logistics arm) anywhere in a link: never shown to a customer */
const SUPPLIER_IN_URL = /(?:^|[^a-z])(cj|cjdropshipping|cjpacket|aliexpress|alibaba|cainiao|zendrop|temu|dsers|spocket)(?:[^a-z]|$)/i;

/** The link the customer may follow: the supplier's, only when it is https, a generic tracker, and names no supplier. */
export function customerTrackingUrl(raw: string | null | undefined): string | null {
  if (!raw) return null;
  let u: URL;
  try {
    u = new URL(raw);
  } catch {
    return null;
  }
  if (u.protocol !== 'https:' || u.username || u.password || u.port) return null;
  if (!GENERIC_TRACKERS.has(u.hostname.toLowerCase())) return null;
  if (SUPPLIER_IN_URL.test(decodeURIComponent(u.href))) return null;
  return u.href;
}

/** how far a shipment has come; a report never moves it back */
const RANK: Record<string, number> = {
  queued: 0,
  submitting: 0,
  failed: 0,
  submitted: 1,
  accepted: 2,
  cancel_requested: 2,
  shipped: 3,
  delivered: 4,
  canceled: 5,
};
const NUMBER = /^[A-Za-z0-9-]{4,40}$/;

export type UpdateOutcome = 'applied' | 'unchanged' | 'unknown_shipment';

export async function applySupplierUpdate(
  env: Env,
  input: { orderId: string; supplier: string; update: SupplierUpdate; actor: string },
): Promise<UpdateOutcome> {
  const { orderId, supplier, update, actor } = input;
  const ship = await env.DB.prepare('SELECT status, tracking_number, tracking_url FROM supplier_shipments WHERE order_id = ? AND supplier = ?')
    .bind(orderId, supplier)
    .first<{ status: string; tracking_number: string | null; tracking_url: string | null }>();
  if (!ship) return 'unknown_shipment';
  const at = update.at ?? new Date().toISOString();
  const cur = ship.status;
  const stmts: D1PreparedStatement[] = [];
  const audit = (action: string, detail: object) =>
    env.DB.prepare('INSERT INTO audit_log (at, actor, action, subject, detail) VALUES (?, ?, ?, ?, ?)').bind(
      at,
      actor.slice(0, 200),
      action,
      orderId,
      JSON.stringify(detail),
    );

  let next = cur;
  if (update.status === 'canceled') next = RANK[cur]! < 3 ? 'canceled' : cur;
  else if (cur === 'canceled') next = cur;
  else if (cur === 'cancel_requested' && update.status === 'accepted' && update.cancel !== 'refused')
    next = cur; // still waiting on the answer
  else if (RANK[update.status]! > RANK[cur]! || (cur === 'cancel_requested' && update.cancel === 'refused')) next = update.status;

  const number = update.tracking_number && NUMBER.test(update.tracking_number) ? update.tracking_number : null;
  const url = update.tracking_url && update.tracking_url.length <= 500 ? update.tracking_url : null;
  const tracking = (next === 'shipped' || next === 'delivered') && (number || url);
  if (next !== cur || (tracking && (number !== ship.tracking_number || url !== ship.tracking_url))) {
    stmts.push(
      env.DB.prepare(
        `UPDATE supplier_shipments SET status = ?, tracking_number = COALESCE(?, tracking_number), tracking_url = COALESCE(?, tracking_url),
           shipped_at = CASE WHEN ? IN ('shipped', 'delivered') THEN COALESCE(shipped_at, ?) ELSE shipped_at END,
           delivered_at = CASE WHEN ? = 'delivered' THEN COALESCE(delivered_at, ?) ELSE delivered_at END,
           updated_at = ? WHERE order_id = ? AND supplier = ?`,
      ).bind(next, number, url, next, at, next, at, at, orderId, supplier),
      audit(`supplier.${next}`, { supplier, ...(number ? { tracking_number: number } : {}) }),
    );
  }
  // the supplier will not cancel (it says so, or the parcel left): the request is refused, the order goes on
  const refused = update.cancel === 'refused' || next === 'shipped' || next === 'delivered';
  if (refused)
    stmts.push(
      env.DB.prepare("UPDATE cancellations SET state = 'refused', resolved_at = ? WHERE order_id = ? AND state = 'requested'").bind(at, orderId),
      env.DB.prepare(
        "INSERT INTO audit_log (at, actor, action, subject, detail) SELECT ?, ?, 'order.cancel_refused', ?, '{}' WHERE EXISTS (SELECT 1 FROM cancellations WHERE order_id = ? AND state = 'refused' AND resolved_at = ?)",
      ).bind(at, actor.slice(0, 200), orderId, orderId, at),
    );
  if (!stmts.length) return 'unchanged';
  await env.DB.batch(stmts);
  if (next === 'canceled') {
    await settleCanceled(env, orderId, actor, 'ביטול שאושר אצל הספק');
    return 'applied';
  }
  await settleOrder(env, orderId, at);
  log.info('shipment.updated', { order_id: orderId, supplier, status: next });
  return next === cur && !tracking ? 'unchanged' : 'applied';
}

/** The order's state from its shipments: shipped once all still going left, delivered once all arrived. */
async function settleOrder(env: Env, orderId: string, at: string): Promise<void> {
  const { results } = await env.DB.prepare("SELECT status FROM supplier_shipments WHERE order_id = ? AND status != 'canceled'")
    .bind(orderId)
    .all<{ status: string }>();
  if (!results.length) return;
  const all = (ok: string[]) => results.every((r) => ok.includes(r.status));
  const next = all(['delivered']) ? 'delivered' : all(['shipped', 'delivered']) ? 'shipped' : null;
  if (!next) return;
  await env.DB.prepare(`UPDATE orders SET status = ?, updated_at = ? WHERE id = ? AND status IN ('paid', 'sent_to_supplier', 'supplier_error', 'shipped')`)
    .bind(next, at, orderId)
    .run();
}

/** The cron: asks the supplier about the shipments it holds that have not arrived yet (when its client can be asked). */
export async function syncShipments(env: Env, client: SupplierClient, limit = 50): Promise<{ asked: number; applied: number }> {
  if (!client.tracking) return { asked: 0, applied: 0 };
  const { results } = await env.DB.prepare(
    `SELECT order_id, supplier_order_id FROM supplier_shipments
     WHERE supplier = ? AND supplier_order_id IS NOT NULL AND status IN ('submitted', 'accepted', 'cancel_requested', 'shipped')
     ORDER BY updated_at LIMIT ?`,
  )
    .bind(client.id, limit)
    .all<{ order_id: string; supplier_order_id: string }>();
  let applied = 0;
  for (const s of results) {
    try {
      const u = await client.tracking(s.supplier_order_id);
      if (u && (await applySupplierUpdate(env, { orderId: s.order_id, supplier: client.id, update: u, actor: `supplier:${client.id}` })) === 'applied')
        applied++;
    } catch (err) {
      log.error('shipment.sync_failed', { order_id: s.order_id, supplier: client.id }, err);
    }
  }
  return { asked: results.length, applied };
}

/** What the customer's order page shows of the delivery: per shipment that left, its number and a generic link. */
export async function deliveryView(db: D1Database, orderId: string) {
  const { results } = await db
    .prepare(
      "SELECT status, tracking_number, tracking_url, shipped_at, delivered_at FROM supplier_shipments WHERE order_id = ? AND status IN ('shipped', 'delivered') ORDER BY shipped_at",
    )
    .bind(orderId)
    .all<{
      status: 'shipped' | 'delivered';
      tracking_number: string | null;
      tracking_url: string | null;
      shipped_at: string | null;
      delivered_at: string | null;
    }>();
  return results.map((r) => ({
    status_he: r.status === 'delivered' ? 'נמסרה' : 'נשלחה',
    tracking_number: r.tracking_number,
    tracking_url: customerTrackingUrl(r.tracking_url),
    shipped_at: r.shipped_at,
    delivered_at: r.delivered_at,
  }));
}
