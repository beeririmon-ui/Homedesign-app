/**
 * S16, the fixes of QA S13–S14 (briefs/site-s16-qa-fixes-2026-11-11.md), each on QA's own case:
 * - ת34: the Admin API acts only for the admin itself (the content type's essence, Origin / Sec-Fetch-Site, or a
 *   service token); a cross-site `text/plain; charset=application/json` request is refused.
 * - ת35: a supplier call that may have reached the supplier, and an order in supplier_error, count as sent: the supplier
 *   is asked by our order number, or a person checks; never a silent full refund.
 * - ת36: one refund call at a time, for every provider (QA's five at once with the same key).
 * - ת37: a malformed tracking link is the number alone, never a 500.
 * - ת38: no customer value in a log row, whatever a provider's error or an exception says.
 * - ת39: every failed send writes a row; /healthz says `degraded` past 30 minutes; the customer reads it honestly.
 * - ת40: a late run whose document differs from the one the takeover recorded writes claim_lost.
 * - ת42: a second cancellation while one waits on the supplier asks the supplier nothing.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { signWebhook } from '@hd/shared';
import { app } from '../src/app';
import type { Env, SupplierJob } from '../src/env';
import { buildSeedSql } from '../scripts/seed';
import { createD1, migrate } from './d1-shim';
import { catalog } from './fixture';
import { processSupplierJob } from '../src/lib/fulfillment';
import { INVOICE_LEASE_MS, processInvoiceJob, type InvoiceProvider } from '../src/lib/invoices';
import { requestRefund } from '../src/lib/refunds';
import { cancelOrder } from '../src/lib/cancel';
import { customerTrackingUrl } from '../src/lib/shipments';
import { resetAccessCache } from '../src/lib/access';
import { errorCode, scrubMessage } from '../src/lib/log';
import { CodedError } from '../src/lib/errors';
import { SUPPLIER_FAILING_MS } from '../src/routes/health';
import type { IssuedRefund, PaymentProvider, RefundInput } from '../src/lib/payments/types';
import { SupplierRefused, type SupplierClient, type SupplierOrderInput } from '../src/lib/suppliers/types';

const SECRET = 'test-webhook-secret-s16-not-a-key';
const DEV_TOKEN = 'dev-admin-token-for-tests-only-s16-0123456789';
const BUYER = { full_name: 'נועה בן־דוד', email: 'buyer.s16@example.com', phone: '052-1234567' };
const ADDRESS = { city: 'באר שבע', street: 'רחוב הערבה', house: '17', apartment: '3', zip: '8410000', notes: '' };
/** the customer's own values, which no log row may carry */
const NEEDLES = ['נועה', 'בן־דוד', 'באר שבע', 'הערבה', 'buyer.s16', '052-1234567', '0521234567'];
let env: Env;
beforeEach(() => {
  const DB = createD1();
  migrate(DB, buildSeedSql(catalog));
  env = {
    DB,
    SUPPLIER_QUEUE: { send: vi.fn(async () => undefined), sendBatch: vi.fn() } as unknown as Queue<SupplierJob>,
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
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  resetAccessCache();
});

const req = (path: string, init?: RequestInit) => app.request(`http://localhost${path}`, init, env);
const json = (body: unknown, method = 'POST', headers: Record<string, string> = {}): RequestInit => ({
  method,
  headers: { 'content-type': 'application/json', ...headers },
  body: JSON.stringify(body),
});
async function paidOrder() {
  const { id: cart } = (await (await req('/api/cart', { method: 'POST' })).json()) as { id: string };
  expect((await req(`/api/cart/${cart}/items`, json({ variant_id: 'vase-a:default', qty: 1 }, 'PUT'))).status).toBe(200);
  const body = { cart_id: cart, customer: BUYER, address: ADDRESS, shipping_method: 'express', consents: { terms: true, marketing: false } };
  const r = (await (await req('/api/checkout', json(body))).json()) as { order_id: string; order_token: string };
  const o = (await env.DB.prepare('SELECT payment_session_id, total_agorot FROM orders WHERE id = ?')
    .bind(r.order_id)
    .first<{ payment_session_id: string; total_agorot: number }>())!;
  const ev = JSON.stringify({ id: `evt_${r.order_id}`, type: 'payment.succeeded', session_id: o.payment_session_id, amount_agorot: o.total_agorot });
  const paid = await req('/api/webhooks/payment/mock', {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-mock-signature': await signWebhook(SECRET, ev, Math.floor(Date.now() / 1000)) },
    body: ev,
  });
  expect(((await paid.json()) as { outcome: string }).outcome).toBe('paid');
  return { id: r.order_id, token: r.order_token, total: o.total_agorot };
}
const one = async <T>(sql: string, ...b: unknown[]) =>
  (await env.DB.prepare(sql)
    .bind(...b)
    .first<T>())!;
const n = async (sql: string, ...b: unknown[]) => (await one<{ n: number }>(sql, ...b)).n;
const status = async (id: string) => (await one<{ status: string }>('SELECT status FROM orders WHERE id = ?', id)).status;
const ship = async (id: string) =>
  one<{ status: string; reach: string; failing_since: string | null; supplier_order_id: string | null; last_error: string | null }>(
    'SELECT status, reach, failing_since, supplier_order_id, last_error FROM supplier_shipments WHERE order_id = ?',
    id,
  );
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
/** every console row while `fn` runs, as text */
async function logged(fn: () => Promise<unknown>): Promise<string[]> {
  const rows: string[] = [];
  for (const m of ['log', 'info', 'warn', 'error', 'debug'] as const)
    vi.spyOn(console, m).mockImplementation((...a: unknown[]) => void rows.push(JSON.stringify(a)));
  try {
    await fn();
  } finally {
    vi.restoreAllMocks();
  }
  return rows;
}

/** a supplier like a network one: what it holds, and how it answers */
function supplier(o: { hangMs?: number; failWith?: (i: SupplierOrderInput) => Error; find?: boolean; findFails?: boolean } = {}) {
  const orders: string[] = [];
  const cancels: string[] = [];
  const finds: string[] = [];
  const c: SupplierClient & { orders: string[]; cancels: string[]; finds: string[] } = {
    id: 'mock',
    orders,
    cancels,
    finds,
    async submitOrder(input) {
      if (o.failWith) throw o.failWith(input);
      orders.push(input.order_id); // created at the supplier; the answer may come too late
      if (o.hangMs) await sleep(o.hangMs);
      return { supplier_order_id: `SUP-${input.order_id}`, raw: {} };
    },
    async cancelOrder(id) {
      cancels.push(id);
      return { outcome: 'requested' };
    },
  };
  if (o.find)
    c.findOrder = async (our) => {
      finds.push(our);
      if (o.findFails) throw new Error(`lookup failed for "${BUYER.full_name}"`);
      return orders.includes(our) ? { supplier_order_id: `SUP-${our}` } : null;
    };
  return c;
}

/** a payment provider: counts the refunds it makes; can be slow, not deduplicating, and askable */
function payments(o: { idempotent?: boolean; find?: boolean; delayMs?: number; failOnce?: boolean } = {}) {
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
      await sleep(o.delayMs ?? 2);
      if (p.refundsIdempotent && byKey.has(idempotency_key)) return byKey.get(idempotency_key)!;
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

// ---------------------------------------------------------------- ת34
const b64u = (b: ArrayBuffer | string) =>
  Buffer.from(typeof b === 'string' ? b : new Uint8Array(b))
    .toString('base64')
    .replace(/=+$/, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_');
async function accessSetup() {
  const k = (await crypto.subtle.generateKey(
    { name: 'RSASSA-PKCS1-v1_5', modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: 'SHA-256' },
    true,
    ['sign', 'verify'],
  )) as CryptoKeyPair;
  const jwk = { ...(await crypto.subtle.exportKey('jwk', k.publicKey)), kid: 'k1', alg: 'RS256', use: 'sig' };
  vi.stubGlobal('fetch', async () => new Response(JSON.stringify({ keys: [jwk] }), { headers: { 'content-type': 'application/json' } }));
  env.ACCESS_TEAM_DOMAIN = 'studio.cloudflareaccess.com';
  env.ACCESS_AUD = 'aud-s16';
  const sign = async (claims: object) => {
    const h = b64u(JSON.stringify({ alg: 'RS256', kid: 'k1' }));
    const p = b64u(JSON.stringify({ aud: ['aud-s16'], iss: 'https://studio.cloudflareaccess.com', exp: Math.floor(Date.now() / 1000) + 600, ...claims }));
    return `${h}.${p}.${b64u(await crypto.subtle.sign('RSASSA-PKCS1-v1_5', k.privateKey, new TextEncoder().encode(`${h}.${p}`)))}`;
  };
  return { person: await sign({ email: 'owner@example.com' }), service: await sign({ common_name: 'studio-client.access', sub: '' }) };
}

describe('ת34: the Admin API acts only for the admin itself', () => {
  it('QA A4: a cross-site "text/plain; charset=application/json" cancel is refused, and the order is untouched', async () => {
    const { person } = await accessSetup();
    const o = await paidOrder();
    const r = await req(`/api/admin/orders/${o.id}/cancel`, {
      method: 'POST',
      // what a page elsewhere can send without a preflight, with the owner's Access login riding along
      headers: {
        'content-type': 'text/plain; charset=application/json',
        'cf-access-jwt-assertion': person,
        origin: 'https://evil.example',
        'sec-fetch-site': 'cross-site',
      },
      body: JSON.stringify({ reason: 'csrf probe' }),
    });
    expect(r.status).toBe(403);
    expect(await status(o.id)).toBe('paid');
    // and the content type alone is refused too, even from the admin's own origin
    const same = await req(`/api/admin/orders/${o.id}/cancel`, {
      method: 'POST',
      headers: { 'content-type': 'text/plain; charset=application/json', 'cf-access-jwt-assertion': person, origin: 'http://localhost' },
      body: JSON.stringify({ reason: 'csrf probe' }),
    });
    expect(same.status).toBe(400);
    expect(((await same.json()) as { error: string }).error).toBe('expected_json');
    expect(await status(o.id)).toBe('paid');
    expect(await n('SELECT COUNT(*) AS n FROM refunds WHERE order_id = ?', o.id)).toBe(0);
  });

  it('the content type: only an essence of exactly application/json, on every JSON endpoint', async () => {
    const { id: cart } = (await (await req('/api/cart', { method: 'POST' })).json()) as { id: string };
    const put = (ct: string) =>
      req(`/api/cart/${cart}/items`, { method: 'PUT', headers: { 'content-type': ct }, body: JSON.stringify({ variant_id: 'vase-a:default', qty: 1 }) });
    for (const bad of ['text/plain; charset=application/json', 'text/plain', 'application/jsonp', 'application/x-www-form-urlencoded; a=application/json', ''])
      expect((await put(bad)).status, bad).toBe(400);
    for (const good of ['application/json', 'application/json; charset=utf-8', 'Application/JSON']) expect((await put(good)).status, good).toBe(200);
  });

  it('a person (Access login): only with this origin, or Sec-Fetch-Site same-origin; a foreign or missing marker is 403', async () => {
    const { person } = await accessSetup();
    const o = await paidOrder();
    const cancel = (h: Record<string, string>) =>
      req(`/api/admin/orders/${o.id}/cancel`, json({ reason: 'בדיקה' }, 'POST', { 'cf-access-jwt-assertion': person, ...h }));
    const markers: Record<string, string>[] = [
      { origin: 'https://evil.example' },
      { origin: 'null' },
      { 'sec-fetch-site': 'cross-site' },
      { 'sec-fetch-site': 'same-site' },
      { origin: 'http://localhost', 'sec-fetch-site': 'cross-site' },
      {},
    ];
    for (const h of markers) {
      const r = await cancel(h);
      expect(r.status, JSON.stringify(h)).toBe(403);
      expect(((await r.json()) as { error: string }).error).toBe('cross_site_request');
    }
    expect(await status(o.id)).toBe('paid');
    // the reads stay open to the person without a marker
    expect((await req(`/api/admin/orders/${o.id}`, { headers: { 'cf-access-jwt-assertion': person } })).status).toBe(200);
    const ok = await cancel({ origin: 'http://localhost', 'sec-fetch-site': 'same-origin' });
    expect(ok.status).toBe(200);
    expect(await status(o.id)).toBe('canceled');
    expect((await one<{ actor: string }>("SELECT actor FROM audit_log WHERE subject = ? AND action = 'order.canceled'", o.id)).actor).toBe('owner@example.com');
  });

  it('a service token (the studio): no browser markers needed; the actor names the token; a foreign Origin is still refused', async () => {
    const { service } = await accessSetup();
    const o = await paidOrder();
    const foreign = await req(
      `/api/admin/orders/${o.id}/cancel`,
      json({ reason: 'בדיקה' }, 'POST', { 'cf-access-jwt-assertion': service, origin: 'https://evil.example' }),
    );
    expect(foreign.status).toBe(403);
    const r = await req(`/api/admin/orders/${o.id}/cancel`, json({ reason: 'בדיקה' }, 'POST', { 'cf-access-jwt-assertion': service }));
    expect(r.status).toBe(200);
    expect((await one<{ actor: string }>("SELECT actor FROM audit_log WHERE subject = ? AND action = 'order.canceled'", o.id)).actor).toBe(
      'service:studio-client.access',
    );
  });

  it('the screen’s forms: the same rule (a foreign Origin is bad_origin); the local dev token acts without markers', async () => {
    env.ADMIN_DEV_TOKEN = DEV_TOKEN;
    const o = await paidOrder();
    const form = (h: Record<string, string>) =>
      req(`/admin/orders/${o.id}/cancel`, {
        method: 'POST',
        headers: { 'content-type': 'application/x-www-form-urlencoded', 'x-hd-dev-admin': DEV_TOKEN, ...h },
        body: 'reason=%D7%91%D7%93%D7%99%D7%A7%D7%94',
      });
    const bad = await form({ origin: 'https://evil.example' });
    expect(bad.status).toBe(303);
    expect(bad.headers.get('location')).toContain('error=bad_origin');
    expect(await status(o.id)).toBe('paid');
    const api = await req(
      `/api/admin/orders/${o.id}/cancel`,
      json({ reason: 'בדיקה' }, 'POST', { 'x-hd-dev-admin': DEV_TOKEN, origin: 'https://evil.example' }),
    );
    expect(api.status).toBe(403);
    const ok = await req(`/api/admin/orders/${o.id}/cancel`, json({ reason: 'בדיקה' }, 'POST', { 'x-hd-dev-admin': DEV_TOKEN }));
    expect(ok.status).toBe(200);
  });
});

// ---------------------------------------------------------------- ת35
describe('ת35: a submit that may have reached the supplier counts as sent; never a silent full refund', () => {
  it('QA B4: the supplier call timed out (the supplier holds the order), and it cannot be asked: left to a person, nothing refunded', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    const sup = supplier({ hangMs: 80 });
    const o = await paidOrder();
    expect(await processSupplierJob(env, { kind: 'submit-order', order_id: o.id }, 1, { client: sup, callTimeoutMs: 20 })).toBe('retry');
    expect(await ship(o.id)).toMatchObject({ status: 'failed', reach: 'maybe' });
    await sleep(100);
    const p = payments();
    const c = await cancelOrder(env, o.id, 'owner@example.com', 'הלקוח ביקש', { supplier: sup, payment: p, callTimeoutMs: 20 });
    expect(c).toMatchObject({ error: true, status: 409, code: 'supplier_check_needed' });
    expect(p.made).toHaveLength(0);
    expect(await status(o.id)).toBe('paid');
    expect(sup.orders).toHaveLength(1);
    expect(await n("SELECT COUNT(*) AS n FROM audit_log WHERE subject = ? AND action = 'order.cancel_needs_person'", o.id)).toBe(1);
    // the admin's list shows it as needing a person
    env.ADMIN_DEV_TOKEN = DEV_TOKEN;
    const list = (await (await req('/api/admin/orders?status=attention', { headers: { 'x-hd-dev-admin': DEV_TOKEN } })).json()) as { orders: { id: string }[] };
    expect(list.orders.map((x) => x.id)).toContain(o.id);
  });

  it('asked by our order number: the supplier holds it → the after-supplier path (a cancellation request, no refund yet)', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const sup = supplier({ hangMs: 80, find: true });
    const o = await paidOrder();
    await processSupplierJob(env, { kind: 'submit-order', order_id: o.id }, 1, { client: sup, callTimeoutMs: 20 });
    await sleep(100);
    const p = payments();
    const c = await cancelOrder(env, o.id, 'owner@example.com', 'הלקוח ביקש', { supplier: sup, payment: p, callTimeoutMs: 20 });
    expect(c).toMatchObject({ outcome: 'requested', stage: 'after_supplier' });
    expect(sup.finds).toEqual([o.id]);
    expect(sup.cancels).toEqual([`SUP-${o.id}`]);
    expect(p.made).toHaveLength(0);
    expect(await ship(o.id)).toMatchObject({ status: 'cancel_requested', supplier_order_id: `SUP-${o.id}`, reach: 'none' });
    expect(await n("SELECT COUNT(*) AS n FROM audit_log WHERE subject = ? AND action = 'supplier.found_by_order'", o.id)).toBe(1);
  });

  it('asked by our order number: the supplier holds none → canceled before the supplier, refunded in full', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    // a server error before the supplier created anything (it may have, as far as we know)
    const sup = supplier({ find: true, failWith: () => Object.assign(new Error('upstream 502'), { status: 502 }) });
    const o = await paidOrder();
    await processSupplierJob(env, { kind: 'submit-order', order_id: o.id }, 1, { client: sup, callTimeoutMs: 20 });
    expect(await ship(o.id)).toMatchObject({ status: 'failed', reach: 'maybe' });
    // a moment after the failed call, the supplier is not asked yet: it may still be creating the order
    const p = payments();
    expect(await cancelOrder(env, o.id, 'a', 'בדיקה', { supplier: sup, payment: p, callTimeoutMs: 60_000 })).toMatchObject({
      code: 'supplier_submit_in_progress',
    });
    await sleep(30);
    const c = await cancelOrder(env, o.id, 'owner@example.com', 'הלקוח ביקש', { supplier: sup, payment: p, callTimeoutMs: 20 });
    expect(c).toMatchObject({ outcome: 'canceled', stage: 'before_supplier' });
    expect(p.made.reduce((s, x) => s + x.amount, 0)).toBe(o.total);
    expect(await ship(o.id)).toMatchObject({ status: 'canceled', reach: 'checked' });
    // the supplier job then sends nothing
    expect(await processSupplierJob(env, { kind: 'submit-order', order_id: o.id }, 2, { client: sup })).toBe('skipped');
    expect(sup.orders).toHaveLength(0);
  });

  it('a refusal created nothing: the order is before the supplier (canceled and refunded), and the failure stays "none"', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const sup = supplier({ failWith: () => new SupplierRefused('cj_order_api_docs_needed') });
    const o = await paidOrder();
    await processSupplierJob(env, { kind: 'submit-order', order_id: o.id }, 1, { client: sup });
    expect(await ship(o.id)).toMatchObject({ status: 'failed', reach: 'none' });
    const p = payments();
    expect(await cancelOrder(env, o.id, 'a', 'בדיקה', { supplier: sup, payment: p })).toMatchObject({ outcome: 'canceled', stage: 'before_supplier' });
    expect(p.made.reduce((s, x) => s + x.amount, 0)).toBe(o.total);
  });

  it('a timeout, then refusals: the order stays "maybe" (a later refusal never clears it)', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const o = await paidOrder();
    await processSupplierJob(env, { kind: 'submit-order', order_id: o.id }, 1, { client: supplier({ hangMs: 60 }), callTimeoutMs: 15 });
    await sleep(70);
    await processSupplierJob(env, { kind: 'submit-order', order_id: o.id }, 2, {
      client: supplier({ failWith: () => new SupplierRefused('duplicate_order') }),
    });
    expect(await ship(o.id)).toMatchObject({ status: 'failed', reach: 'maybe' });
  });

  it('supplier_error counts as sent: a person checks at the supplier ("none" → canceled and refunded; "found" → the after-supplier path)', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    env.ADMIN_DEV_TOKEN = DEV_TOKEN;
    const admin = { 'x-hd-dev-admin': DEV_TOKEN };
    for (const outcome of ['none', 'found'] as const) {
      const o = await paidOrder();
      const refusing = supplier({ failWith: () => new SupplierRefused('cj_order_api_docs_needed') });
      for (let a = 1; a <= 5; a++) await processSupplierJob(env, { kind: 'submit-order', order_id: o.id }, a, { client: refusing });
      expect(await status(o.id)).toBe('supplier_error');
      // the mock supplier cannot be asked by our order number: a person
      const first = await req(`/api/admin/orders/${o.id}/cancel`, json({ reason: 'הלקוח ביקש' }, 'POST', admin));
      expect(first.status).toBe(409);
      expect(((await first.json()) as { error: string }).error).toBe('supplier_check_needed');
      expect(await n('SELECT COUNT(*) AS n FROM refunds WHERE order_id = ?', o.id)).toBe(0);
      const check = await req(
        `/api/admin/orders/${o.id}/supplier-check`,
        json(outcome === 'found' ? { outcome, supplier_order_id: 'CJ-777001', note: 'נמצאה בלוח של הספק' } : { outcome, note: 'אין אצל הספק' }, 'POST', admin),
      );
      expect(check.status).toBe(200);
      const c = (await (await req(`/api/admin/orders/${o.id}/cancel`, json({ reason: 'הלקוח ביקש' }, 'POST', admin))).json()) as {
        outcome: string;
        stage: string;
      };
      if (outcome === 'none') {
        expect(c).toMatchObject({ outcome: 'canceled', stage: 'before_supplier' });
        expect(await n("SELECT COALESCE(SUM(amount_agorot), 0) AS n FROM refunds WHERE order_id = ? AND state = 'refunded'", o.id)).toBe(o.total);
      } else {
        expect(c).toMatchObject({ outcome: 'requested', stage: 'after_supplier' });
        expect(await n('SELECT COUNT(*) AS n FROM refunds WHERE order_id = ?', o.id)).toBe(0);
        expect(await ship(o.id)).toMatchObject({ status: 'cancel_requested', supplier_order_id: 'CJ-777001' });
      }
      expect(await n("SELECT COUNT(*) AS n FROM audit_log WHERE subject = ? AND action LIKE 'supplier.%_by_order' AND actor = 'dev-token'", o.id)).toBe(1);
    }
  });

  it('an order whose shipment was never sent (no supplier configured) is still before the supplier', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const o = await paidOrder();
    const prod = { ...env, ENVIRONMENT: 'production' as const, SUPPLIER_PROVIDER: 'mock' };
    for (let a = 1; a <= 5; a++) await processSupplierJob(prod, { kind: 'submit-order', order_id: o.id }, a);
    expect(await status(o.id)).toBe('supplier_error');
    expect((await ship(o.id)).status).toBe('queued');
    const p = payments();
    expect(await cancelOrder(env, o.id, 'a', 'בדיקה', { payment: p })).toMatchObject({ outcome: 'canceled', stage: 'before_supplier' });
    expect(p.made.reduce((s, x) => s + x.amount, 0)).toBe(o.total);
  });
});

// ---------------------------------------------------------------- ת42
describe('ת42: a second cancellation while one waits on the supplier', () => {
  it('returns the state, asks the supplier nothing, and writes no second request', async () => {
    const sup = supplier();
    const o = await paidOrder();
    expect(await processSupplierJob(env, { kind: 'submit-order', order_id: o.id }, 1, { client: sup })).toBe('submitted');
    expect(await cancelOrder(env, o.id, 'a', 'בדיקה', { supplier: sup })).toMatchObject({ outcome: 'requested' });
    expect(await cancelOrder(env, o.id, 'a', 'שוב', { supplier: sup })).toMatchObject({ outcome: 'requested', stage: 'after_supplier' });
    expect(sup.cancels).toHaveLength(1);
    expect(await n("SELECT COUNT(*) AS n FROM audit_log WHERE subject = ? AND action = 'order.cancel_requested'", o.id)).toBe(1);
    expect(await n("SELECT COUNT(*) AS n FROM audit_log WHERE subject = ? AND action = 'supplier.cancel_requested'", o.id)).toBe(1);
  });
});

// ---------------------------------------------------------------- ת36
describe('ת36: one refund call at a time, for every kind of provider', () => {
  it('QA C2: a provider that does not deduplicate but can be asked, the same key five times at once → one refund', async () => {
    const o = await paidOrder();
    const p = payments({ idempotent: false, find: true, delayMs: 30 });
    const out = await Promise.all(
      Array.from({ length: 5 }, () => requestRefund(env, { orderId: o.id, amount: 1000, reason: 'qa', key: `qa_same_${o.id}`, actor: 'qa' }, { provider: p })),
    );
    expect(p.made).toHaveLength(1);
    expect(out.filter((r) => r.ok)).toHaveLength(1);
    expect(out.filter((r) => !r.ok).map((r) => (r.ok ? '' : r.code))).toEqual(['in_progress', 'in_progress', 'in_progress', 'in_progress']);
    // once done, the same key again is the first refund
    expect(await requestRefund(env, { orderId: o.id, amount: 1000, reason: 'qa', key: `qa_same_${o.id}`, actor: 'qa' }, { provider: p })).toMatchObject({
      ok: true,
      duplicate: true,
    });
    expect(p.made).toHaveLength(1);
  });

  it('every kind: a deduplicating provider, and one that can be neither asked nor deduplicates, also make one call', async () => {
    for (const kind of [{ idempotent: true }, { idempotent: false }] as const) {
      const o = await paidOrder();
      const p = payments({ ...kind, delayMs: 30 });
      const calls = vi.spyOn(p, 'refund');
      await Promise.all(
        Array.from({ length: 5 }, () => requestRefund(env, { orderId: o.id, amount: 1000, reason: 'qa', key: `qa_k_${o.id}`, actor: 'qa' }, { provider: p })),
      );
      expect(calls, JSON.stringify(kind)).toHaveBeenCalledTimes(1);
    }
  });

  it('after a failure: within the lease 409; after it the provider is asked, and called again only when it holds none', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const o = await paidOrder();
    let clock = Date.now();
    // the provider made the refund, then the answer was lost (a timeout): asking finds it, no second refund
    const p = payments({ idempotent: false, find: true, failOnce: true });
    const ask = () => requestRefund(env, { orderId: o.id, amount: 1000, reason: 'r', key: 'rf_s16_lease', actor: 'a' }, { provider: p, now: () => clock });
    expect(await ask()).toMatchObject({ ok: false, code: 'provider_failed' });
    expect(await ask()).toMatchObject({ ok: false, code: 'in_progress' });
    clock += INVOICE_LEASE_MS + 1000;
    expect(await ask()).toMatchObject({ ok: true, amount_agorot: 1000 });
    expect(p.made).toHaveLength(1);
    // a deduplicating provider gets the lease back when its call fails: the same key again at once
    const q = payments({ idempotent: true, failOnce: true });
    const ask2 = () => requestRefund(env, { orderId: o.id, amount: 500, reason: 'r', key: 'rf_s16_dedupe', actor: 'a' }, { provider: q });
    expect(await ask2()).toMatchObject({ ok: false, code: 'provider_failed' });
    expect(await ask2()).toMatchObject({ ok: true, amount_agorot: 500 });
    expect(q.made).toHaveLength(1);
  });
});

// ---------------------------------------------------------------- ת37
describe('ת37: a malformed tracking link', () => {
  it('is the number alone, and the customer’s order page answers 200', async () => {
    expect(customerTrackingUrl('https://parcelsapp.com/he/tracking/%E0%A4%A')).toBeNull();
    expect(customerTrackingUrl('https://parcelsapp.com/he/tracking/IL12345678')).toBe('https://parcelsapp.com/he/tracking/IL12345678');
    const o = await paidOrder();
    await processSupplierJob(env, { kind: 'submit-order', order_id: o.id }, 1);
    await env.DB.prepare(
      "UPDATE supplier_shipments SET status = 'shipped', tracking_number = 'IL12345678', tracking_url = ?, shipped_at = ? WHERE order_id = ?",
    )
      .bind('https://parcelsapp.com/he/tracking/%E0%A4%A', new Date().toISOString(), o.id)
      .run();
    const r = await req(`/api/orders/${o.id}`, { headers: { 'x-order-token': o.token } });
    expect(r.status).toBe(200);
    expect(((await r.json()) as { shipments: unknown[] }).shipments).toEqual([expect.objectContaining({ tracking_number: 'IL12345678', tracking_url: null })]);
  });
});

// ---------------------------------------------------------------- ת38
describe('ת38: no customer value in any log row, whatever the error says', () => {
  const echo = (i: { full_name?: string; city?: string; street?: string; phone?: string; email?: string }) =>
    new Error(`400 invalid consignee "${i.full_name}" at ${i.street} 17, ${i.city}; tel ${i.phone}; ${i.email}`);

  it('QA F: a supplier’s and an invoice provider’s error that echo the buyer, and an exception with the name and address', async () => {
    const o1 = await paidOrder();
    const o2 = await paidOrder();
    const o3 = await paidOrder();
    const failingInvoices: InvoiceProvider = {
      id: 'mock',
      idempotent: true,
      async issue(input) {
        throw echo({ ...input.customer, street: ADDRESS.street, city: ADDRESS.city });
      },
    };
    const brokenDb = {
      ...env,
      DB: {
        prepare: () => ({
          bind: () => ({
            first: async () => {
              throw new Error(`failed for ${BUYER.full_name}, ${ADDRESS.street} 17, ${ADDRESS.city} (${BUYER.email}) 'בן־דוד'`);
            },
          }),
        }),
      } as unknown as D1Database,
    };
    const rows = await logged(async () => {
      await processSupplierJob(env, { kind: 'submit-order', order_id: o1.id }, 1, { client: supplier({ failWith: (i) => echo(i.ship_to) }) });
      await processInvoiceJob(env, o2.id, failingInvoices);
      await app.request(`http://localhost/api/orders/${o3.id}`, { headers: { 'x-order-token': o3.token } }, brokenDb);
      await cancelOrder(env, o1.id, 'a', 'בדיקה', { supplier: supplier({ find: true, findFails: true }), callTimeoutMs: 1 });
    });
    const leaks = rows.flatMap((r) => NEEDLES.filter((x) => r.includes(x)).map((x) => `${x} in ${r.slice(0, 80)}`));
    expect(leaks).toEqual([]);
    expect(rows.some((r) => r.includes('supplier.submit_failed') && r.includes('"code":"Error"'))).toBe(true);
    expect(rows.some((r) => r.includes('request.unhandled'))).toBe(true);
    // the full text stays in D1, behind Access
    expect((await ship(o1.id)).last_error).toContain(BUYER.full_name);
    expect((await one<{ last_error: string }>('SELECT last_error FROM invoices WHERE order_id = ?', o2.id)).last_error).toContain(BUYER.full_name);
  });

  it('the code of an error, never its text; the scrub of an exception’s message', () => {
    expect(errorCode(new SupplierRefused('cj_order_api_docs_needed'))).toBe('cj_order_api_docs_needed');
    expect(errorCode(Object.assign(new Error('x'), { status: 503 }))).toBe('http_503');
    expect(errorCode(Object.assign(new Error(`no answer`), { name: 'CallTimedOut' }))).toBe('timeout');
    // S19 (QA ת53): our own refusal is a CodedError; the same words from anyone else's error are no code
    expect(errorCode(new CodedError('set_composition_missing', 'vase-a:default'))).toBe('set_composition_missing');
    expect(errorCode(new Error('set_composition_missing: vase-a:default'))).toBe('Error');
    expect(errorCode(new Error(`invalid consignee ${BUYER.full_name}`))).toBe('Error');
    expect(scrubMessage(`Unexpected token 'x', "{"full_name":"${BUYER.full_name}"... is not valid JSON`)).not.toContain('נועה');
    expect(scrubMessage(`failed for ${BUYER.full_name}, ${ADDRESS.street} 17, ${ADDRESS.city}`)).toBe('failed for [he], [he] 17, [he]');
    expect(scrubMessage('D1_ERROR: no such column: reach')).toBe('D1_ERROR: no such column: reach');
  });
});

// ---------------------------------------------------------------- ת39
describe('ת39: a failing supplier is seen: a row per failed send, /healthz, and the customer’s page', () => {
  it('QA E2: five failed sends → five rows by code; /healthz degraded past 30 minutes; ok again once a send succeeds', async () => {
    const o = await paidOrder();
    // S17 (ת48): a supplier documented to deduplicate by our order number is sent again after a failure that may have
    // reached it (one that cannot be asked and does not deduplicate is left to a person: api/test/s17.test.ts)
    const failing = { ...supplier({ failWith: () => new Error(`cj: the create-order call refused for ${BUYER.full_name}`) }), dedupesByOrderId: true };
    const rows = await logged(async () => {
      for (let a = 1; a <= 5; a++) await processSupplierJob(env, { kind: 'submit-order', order_id: o.id }, a, { client: failing });
    });
    const sends = rows.filter((r) => r.includes('supplier.submit_failed'));
    expect(sends).toHaveLength(5);
    for (const r of sends) expect(r).toMatch(/"level":"error".*"order_id":"\d{10}".*"supplier":"mock".*"code":"Error","may_have_reached":true/);
    expect(await status(o.id)).toBe('supplier_error');
    const health = async () => {
      const r = await req('/healthz');
      return { code: r.status, body: await r.json() };
    };
    // within the retries' time: ok (the shipment has been failing for less than 30 minutes)
    expect(await health()).toEqual({ code: 200, body: { ok: true, checks: { db: 'ok', queue: 'ok', supplier: 'ok' } } });
    await env.DB.prepare('UPDATE supplier_shipments SET failing_since = ? WHERE order_id = ?')
      .bind(new Date(Date.now() - SUPPLIER_FAILING_MS - 60_000).toISOString(), o.id)
      .run();
    vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    expect(await health()).toEqual({ code: 503, body: { ok: false, checks: { db: 'ok', queue: 'ok', supplier: 'degraded' } } });
    // the customer reads it honestly, in neutral words, without the supplier (S17, §7: still "בהכנה", with the line)
    const view = (await (await req(`/api/orders/${o.id}`, { headers: { 'x-order-token': o.token } })).json()) as { status_he: string };
    expect(view.status_he).toBe('בהכנה');
    // the order is canceled (a person checked: none at the supplier): nothing is failing any more
    env.ADMIN_DEV_TOKEN = DEV_TOKEN;
    await req(`/api/admin/orders/${o.id}/supplier-check`, json({ outcome: 'none', note: 'אין אצל הספק' }, 'POST', { 'x-hd-dev-admin': DEV_TOKEN }));
    await req(`/api/admin/orders/${o.id}/cancel`, json({ reason: 'תקלה מול הספק' }, 'POST', { 'x-hd-dev-admin': DEV_TOKEN }));
    expect(await status(o.id)).toBe('canceled');
    expect((await health()).code).toBe(200);
  });

  it('a send that succeeds after failures clears the run of failures', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const o = await paidOrder();
    await processSupplierJob(env, { kind: 'submit-order', order_id: o.id }, 1, { client: supplier({ failWith: () => new SupplierRefused('busy') }) });
    expect((await ship(o.id)).failing_since).toBeTruthy();
    expect(await processSupplierJob(env, { kind: 'submit-order', order_id: o.id }, 2, { client: supplier() })).toBe('submitted');
    expect(await ship(o.id)).toMatchObject({ status: 'submitted', failing_since: null, last_error: null });
  });
});

// ---------------------------------------------------------------- ת40
describe('ת40: the late run’s document differs from the one the takeover recorded → claim_lost', () => {
  it('the invoice: the takeover issued and recorded, the late run’s answer is a second invoice', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const o = await paidOrder();
    let release!: () => void;
    const hang = new Promise<void>((r) => (release = r));
    let k = 0;
    // a provider that does not deduplicate (each call a new number) and can be asked (nothing found for the late call yet)
    const provider = (wait?: Promise<void>): InvoiceProvider => ({
      id: 'mock',
      idempotent: false,
      async issue(input) {
        if (wait) await wait;
        return { invoice_id: `INV-${input.order_id}-${++k}`, url: null };
      },
      async find() {
        return null;
      },
    });
    let clock = Date.now();
    const late = processInvoiceJob(env, o.id, provider(hang), { now: () => clock, callTimeoutMs: 5_000 });
    await sleep(20);
    clock += INVOICE_LEASE_MS + 1000;
    expect(await processInvoiceJob(env, o.id, provider(), { now: () => clock })).toBe('invoiced');
    release();
    expect(await late).toBe('retry');
    expect(await n("SELECT COUNT(*) AS n FROM audit_log WHERE subject = ? AND action = 'invoice.claim_lost'", o.id)).toBe(1);
    expect(await n("SELECT COUNT(*) AS n FROM audit_log WHERE subject = ? AND action = 'order.invoiced'", o.id)).toBe(1);
  });
});
