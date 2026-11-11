/**
 * S13, operations (briefs/site-s13-operations-2026-11-11.md): the cancellation states before and after the supplier,
 * idempotent refunds that never go above what was paid (and their credit notes), the delivery statuses the customer
 * sees, no PII in a log row, /healthz without internal details, the admin closed (403) without permission, and the
 * new-order alert's mock.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { signWebhook } from '@hd/shared';
import { app } from '../src/app';
import type { Env, SupplierJob } from '../src/env';
import { buildSeedSql } from '../scripts/seed';
import { createD1, migrate } from './d1-shim';
import { catalog } from './fixture';
import { processSupplierJob } from '../src/lib/fulfillment';
import { processCreditNoteJob, processInvoiceJob, type InvoiceProvider } from '../src/lib/invoices';
import { requestRefund } from '../src/lib/refunds';
import { cancelOrder } from '../src/lib/cancel';
import { applySupplierUpdate, customerTrackingUrl, syncShipments } from '../src/lib/shipments';
import { RefundRefused, type IssuedRefund, type PaymentProvider, type RefundInput } from '../src/lib/payments/types';
import type { SupplierClient } from '../src/lib/suppliers/types';
import { logRow, log, redact, scrub } from '../src/lib/log';
import { processNotifyJob } from '../src/lib/notify';
import { configIssues } from '../src/lib/config';

const SECRET = 'test-webhook-secret-s13-not-a-key';
const DEV_TOKEN = 'dev-admin-token-for-tests-only-0123456789';
const BUYER = { full_name: 'ישראלה ישראלי', email: 'buyer.s13@example.com', phone: '050-7654321' };
const ADDRESS = { city: 'חיפה', street: 'שדרות הנשיא', house: '42', apartment: '7', zip: '3460000', notes: 'להשאיר אצל השכנה' };
let env: Env;
let sent: SupplierJob[];
beforeEach(() => {
  const DB = createD1();
  migrate(DB, buildSeedSql(catalog));
  sent = [];
  env = {
    DB,
    SUPPLIER_QUEUE: { send: vi.fn(async (m: SupplierJob) => void sent.push(m)), sendBatch: vi.fn() } as unknown as Queue<SupplierJob>,
    ENVIRONMENT: 'test',
    PAYMENT_PROVIDER: 'mock',
    SUPPLIER_PROVIDER: 'mock',
    INVOICE_PROVIDER: 'mock',
    NOTIFY_PROVIDER: 'mock',
    ACCESS_TEAM_DOMAIN: '',
    ACCESS_AUD: '',
    PAYMENT_WEBHOOK_SECRET: SECRET,
  };
});
afterEach(() => vi.restoreAllMocks());

const req = (path: string, init?: RequestInit) => app.request(`http://localhost${path}`, init, env);
const json = (body: unknown, method = 'POST', headers: Record<string, string> = {}): RequestInit => ({
  method,
  headers: { 'content-type': 'application/json', ...headers },
  body: JSON.stringify(body),
});
const asAdmin = { 'x-hd-dev-admin': DEV_TOKEN };
async function cartWith(items: { variant_id: string; qty: number }[]) {
  const { id } = (await (await req('/api/cart', { method: 'POST' })).json()) as { id: string };
  for (const i of items) expect((await req(`/api/cart/${id}/items`, json(i, 'PUT'))).status).toBe(200);
  return id;
}
async function pendingOrder(items = [{ variant_id: 'vase-a:default', qty: 1 }]) {
  const body = { cart_id: await cartWith(items), customer: BUYER, address: ADDRESS, shipping_method: 'express', consents: { terms: true, marketing: false } };
  const r = (await (await req('/api/checkout', json(body))).json()) as { order_id: string; order_token: string };
  const o = await env.DB.prepare('SELECT payment_session_id, total_agorot FROM orders WHERE id = ?')
    .bind(r.order_id)
    .first<{ payment_session_id: string; total_agorot: number }>();
  return { orderId: r.order_id, token: r.order_token, session: o!.payment_session_id, total: o!.total_agorot };
}
async function pay(o: { orderId: string; session: string; total: number }) {
  const body = JSON.stringify({ id: `evt_${o.orderId}`, type: 'payment.succeeded', session_id: o.session, amount_agorot: o.total });
  const r = await req('/api/webhooks/payment/mock', {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-mock-signature': await signWebhook(SECRET, body, Math.floor(Date.now() / 1000)) },
    body,
  });
  return (await r.json()) as { outcome: string };
}
async function paidOrder(items?: { variant_id: string; qty: number }[]) {
  const o = await pendingOrder(items);
  expect((await pay(o)).outcome).toBe('paid');
  return o;
}
async function sentOrder() {
  const o = await paidOrder();
  expect(await processSupplierJob(env, { kind: 'submit-order', order_id: o.orderId }, 1)).toBe('submitted');
  return o;
}
const one = async <T>(sql: string, ...b: unknown[]) =>
  (await env.DB.prepare(sql)
    .bind(...b)
    .first<T>())!;
const n = async (sql: string, ...b: unknown[]) => (await one<{ n: number }>(sql, ...b)).n;
const status = async (id: string) => (await one<{ status: string }>('SELECT status FROM orders WHERE id = ?', id)).status;
const refunded = async (id: string) => n("SELECT COALESCE(SUM(amount_agorot), 0) AS n FROM refunds WHERE order_id = ? AND state = 'refunded'", id);
const customerView = async (o: { orderId: string; token: string }) =>
  (await (await req(`/api/orders/${o.orderId}`, { headers: { 'x-order-token': o.token } })).json()) as {
    status: string;
    status_he: string;
    shipments: { status_he: string; tracking_number: string | null; tracking_url: string | null }[];
    refunded_agorot: number;
  };

/** a payment provider like a network one: counts every refund it makes, per key, and can fail or refuse on demand */
function payments(o: { idempotent?: boolean; find?: boolean; failOnce?: boolean; refuse?: boolean } = {}) {
  const made: { key: string; amount: number }[] = [];
  const byKey = new Map<string, IssuedRefund>();
  let fail = o.failOnce ?? false;
  const p: PaymentProvider & { made: typeof made } = {
    id: 'mock',
    made,
    refundsIdempotent: o.idempotent ?? true,
    async createSession() {
      throw new Error('not used');
    },
    async verifyWebhook() {
      return { ok: false, reason: 'not used' };
    },
    async refund(input: RefundInput, { idempotency_key }) {
      await new Promise((r) => setTimeout(r, 3));
      if (o.refuse) throw new RefundRefused('card_closed');
      if (p.refundsIdempotent && byKey.has(idempotency_key)) return byKey.get(idempotency_key)!;
      if (input.refunded_before_agorot + input.amount_agorot > input.paid_agorot) throw new RefundRefused('exceeds');
      made.push({ key: idempotency_key, amount: input.amount_agorot });
      const r = { refund_id: `RF-${made.length}` };
      byKey.set(idempotency_key, r);
      if (fail) {
        fail = false;
        throw new Error('network: connection reset');
      }
      return r;
    },
  };
  if (o.find) p.findRefund = async (k) => byKey.get(k) ?? null;
  return p;
}

describe('the cancellation procedure: every state, before and after the supplier', () => {
  it('before payment: canceled, nothing refunded; a payment that still arrives is refunded at once', async () => {
    const o = await pendingOrder();
    const r = await cancelOrder(env, o.orderId, 'owner@example.com', 'הלקוחה ביקשה');
    expect(r).toMatchObject({ outcome: 'canceled', stage: 'before_payment' });
    expect(await status(o.orderId)).toBe('canceled');
    expect(await n('SELECT COUNT(*) AS n FROM refunds WHERE order_id = ?', o.orderId)).toBe(0);
    // the customer paid a moment later: recorded, refunded in full, never kept and never sent to the supplier
    expect((await pay(o)).outcome).toBe('paid_after_cancel');
    expect(await refunded(o.orderId)).toBe(o.total);
    expect(await status(o.orderId)).toBe('canceled');
    expect(sent.some((j) => j.kind === 'submit-order')).toBe(false);
    expect((await one<{ stage: string }>('SELECT stage FROM cancellations WHERE order_id = ?', o.orderId)).stage).toBe('after_payment_late');
  });

  it('before the supplier: canceled and refunded in full through the payment provider; the supplier job then sends nothing', async () => {
    const o = await paidOrder();
    const r = await cancelOrder(env, o.orderId, 'owner@example.com', 'מלאי');
    expect(r).toMatchObject({ outcome: 'canceled', stage: 'before_supplier', refund: { ok: true, amount_agorot: o.total } });
    expect(await status(o.orderId)).toBe('canceled');
    expect(await refunded(o.orderId)).toBe(o.total);
    expect(await processSupplierJob(env, { kind: 'submit-order', order_id: o.orderId }, 1)).toBe('skipped');
    expect(await n("SELECT COUNT(*) AS n FROM supplier_shipments WHERE order_id = ? AND status IN ('submitting', 'submitted')", o.orderId)).toBe(0);
    // every step names who did it
    const audit = (
      await env.DB.prepare('SELECT actor, action FROM audit_log WHERE subject = ? ORDER BY id').bind(o.orderId).all<{ actor: string; action: string }>()
    ).results;
    expect(audit).toContainEqual({ actor: 'owner@example.com', action: 'order.canceled' });
    expect(audit).toContainEqual({ actor: 'owner@example.com', action: 'refund.requested' });
    expect(audit).toContainEqual({ actor: 'owner@example.com', action: 'refund.refunded' });
    // asked again: no second refund
    expect(await cancelOrder(env, o.orderId, 'owner@example.com', 'שוב')).toMatchObject({ outcome: 'canceled' });
    expect(await n('SELECT COUNT(*) AS n FROM refunds WHERE order_id = ?', o.orderId)).toBe(1);
  });

  it('a submission in flight (the shipment claimed) is never canceled "before the supplier": 409, try again', async () => {
    const o = await paidOrder();
    await env.DB.prepare("UPDATE supplier_shipments SET status = 'submitting' WHERE order_id = ?").bind(o.orderId).run();
    expect(await cancelOrder(env, o.orderId, 'owner@example.com', 'מהר')).toMatchObject({ error: true, code: 'supplier_submit_in_progress' });
    expect(await status(o.orderId)).toBe('paid');
    // and a canceled order is never claimed by the supplier job
    const p = await paidOrder();
    await cancelOrder(env, p.orderId, 'owner@example.com', 'בוטל');
    expect(await processSupplierJob(env, { kind: 'submit-order', order_id: p.orderId }, 2)).toBe('skipped');
  });

  it('after the supplier: a cancellation request; the order waits on the answer, then is canceled and refunded', async () => {
    const o = await sentOrder();
    const r = await cancelOrder(env, o.orderId, 'owner@example.com', 'הלקוח התחרט');
    expect(r).toMatchObject({ outcome: 'requested', stage: 'after_supplier' });
    expect(await status(o.orderId)).toBe('sent_to_supplier');
    expect((await one<{ state: string }>('SELECT state FROM cancellations WHERE order_id = ?', o.orderId)).state).toBe('requested');
    expect((await one<{ status: string }>("SELECT status FROM supplier_shipments WHERE order_id = ? AND supplier = 'mock'", o.orderId)).status).toBe(
      'cancel_requested',
    );
    expect(await refunded(o.orderId)).toBe(0);
    // the supplier confirms
    expect(await applySupplierUpdate(env, { orderId: o.orderId, supplier: 'mock', update: { status: 'canceled' }, actor: 'supplier:mock' })).toBe('applied');
    expect(await status(o.orderId)).toBe('canceled');
    expect(await refunded(o.orderId)).toBe(o.total);
    expect((await one<{ state: string }>('SELECT state FROM cancellations WHERE order_id = ?', o.orderId)).state).toBe('canceled');
  });

  it('after the supplier: the supplier refuses; the order goes on, nothing is refunded', async () => {
    const o = await sentOrder();
    await cancelOrder(env, o.orderId, 'owner@example.com', 'הלקוח התחרט');
    await applySupplierUpdate(env, { orderId: o.orderId, supplier: 'mock', update: { status: 'accepted', cancel: 'refused' }, actor: 'supplier:mock' });
    expect((await one<{ state: string }>('SELECT state FROM cancellations WHERE order_id = ?', o.orderId)).state).toBe('refused');
    expect((await one<{ status: string }>("SELECT status FROM supplier_shipments WHERE order_id = ? AND supplier = 'mock'", o.orderId)).status).toBe(
      'accepted',
    );
    expect(await status(o.orderId)).toBe('sent_to_supplier');
    expect(await refunded(o.orderId)).toBe(0);
  });

  it('after the supplier: one that cancels at once (canceled and refunded); one that refuses (refused); shipped (409)', async () => {
    const at = (outcome: 'canceled' | 'refused'): SupplierClient => ({
      id: 'mock',
      submitOrder: async () => ({ supplier_order_id: 'x', raw: {} }),
      cancelOrder: async () => ({ outcome }),
    });
    const a = await sentOrder();
    expect(await cancelOrder(env, a.orderId, 'owner@example.com', 'א', { supplier: at('canceled') })).toMatchObject({
      outcome: 'canceled',
      refund: { ok: true },
    });
    expect(await status(a.orderId)).toBe('canceled');
    const b = await sentOrder();
    expect(await cancelOrder(env, b.orderId, 'owner@example.com', 'ב', { supplier: at('refused') })).toMatchObject({ outcome: 'refused' });
    expect(await status(b.orderId)).toBe('sent_to_supplier');
    const c = await sentOrder();
    await applySupplierUpdate(env, {
      orderId: c.orderId,
      supplier: 'mock',
      update: { status: 'shipped', tracking_number: 'IL12345678' },
      actor: 'supplier:mock',
    });
    expect(await cancelOrder(env, c.orderId, 'owner@example.com', 'ג')).toMatchObject({ error: true, status: 409, code: 'already_shipped' });
  });
});

describe('refunds: idempotent, and never more than what was paid', () => {
  it('the same key is the same refund: one provider call, one row, one audit row', async () => {
    const o = await paidOrder();
    const p = payments();
    const ask = () =>
      requestRefund(env, { orderId: o.orderId, amount: 1000, reason: 'פגם', key: 'rf_same_key_1', actor: 'owner@example.com' }, { provider: p });
    const first = await ask();
    const again = await ask();
    expect(first).toMatchObject({ ok: true, amount_agorot: 1000, duplicate: false });
    expect(again).toMatchObject({ ok: true, amount_agorot: 1000, duplicate: true });
    expect(p.made).toEqual([{ key: 'rf_same_key_1', amount: 1000 }]);
    expect(await n("SELECT COUNT(*) AS n FROM audit_log WHERE action = 'refund.refunded' AND subject = ?", o.orderId)).toBe(1);
    // the key reused for another amount is refused, never a second refund
    expect(await requestRefund(env, { orderId: o.orderId, amount: 2000, reason: 'פגם', key: 'rf_same_key_1', actor: 'x' }, { provider: p })).toMatchObject({
      ok: false,
      code: 'key_reused',
    });
  });

  it('partial, then the rest, then nothing: the refunds add up to exactly what was paid', async () => {
    const o = await paidOrder();
    const p = payments();
    expect(await requestRefund(env, { orderId: o.orderId, amount: 1500, reason: 'חלקי', key: 'rf_partial_1', actor: 'a' }, { provider: p })).toMatchObject({
      ok: true,
    });
    expect(await status(o.orderId)).toBe('paid');
    expect(
      await requestRefund(env, { orderId: o.orderId, amount: o.total, reason: 'יותר מדי', key: 'rf_too_much', actor: 'a' }, { provider: p }),
    ).toMatchObject({
      ok: false,
      status: 422,
      code: 'exceeds_paid',
    });
    expect(await requestRefund(env, { orderId: o.orderId, amount: 'rest', reason: 'היתרה', key: 'rf_rest_0001', actor: 'a' }, { provider: p })).toMatchObject({
      ok: true,
      amount_agorot: o.total - 1500,
    });
    expect(await refunded(o.orderId)).toBe(o.total);
    expect(await status(o.orderId)).toBe('refunded');
    expect(await requestRefund(env, { orderId: o.orderId, amount: 1, reason: 'עוד', key: 'rf_one_more', actor: 'a' }, { provider: p })).toMatchObject({
      ok: false,
      code: 'exceeds_paid',
    });
    expect(await requestRefund(env, { orderId: o.orderId, amount: 'rest', reason: 'עוד', key: 'rf_rest_0002', actor: 'a' }, { provider: p })).toMatchObject({
      ok: false,
      code: 'nothing_left',
    });
    expect(p.made.reduce((s, m) => s + m.amount, 0)).toBe(o.total);
    expect((await one<{ kind: string }>("SELECT kind FROM refunds WHERE id = 'rf_rest_0001'")).kind).toBe('full');
  });

  it('two refunds at once, each 60% of the payment, different keys: exactly one goes through', async () => {
    const o = await paidOrder();
    const p = payments();
    const part = Math.ceil(o.total * 0.6);
    const [a, b] = await Promise.all([
      requestRefund(env, { orderId: o.orderId, amount: part, reason: 'א', key: 'rf_race_a1', actor: 'a' }, { provider: p }),
      requestRefund(env, { orderId: o.orderId, amount: part, reason: 'ב', key: 'rf_race_b1', actor: 'b' }, { provider: p }),
    ]);
    expect([a.ok, b.ok].filter(Boolean)).toHaveLength(1);
    expect(await refunded(o.orderId)).toBe(part);
    expect(await n("SELECT COALESCE(SUM(amount_agorot), 0) AS n FROM refunds WHERE order_id = ? AND state != 'refused'", o.orderId)).toBeLessThanOrEqual(
      o.total,
    );
  });

  it('a provider failure keeps the claim (it counts); the same key again refunds once; a refusal frees the amount', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const o = await paidOrder();
    const flaky = payments({ failOnce: true });
    const ask = (p: PaymentProvider, key: string, amount: number | 'rest') =>
      requestRefund(env, { orderId: o.orderId, amount, reason: 'r', key, actor: 'a' }, { provider: p });
    expect(await ask(flaky, 'rf_flaky_01', 2000)).toMatchObject({ ok: false, status: 502, code: 'provider_failed' });
    expect((await one<{ state: string }>("SELECT state FROM refunds WHERE id = 'rf_flaky_01'")).state).toBe('claimed');
    // while it is claimed it counts: the rest is the total minus it
    expect(await ask(flaky, 'rf_flaky_02', o.total)).toMatchObject({ ok: false, code: 'exceeds_paid' });
    expect(await ask(flaky, 'rf_flaky_01', 2000)).toMatchObject({ ok: true, amount_agorot: 2000 });
    expect(flaky.made).toHaveLength(1);
    const refusing = payments({ refuse: true });
    expect(await ask(refusing, 'rf_refused_1', 1000)).toMatchObject({ ok: false, code: 'refused' });
    expect((await one<{ state: string }>("SELECT state FROM refunds WHERE id = 'rf_refused_1'")).state).toBe('refused');
    // refused: freed, so the rest is still everything but the 2000
    expect(await ask(payments(), 'rf_after_refuse', 'rest')).toMatchObject({ ok: true, amount_agorot: o.total - 2000 });
  });

  it('a provider that neither deduplicates nor can be asked: a claim left behind goes to a person, never a second call', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const o = await paidOrder();
    const p = payments({ idempotent: false, failOnce: true });
    let clock = Date.now();
    const ask = () => requestRefund(env, { orderId: o.orderId, amount: 1000, reason: 'r', key: 'rf_blind_01', actor: 'a' }, { provider: p, now: () => clock });
    expect(await ask()).toMatchObject({ ok: false, code: 'provider_failed' });
    expect(await ask()).toMatchObject({ ok: false, code: 'in_progress' });
    clock += 11 * 60_000;
    expect(await ask()).toMatchObject({ ok: false, code: 'unresolved' });
    expect(p.made).toHaveLength(1);
    expect(await n("SELECT COUNT(*) AS n FROM audit_log WHERE action = 'refund.unresolved' AND subject = ?", o.orderId)).toBe(1);
  });

  it('the credit note: once per refund (the refund id is the key), and none when no invoice was issued', async () => {
    const o = await paidOrder();
    expect(await processInvoiceJob(env, o.orderId)).toBe('invoiced');
    const r = await requestRefund(env, { orderId: o.orderId, amount: 1200, reason: 'r', key: 'rf_credit_01', actor: 'a' }, { provider: payments() });
    expect(r.ok).toBe(true);
    expect(sent).toContainEqual({ kind: 'credit-note', order_id: o.orderId, refund_id: 'rf_credit_01' });
    const keys: string[] = [];
    const inv: InvoiceProvider = {
      id: 'counting',
      idempotent: true,
      issue: async () => ({ invoice_id: 'x', url: null }),
      creditNote: async (input, { idempotency_key }) => {
        keys.push(idempotency_key);
        expect(input.amount_agorot).toBe(1200);
        return { credit_note_id: `CN-${idempotency_key}`, url: null };
      },
    };
    expect(await processCreditNoteJob(env, 'rf_credit_01', inv)).toBe('credited');
    expect(await processCreditNoteJob(env, 'rf_credit_01', inv)).toBe('skipped');
    expect(keys).toEqual(['rf_credit_01']);
    expect((await one<{ credit_state: string }>("SELECT credit_state FROM refunds WHERE id = 'rf_credit_01'")).credit_state).toBe('issued');
    // canceled before its invoice was issued: no credit note is needed
    const c = await paidOrder();
    await cancelOrder(env, c.orderId, 'owner@example.com', 'בוטל', { payment: payments() });
    const rid = (await one<{ id: string }>('SELECT id FROM refunds WHERE order_id = ?', c.orderId)).id;
    expect(await processCreditNoteJob(env, rid, inv)).toBe('skipped');
    expect((await one<{ credit_state: string }>('SELECT credit_state FROM refunds WHERE id = ?', rid)).credit_state).toBe('not_needed');
  });
});

describe('delivery statuses for the customer (התקבלה · בהכנה · נשלחה · נמסרה)', () => {
  it('from the supplier: preparing, shipped with its number and a generic link, delivered; never a step back', async () => {
    const o = await paidOrder();
    expect(await customerView(o)).toMatchObject({ status: 'paid', status_he: 'התקבלה', shipments: [] });
    await processSupplierJob(env, { kind: 'submit-order', order_id: o.orderId }, 1);
    expect(await customerView(o)).toMatchObject({ status: 'sent_to_supplier', status_he: 'בהכנה' });
    await applySupplierUpdate(env, { orderId: o.orderId, supplier: 'mock', update: { status: 'accepted' }, actor: 'supplier:mock' });
    expect((await customerView(o)).status_he).toBe('בהכנה');
    await applySupplierUpdate(env, {
      orderId: o.orderId,
      supplier: 'mock',
      update: { status: 'shipped', tracking_number: 'RR123456789IL', tracking_url: 'https://parcelsapp.com/he/tracking/RR123456789IL' },
      actor: 'supplier:mock',
    });
    expect(await customerView(o)).toMatchObject({
      status: 'shipped',
      status_he: 'נשלחה',
      shipments: [{ status_he: 'נשלחה', tracking_number: 'RR123456789IL', tracking_url: 'https://parcelsapp.com/he/tracking/RR123456789IL' }],
    });
    await applySupplierUpdate(env, { orderId: o.orderId, supplier: 'mock', update: { status: 'delivered' }, actor: 'supplier:mock' });
    expect(await customerView(o)).toMatchObject({
      status: 'delivered',
      status_he: 'נמסרה',
      shipments: [{ status_he: 'נמסרה', tracking_number: 'RR123456789IL' }],
    });
    // a late "accepted" changes nothing
    expect(await applySupplierUpdate(env, { orderId: o.orderId, supplier: 'mock', update: { status: 'accepted' }, actor: 'supplier:mock' })).toBe('unchanged');
    expect(await status(o.orderId)).toBe('delivered');
  });

  it("the supplier's own link is never shown: the number alone; the customer's view names no supplier", async () => {
    const o = await sentOrder();
    await applySupplierUpdate(env, {
      orderId: o.orderId,
      supplier: 'mock',
      update: { status: 'shipped', tracking_number: 'CJPKL7012345678', tracking_url: 'https://cjpacket.com/?trackingNumber=CJPKL7012345678' },
      actor: 'supplier:mock',
    });
    const v = await customerView(o);
    expect(v.shipments).toEqual([expect.objectContaining({ tracking_number: 'CJPKL7012345678', tracking_url: null })]);
    expect(JSON.stringify(v)).not.toMatch(/cjpacket|aliexpress|zendrop|alibaba|cainiao|"mock"|supplier/i);
  });

  it('only a generic tracker that names no supplier passes (https, no credentials)', () => {
    expect(customerTrackingUrl('https://www.17track.net/he/track?nums=RR123456789IL')).toBe('https://www.17track.net/he/track?nums=RR123456789IL');
    expect(customerTrackingUrl('https://www.israelpost.co.il/itemtrace?itemcode=RR123456789IL')).not.toBeNull();
    for (const bad of [
      'https://www.17track.net/he/track?nums=X&from=aliexpress',
      'https://t.17track.net/#nums=X&fc=cj',
      'https://track.aliexpress.com/logisticsdetail.htm?id=1',
      'https://global.cainiao.com/detail.htm?mailNoList=X',
      'https://cjpacket.com/?trackingNumber=X',
      'http://www.17track.net/he/track?nums=X',
      'https://user:pw@www.17track.net/',
      'https://www.17track.net.evil.example/track',
      'javascript:alert(1)',
      'not a url',
      null,
    ])
      expect(customerTrackingUrl(bad), String(bad)).toBeNull();
  });

  it('the cron asks the supplier (when its client can be asked) and applies what it says', async () => {
    const o = await sentOrder();
    const asked: string[] = [];
    const client: SupplierClient = {
      id: 'mock',
      submitOrder: async () => ({ supplier_order_id: 'x', raw: {} }),
      tracking: async (id) => (asked.push(id), { status: 'shipped', tracking_number: 'LP00123456789', tracking_url: null }),
    };
    expect(await syncShipments(env, client)).toEqual({ asked: 1, applied: 1 });
    expect(asked).toEqual([`MOCK-${o.orderId}`]);
    expect((await customerView(o)).shipments).toEqual([expect.objectContaining({ status_he: 'נשלחה', tracking_number: 'LP00123456789', tracking_url: null })]);
    expect(await syncShipments(env, { id: 'mock', submitOrder: client.submitOrder })).toEqual({ asked: 0, applied: 0 });
  });
});

describe('no PII in a log row', () => {
  it('the row drops personal keys wherever they are and masks emails and phone numbers in any string', () => {
    const row = logRow('error', 'x', {
      order_id: '1234567890',
      email: 'buyer@example.com',
      customer: { full_name: 'ישראלה ישראלי', phone: '050-1234567' },
      ship_to: { city: 'חיפה', street: 'הנשיא' },
      address_json: '{"city":"חיפה"}',
      detail: 'call 050-1234567 or +972 52 765 4321, mail buyer@example.com',
      nested: { list: [{ name: 'ישראלה', ok: 1 }] },
    });
    const text = JSON.stringify(row);
    for (const pii of ['buyer@example.com', '050-1234567', 'ישראלה', 'חיפה', 'הנשיא', '765 4321']) expect(text, pii).not.toContain(pii);
    expect(row).toMatchObject({
      level: 'error',
      event: 'x',
      order_id: '1234567890',
      detail: 'call [phone] or [phone], mail [email]',
      nested: { list: [{ ok: 1 }] },
    });
    expect(scrub('order 1234567890')).toBe('order 1234567890'); // an order number is not a phone number
    expect(redact(new Error('failed for buyer@example.com'))).toMatchObject({ error_message: 'failed for [email]' });
  });

  it("a whole order, its jobs, a refund, a cancellation and a crash: no row carries the buyer's details; the crash gives the customer its id", async () => {
    const rows: unknown[] = [];
    for (const m of ['log', 'warn', 'error', 'info'] as const) vi.spyOn(console, m).mockImplementation((...a: unknown[]) => void rows.push(a));
    const o = await paidOrder();
    await processSupplierJob(env, { kind: 'submit-order', order_id: o.orderId }, 1);
    await processSupplierJob(env, { kind: 'issue-invoice', order_id: o.orderId }, 1);
    await processSupplierJob(env, { kind: 'notify-order', order_id: o.orderId }, 1);
    await requestRefund(env, { orderId: o.orderId, amount: 500, reason: 'r', key: 'rf_pii_0001', actor: 'a' }, { provider: payments({ failOnce: true }) });
    const p = await paidOrder();
    await cancelOrder(env, p.orderId, 'owner@example.com', 'בוטל');
    // a crash in a request: the database fails under the order page
    const broken = {
      ...env,
      DB: {
        prepare: () => ({
          bind: () => ({
            first: async () => {
              throw new Error(`D1 failed reading ${BUYER.email} ${BUYER.phone}`);
            },
          }),
        }),
      } as unknown as D1Database,
    };
    const res = await app.request(`http://localhost/api/orders/${o.orderId}`, { headers: { 'x-order-token': o.token } }, broken);
    expect(res.status).toBe(500);
    const body = (await res.json()) as { error: string; error_id: string; message_he: string };
    expect(body.error_id).toMatch(/^E-[2-9A-HJKMNP-Z]{8}$/);
    expect(body.message_he).toContain(body.error_id);
    const text = JSON.stringify(rows);
    expect(rows.length).toBeGreaterThan(2);
    expect(text).toContain(body.error_id);
    for (const pii of [BUYER.email, BUYER.phone, BUYER.full_name, ADDRESS.street, ADDRESS.city, ADDRESS.notes, '7654321']) expect(text, pii).not.toContain(pii);
  });
});

describe('/healthz: D1 and the queue, nothing else', () => {
  it('ok: 200 with one word per check, and not one internal detail', async () => {
    const res = await req('/healthz');
    expect(res.status).toBe(200);
    expect(res.headers.get('cache-control')).toBe('no-store');
    const body = await res.json();
    expect(body).toEqual({ ok: true, checks: { db: 'ok', queue: 'ok' } });
    const text = JSON.stringify(body);
    for (const leak of ['test', 'mock', 'environment', 'version', 'catalog', SECRET, 'D1', 'error']) expect(text).not.toContain(leak);
  });

  it('the database failing: 503, "fail", no error text; a queue that stopped draining: 503, "stalled"', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    const broken = {
      ...env,
      DB: {
        prepare: () => ({
          first: async () => {
            throw new Error('D1_ERROR: no such table: secret_internal');
          },
          bind: () => ({ first: async () => null }),
        }),
      } as unknown as D1Database,
    };
    const r1 = await app.request('http://localhost/healthz', {}, broken);
    expect(r1.status).toBe(503);
    expect(await r1.json()).toEqual({ ok: false, checks: { db: 'fail', queue: 'ok' } });
    const o = await paidOrder();
    await env.DB.prepare('UPDATE orders SET paid_at = ? WHERE id = ?')
      .bind(new Date(Date.now() - 31 * 60_000).toISOString(), o.orderId)
      .run();
    const r2 = await req('/healthz');
    expect(r2.status).toBe(503);
    expect(await r2.json()).toEqual({ ok: false, checks: { db: 'ok', queue: 'stalled' } });
  });

  it('the old /api/health no longer tells the environment', async () => {
    expect(await (await req('/api/health')).json()).toEqual({ ok: true, catalog_version: 'testcatalog01' });
  });
});

describe('the admin: 403 without permission, everywhere', () => {
  it('the API and the screen, reads and actions: 403, and nothing changes', async () => {
    vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    const o = await paidOrder();
    const id = o.orderId;
    for (const [path, init] of [
      ['/api/admin/orders', undefined],
      [`/api/admin/orders/${id}`, undefined],
      [`/api/admin/orders/${id}/cancel`, json({ reason: 'x y' })],
      [`/api/admin/orders/${id}/refund`, json({ amount_agorot: 100, reason: 'x y', key: 'rf_forbidden1' })],
      ['/admin/', undefined],
      ['/admin', undefined],
      [`/admin/orders/${id}`, undefined],
      [
        `/admin/orders/${id}/cancel`,
        { method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded', origin: 'http://localhost' }, body: 'reason=xyz' },
      ],
    ] as [string, RequestInit | undefined][]) {
      expect((await req(path, init)).status, path).toBe(403);
      expect((await req(path, { ...init, headers: { ...(init?.headers as Record<string, string>), 'cf-access-jwt-assertion': 'a.b.c' } })).status, path).toBe(
        403,
      );
    }
    expect(await status(id)).toBe('paid');
    expect(await n('SELECT COUNT(*) AS n FROM refunds')).toBe(0);
    // the screen's 403 is a short Hebrew page that says nothing about the shop
    const page = await (await req('/admin/')).text();
    expect(page).toContain('אין גישה');
    expect(page).not.toMatch(/הזמנה|order|1\d{9}/);
  });

  it('the dev token: only in a local run, only the exact value', async () => {
    env.ADMIN_DEV_TOKEN = DEV_TOKEN;
    expect((await req('/api/admin/orders', { headers: asAdmin })).status).toBe(200);
    expect((await req('/api/admin/orders', { headers: { 'x-hd-dev-admin': `${DEV_TOKEN}x` } })).status).toBe(403);
    for (const ENVIRONMENT of ['preview', 'production'] as const) {
      env = { ...env, ENVIRONMENT };
      expect((await req('/api/admin/orders', { headers: asAdmin })).status, ENVIRONMENT).toBe(403);
      expect((await req('/admin/', { headers: asAdmin })).status, ENVIRONMENT).toBe(403);
    }
  });
});

describe('the admin screen and API (order operations)', () => {
  beforeEach(() => {
    env.ADMIN_DEV_TOKEN = DEV_TOKEN;
  });

  it('the list filters by status and "needs a person", and searches by the public order number', async () => {
    const a = await paidOrder();
    const b = await pendingOrder();
    const list = async (q: string) =>
      ((await (await req(`/api/admin/orders${q}`, { headers: asAdmin })).json()) as { orders: { id: string }[] }).orders.map((r) => r.id);
    expect(await list(`?q=${a.orderId}`)).toEqual([a.orderId]);
    expect(await list(`?q=${a.orderId.slice(0, 10)}`)).toEqual([a.orderId]);
    expect(await list('?status=pending_payment')).toEqual([b.orderId]);
    expect(await list('?status=attention')).toEqual([]);
    await env.DB.prepare("INSERT INTO invoices (order_id, state, provider, idempotency_key, claimed_at) VALUES (?, 'unresolved', 'x', ?, ?)")
      .bind(a.orderId, a.orderId, new Date().toISOString())
      .run();
    expect(await list('?status=attention')).toEqual([a.orderId]);
    expect((await req('/api/admin/orders?q=abc', { headers: asAdmin })).status).toBe(400);
    const html = await (await req(`/admin/?q=${a.orderId}`, { headers: asAdmin })).text();
    expect(html).toContain('dir="rtl"');
    expect(html).toContain(`/admin/orders/${a.orderId}`);
    expect(html).not.toContain(`/admin/orders/${b.orderId}`);
  });

  it('an order: items with house and variant, and its payment, invoice and supplier tracks from the audit log', async () => {
    const o = await sentOrder();
    await processInvoiceJob(env, o.orderId);
    const d = (await (await req(`/api/admin/orders/${o.orderId}`, { headers: asAdmin })).json()) as {
      items: { variant_id: string; house: string | null }[];
      tracks: Record<'payment' | 'invoice' | 'supplier', { action: string }[]>;
    };
    expect(d.items[0]).toMatchObject({ variant_id: 'vase-a:default', house: null });
    expect(d.tracks.payment.map((a) => a.action)).toEqual(['order.created', 'order.paid']);
    expect(d.tracks.invoice.map((a) => a.action)).toEqual(['order.invoiced']);
    expect(d.tracks.supplier.map((a) => a.action)).toEqual(['supplier.submitted']);
    const html = await (await req(`/admin/orders/${o.orderId}`, { headers: asAdmin })).text();
    for (const s of ['תשלום', 'חשבונית', 'ספק ומשלוח', 'vase-a:default', 'נשלחה לספק', 'ספק מדומה']) expect(html, s).toContain(s);
    expect(html).not.toMatch(/<script/i);
  });

  it('"checked by a person" on an unresolved invoice: found (its number recorded) or none (the job runs again); logged with who', async () => {
    const a = await paidOrder();
    const b = await paidOrder();
    for (const o of [a, b])
      await env.DB.prepare("INSERT INTO invoices (order_id, state, provider, idempotency_key, claimed_at) VALUES (?, 'unresolved', 'mock', ?, ?)")
        .bind(o.orderId, o.orderId, new Date().toISOString())
        .run();
    const check = (id: string, body: object) => req(`/api/admin/orders/${id}/invoice-check`, json(body, 'POST', asAdmin));
    expect((await check(a.orderId, { outcome: 'found', invoice_number: 'INV-2026-0042', note: 'נמצא בלוח הבקרה' })).status).toBe(200);
    expect(await one('SELECT state, provider_invoice_id, checked_by FROM invoices WHERE order_id = ?', a.orderId)).toEqual({
      state: 'issued',
      provider_invoice_id: 'INV-2026-0042',
      checked_by: 'dev-token',
    });
    expect((await one<{ invoice_number: string }>('SELECT invoice_number FROM orders WHERE id = ?', a.orderId)).invoice_number).toBe('INV-2026-0042');
    expect((await check(a.orderId, { outcome: 'none', note: 'שוב' })).status).toBe(409);
    expect((await check(b.orderId, { outcome: 'none', note: 'אין כלום אצל הספק' })).status).toBe(200);
    expect(await n('SELECT COUNT(*) AS n FROM invoices WHERE order_id = ?', b.orderId)).toBe(0);
    expect(sent).toContainEqual({ kind: 'issue-invoice', order_id: b.orderId });
    expect(await processInvoiceJob(env, b.orderId)).toBe('invoiced');
    expect(await n("SELECT COUNT(*) AS n FROM audit_log WHERE action = 'invoice.checked' AND actor = 'dev-token'")).toBe(2);
  });

  it('the screen acts through forms from its own origin only; a refund from the form is idempotent by its key', async () => {
    const o = await paidOrder();
    const form = (path: string, body: string, origin = 'http://localhost') =>
      req(path, { method: 'POST', headers: { ...asAdmin, 'content-type': 'application/x-www-form-urlencoded', origin }, body });
    const evil = await form(`/admin/orders/${o.orderId}/refund`, 'amount=10&reason=xyz&key=rf_form_evil1', 'https://evil.example');
    expect(evil.status).toBe(303);
    expect(evil.headers.get('location')).toContain('error=bad_origin');
    expect(await n('SELECT COUNT(*) AS n FROM refunds')).toBe(0);
    const ok = await form(`/admin/orders/${o.orderId}/refund`, 'amount=10.50&reason=%D7%A4%D7%92%D7%9D&key=rf_form_0001');
    expect(ok.headers.get('location')).toBe(`/admin/orders/${o.orderId}?done=refunded`);
    const dup = await form(`/admin/orders/${o.orderId}/refund`, 'amount=10.50&reason=%D7%A4%D7%92%D7%9D&key=rf_form_0001');
    expect(dup.headers.get('location')).toBe(`/admin/orders/${o.orderId}?done=refund_duplicate`);
    expect(await refunded(o.orderId)).toBe(1050);
    const page = await (await req(`/admin/orders/${o.orderId}?done=refunded`, { headers: asAdmin })).text();
    expect(page).toContain('ההחזר בוצע');
    expect(page).toContain('dev-token');
    // the mock supplier, played from the screen: shipped, then the customer sees it
    await processSupplierJob(env, { kind: 'submit-order', order_id: o.orderId }, 1);
    const shipped = await form(`/admin/orders/${o.orderId}/mock-supplier`, 'event=shipped');
    expect(shipped.headers.get('location')).toContain('done=mock_applied');
    expect((await customerView(o)).status_he).toBe('נשלחה');
    // never in production
    env = { ...env, ENVIRONMENT: 'production', ACCESS_TEAM_DOMAIN: '', ADMIN_DEV_BYPASS: '1' };
    expect((await req(`/api/admin/orders/${o.orderId}/mock-supplier`, json({ event: 'delivered' }, 'POST', asAdmin))).status).toBe(403);
  });
});

describe('the new-order alert (NOTIFY_PROVIDER): an interface and a mock that writes a log row', () => {
  it('once per order, with no customer details; production without a channel skips it and never holds the order', async () => {
    const rows: Record<string, unknown>[] = [];
    vi.spyOn(console, 'log').mockImplementation((r: unknown) => void rows.push(r as Record<string, unknown>));
    const o = await paidOrder();
    expect(sent).toContainEqual({ kind: 'notify-order', order_id: o.orderId });
    expect(await processNotifyJob(env, o.orderId, 1)).toBe('sent');
    expect(await processNotifyJob(env, o.orderId, 1)).toBe('skipped');
    const alerts = rows.filter((r) => r.event === 'notify.new_order');
    expect(alerts).toHaveLength(1);
    expect(alerts[0]).toMatchObject({ order_id: o.orderId, total_agorot: o.total, items: 1, admin_path: `/admin/orders/${o.orderId}` });
    expect(JSON.stringify(alerts)).not.toMatch(new RegExp([BUYER.email, BUYER.phone, BUYER.full_name, ADDRESS.street].join('|')));
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    const p = await paidOrder();
    expect(await processNotifyJob({ ...env, ENVIRONMENT: 'production', NOTIFY_PROVIDER: 'UNDECIDED' }, p.orderId, 1)).toBe('skipped');
    expect(warn.mock.calls.some((c) => (c[0] as { event?: string }).event === 'notify.skipped')).toBe(true);
    // a failing channel is retried, then given up loudly: the order is never held
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const failing = { id: 'x', notify: async () => Promise.reject(new Error('down')) };
    const q = await paidOrder();
    expect(await processNotifyJob(env, q.orderId, 1, failing)).toBe('retry');
    expect(await processNotifyJob(env, q.orderId, 3, failing)).toBe('skipped');
    // the deploy check knows the variable: UNDECIDED is the placeholder, mock is refused in production
    expect(
      configIssues({ ENVIRONMENT: 'production', PAYMENT_PROVIDER: 'grow', INVOICE_PROVIDER: 'grow', SUPPLIER_PROVIDER: 'cj', NOTIFY_PROVIDER: 'UNDECIDED' }),
    ).toEqual([]);
    expect(
      configIssues({ ENVIRONMENT: 'production', PAYMENT_PROVIDER: 'grow', INVOICE_PROVIDER: 'grow', SUPPLIER_PROVIDER: 'cj', NOTIFY_PROVIDER: 'mock' }),
    ).toHaveLength(1);
    log.info('done', {});
  });
});
