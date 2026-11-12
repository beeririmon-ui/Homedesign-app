/**
 * S17, the fixes of QA S15–S16 before real suppliers (briefs/site-s17-qa-fixes-2026-11-11.md):
 * - ת46: a known order's customer values leave every log row (Latin or Hebrew, any case, a phone by its digits); an
 *   error of an unknown order is logged in production by its name and code only; PHONE_RE knows 972 and 00972;
 *   errorCode takes `code` only from our own classes.
 * - ת47: a `submitting` claim past its lease counts as failing for /healthz.
 * - ת48: a send that may have reached the supplier is asked about first (findOrder); one that cannot be asked is sent
 *   again only when its adapter documents deduplication by our order number, otherwise a person checks.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { signWebhook } from '@hd/shared';
import { app } from '../src/app';
import type { Env, SupplierJob } from '../src/env';
import { buildSeedSql } from '../scripts/seed';
import { createD1, migrate } from './d1-shim';
import { catalog } from './fixture';
import { SUBMIT_LEASE_MS, processSupplierJob } from '../src/lib/fulfillment';
import { cancelOrder } from '../src/lib/cancel';
import { configureLog, errorCode, knownValues, logRow, orderLog, scrub, stripKnown } from '../src/lib/log';
import { HttpError } from '../src/lib/http';
import { SUPPLIER_FAILING_MS } from '../src/routes/health';
import { SupplierRefused, type SupplierClient, type SupplierOrderInput } from '../src/lib/suppliers/types';

const SECRET = 'test-webhook-secret-s17-not-a-key';
const DEV_TOKEN = 'dev-admin-token-for-tests-only-s17-0123456789';
/** QA's leak (ת46): a customer who typed their details in Latin letters */
const LATIN = { full_name: 'Orna Bodeket', email: 'orna.bodeket@example.com', phone: '052-7654321' };
const LATIN_ADDRESS = { city: 'Mitzpe Bdika', street: 'Sderot HaBodkim', house: '17', apartment: '3', zip: '8410000', notes: '' };
const HEBREW = { full_name: 'נועה בן־דוד', email: 'buyer.s17@example.com', phone: '052-1234567' };
const HEBREW_ADDRESS = { city: 'באר שבע', street: 'רחוב הערבה', house: '17', apartment: '3', zip: '8410000', notes: '' };
const NEEDLES = ['Orna', 'orna', 'ORNA', 'Bodeket', 'HaBodkim', 'Habodkim', 'Mitzpe', 'Bdika', 'orna.bodeket', '7654321', '765-4321', '8410000'];

let env: Env;
let queued: SupplierJob[];
beforeEach(() => {
  const DB = createD1();
  migrate(DB, buildSeedSql(catalog));
  queued = [];
  env = {
    DB,
    SUPPLIER_QUEUE: {
      send: vi.fn(async (j: SupplierJob) => void queued.push(j)),
      sendBatch: vi.fn(),
    } as unknown as Queue<SupplierJob>,
    ENVIRONMENT: 'test',
    PAYMENT_PROVIDER: 'mock',
    SUPPLIER_PROVIDER: 'mock',
    INVOICE_PROVIDER: 'mock',
    NOTIFY_PROVIDER: 'mock',
    ACCESS_TEAM_DOMAIN: '',
    ACCESS_AUD: '',
    PAYMENT_WEBHOOK_SECRET: SECRET,
    ADMIN_DEV_TOKEN: DEV_TOKEN,
  };
  configureLog(env);
});
afterEach(() => {
  vi.restoreAllMocks();
  configureLog({ ENVIRONMENT: 'production' });
});

const req = (path: string, init?: RequestInit, e: Env = env) => app.request(`http://localhost${path}`, init, e);
const json = (body: unknown, method = 'POST', headers: Record<string, string> = {}): RequestInit => ({
  method,
  headers: { 'content-type': 'application/json', ...headers },
  body: JSON.stringify(body),
});
const admin = { 'x-hd-dev-admin': DEV_TOKEN };
async function paidOrder(customer = HEBREW, address = HEBREW_ADDRESS) {
  const { id: cart } = (await (await req('/api/cart', { method: 'POST' })).json()) as { id: string };
  expect((await req(`/api/cart/${cart}/items`, json({ variant_id: 'vase-a:default', qty: 1 }, 'PUT'))).status).toBe(200);
  const body = { cart_id: cart, customer, address, shipping_method: 'express', consents: { terms: true, marketing: false } };
  const r = (await (await req('/api/checkout', json(body))).json()) as { order_id: string; order_token: string };
  expect(r.order_id).toMatch(/^\d{10}$/);
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
  queued.length = 0;
  return { id: r.order_id, token: r.order_token };
}
const one = async <T>(sql: string, ...b: unknown[]) =>
  (await env.DB.prepare(sql)
    .bind(...b)
    .first<T>())!;
const n = async (sql: string, ...b: unknown[]) => (await one<{ n: number }>(sql, ...b)).n;
const status = async (id: string) => (await one<{ status: string }>('SELECT status FROM orders WHERE id = ?', id)).status;
const ship = async (id: string) =>
  one<{ status: string; reach: string; supplier_order_id: string | null; attempts: number }>(
    'SELECT status, reach, supplier_order_id, attempts FROM supplier_shipments WHERE order_id = ?',
    id,
  );
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
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

/** a supplier like a network one: the orders it holds (a timed-out call may still create one), how it answers */
function supplier(
  o: { hangMs?: number; failWith?: (i: SupplierOrderInput) => Error; failTimes?: number; find?: boolean; findFails?: boolean; dedupes?: boolean } = {},
) {
  const orders: string[] = [];
  const finds: string[] = [];
  let fails = o.failTimes ?? Infinity;
  const c: SupplierClient & { orders: string[]; finds: string[]; calls: number } = {
    id: 'mock',
    orders,
    finds,
    calls: 0,
    ...(o.dedupes ? { dedupesByOrderId: true } : {}),
    async submitOrder(input) {
      c.calls++;
      if (o.failWith && fails-- > 0) throw o.failWith(input);
      orders.push(input.order_id);
      if (o.hangMs) await sleep(o.hangMs);
      return { supplier_order_id: `SUP-${input.order_id}-${orders.length}`, raw: {} };
    },
  };
  if (o.find)
    c.findOrder = async (our) => {
      finds.push(our);
      if (o.findFails) throw Object.assign(new Error(`lookup failed for ${LATIN.full_name}`), { status: 502 });
      const i = orders.indexOf(our);
      return i < 0 ? null : { supplier_order_id: `SUP-${our}-${i + 1}` };
    };
  return c;
}
const job = (id: string): SupplierJob => ({ kind: 'submit-order', order_id: id });

// ---------------------------------------------------------------- ת46
describe('ת46: no customer value in a log row, in any script', () => {
  it('QA’s case: a known order’s values typed in Latin leave every row (an exception in its request, the queue’s row)', async () => {
    const o = await paidOrder(LATIN, LATIN_ADDRESS);
    const leak = `failed for ORNA bodeket at sderot habodkim 17, Mitzpe Bdika; tel 972527654321 / 00972-52-765-4321 / +972 52 765 4321; orna.bodeket@example.com; zip 8410000`;
    // the order's own page: its first query fails with the customer's values in the text (QA's request.unhandled)
    const broken = {
      ...env,
      DB: new Proxy(env.DB, {
        get(t, k) {
          if (k !== 'prepare') return Reflect.get(t, k);
          return (sql: string) => {
            if (/LEFT JOIN customers c/.test(sql)) return t.prepare(sql);
            throw new Error(leak);
          };
        },
      }),
    } as Env;
    const rows = await logged(async () => {
      const r = await req(`/api/orders/${o.id}`, { headers: { 'x-order-token': o.token } }, broken);
      expect(r.status).toBe(500);
      // a provider error whose own `code` carries the name, through the queue's row
      (await orderLog(env.DB, o.id)).error(
        'queue.job_failed',
        { kind: 'submit-order', order_id: o.id, reason: `refused ${LATIN.full_name}` },
        Object.assign(new Error(leak), { code: 'invalid_consignee:Orna' }),
      );
    });
    const text = rows.join('\n');
    expect(NEEDLES.filter((x) => text.includes(x))).toEqual([]);
    expect(text).toContain('request.unhandled');
    // the message keeps its meaning: who and where are gone, the rest stays ("ORNA bodeket" is the one value, any case)
    expect(text).toContain('failed for [customer] at [customer] 17, [customer]; tel [phone] / [phone] / [phone]; [email]; zip [phone]');
    expect(text).toContain(o.id); // the order number stays: it ties the row to the order
    expect(text).toContain('"error_code":"Error"');
  });

  it('the values of a known order: whole and by word, any case; a phone by its digits in every form', () => {
    const k = knownValues({ full_name: 'Orna Bodeket', email: 'orna.b@example.com', phone: '+972-52-765-4321', address: LATIN_ADDRESS });
    expect(stripKnown('ORNA BODEKET; orna; HaBodkim; habodkim; Mitzpe-Bdika', k)).toBe('[customer]; [customer]; [customer]; [customer]; [customer]-[customer]');
    for (const p of ['0527654321', '052-765-4321', '52 765 4321', '972527654321', '00972527654321', '+972 (52) 765-4321'])
      expect(stripKnown(`call ${p} now`, k), p).toBe('call [phone] now');
    // a house number alone is nobody's detail; the zip is stripped by its digits
    expect(stripKnown('attempt 17 of 5, zip 8410000, code http_502', k)).toBe('attempt 17 of 5, zip [phone], code http_502');
    const he = knownValues({ full_name: HEBREW.full_name, address: HEBREW_ADDRESS });
    expect(stripKnown('נכשל עבור נועה בן־דוד, רחוב הערבה, באר שבע', he)).not.toMatch(/נועה|הערבה|באר שבע/);
  });

  it('an unknown order in production: the error’s name and code only; elsewhere the scrubbed message', async () => {
    const err = Object.assign(new Error(`invalid consignee Orna Bodeket, 972527654321`), { status: 400 });
    configureLog({ ENVIRONMENT: 'production' });
    const prod = logRow('error', 'request.unhandled', { path: '/api/cart/x' }, err);
    expect(prod).toMatchObject({ error_name: 'Error', error_code: 'http_400' });
    expect(prod).not.toHaveProperty('error_message');
    expect(JSON.stringify(prod)).not.toMatch(/Orna|Bodeket|972527654321/);
    configureLog({ ENVIRONMENT: 'preview' });
    expect(logRow('error', 'x', {}, err).error_message).toBe('invalid consignee Orna Bodeket, [phone]');
    // and through a request: production, a path with no order, an exception with Latin details
    const prodEnv = { ...env, ENVIRONMENT: 'production' } as Env;
    const broken = {
      ...prodEnv,
      DB: {
        prepare: () => {
          throw new Error('for Orna Bodeket');
        },
      } as unknown as D1Database,
    };
    const rows = await logged(async () => void (await req('/api/cart', { method: 'POST' }, broken)));
    const row = rows.find((r) => r.includes('request.unhandled'))!;
    expect(row).toContain('"error_name":"Error"');
    expect(row).not.toMatch(/Orna|error_message/);
  });

  it('PHONE_RE: 972 and 00972 without a plus, as well as +972 and 0', () => {
    expect(scrub('a 972521234567 b 00972521234567 c 972-52-123-4567 d +972 52 123 4567 e 052-1234567 f 03-1234567')).toBe(
      'a [phone] b [phone] c [phone] d [phone] e [phone] f [phone]',
    );
    // an order number (ten digits from 1–9) is not a phone
    expect(scrub('order 5123456789')).toBe('order 5123456789');
  });

  it('errorCode: `code` only from our own classes or a system code, never a provider’s free text', () => {
    expect(errorCode(Object.assign(new Error('x'), { code: 'invalid_consignee:Orna' }))).toBe('Error');
    expect(errorCode(Object.assign(new Error('x'), { code: 'orna_bodeket' }))).toBe('Error');
    expect(errorCode(Object.assign(new Error('x'), { code: 'ECONNRESET' }))).toBe('ECONNRESET');
    expect(errorCode(new SupplierRefused('cj_order_api_docs_needed'))).toBe('cj_order_api_docs_needed');
    expect(errorCode(new HttpError(409, 'not_cancelable'))).toBe('not_cancelable');
    expect(errorCode(new Error('invalid_consignee: Orna'))).toBe('invalid_consignee');
    expect(errorCode(new Error('orna: refused'))).toBe('Error');
    expect(errorCode(Object.assign(new Error('x'), { name: 'Orna Bodeket' }))).toBe('Error');
  });
});

// ---------------------------------------------------------------- ת47
describe('ת47: a send that died mid-call is seen by /healthz', () => {
  const health = async () => {
    const r = await req('/healthz');
    return { code: r.status, body: (await r.json()) as { checks: Record<string, string> } };
  };
  it('QA’s case: a retry dies mid-call after an earlier failure (submitting, last_error set): degraded past the lease', async () => {
    vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const o = await paidOrder();
    await processSupplierJob(env, job(o.id), 1, { client: supplier({ failWith: () => new SupplierRefused('busy') }) });
    const ago = (ms: number) => new Date(Date.now() - ms).toISOString();
    // the second run claimed it and died: the claim stays, with the first failure's last_error
    await env.DB.prepare("UPDATE supplier_shipments SET status = 'submitting', failing_since = ?, updated_at = ? WHERE order_id = ?")
      .bind(ago(90 * 60_000), ago(80 * 60_000), o.id)
      .run();
    expect((await health()).body.checks.supplier).toBe('degraded');
    expect((await health()).code).toBe(503);
    // a claim within its lease is a call that may still answer: not failing
    await env.DB.prepare('UPDATE supplier_shipments SET updated_at = ? WHERE order_id = ?')
      .bind(ago(SUBMIT_LEASE_MS / 2), o.id)
      .run();
    expect((await health()).body.checks.supplier).toBe('ok');
    // a first claim that died (no failure before it): past the lease and 30 minutes, degraded too
    await env.DB.prepare('UPDATE supplier_shipments SET failing_since = NULL, last_error = NULL, updated_at = ? WHERE order_id = ?')
      .bind(ago(SUPPLIER_FAILING_MS + 60_000), o.id)
      .run();
    expect((await health()).body.checks.supplier).toBe('degraded');
  });
});

// ---------------------------------------------------------------- ת48
describe('ת48: a send that may have reached the supplier is never repeated blindly', () => {
  const quiet = () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    vi.spyOn(console, 'warn').mockImplementation(() => undefined);
  };

  it('QA B4d: a timeout (the supplier created it), then a retry: asked first, found → recorded, one order at the supplier', async () => {
    quiet();
    const o = await paidOrder();
    const sup = supplier({ hangMs: 60, find: true });
    expect(await processSupplierJob(env, job(o.id), 1, { client: sup, callTimeoutMs: 15 })).toBe('retry');
    await sleep(70);
    expect(await ship(o.id)).toMatchObject({ status: 'failed', reach: 'maybe' });
    expect(await processSupplierJob(env, job(o.id), 2, { client: sup })).toBe('submitted');
    expect(sup.orders).toEqual([o.id]);
    expect(sup.calls).toBe(1);
    expect(await ship(o.id)).toMatchObject({ status: 'submitted', reach: 'none', supplier_order_id: `SUP-${o.id}-1` });
    expect(await status(o.id)).toBe('sent_to_supplier');
    expect(await n("SELECT COUNT(*) AS n FROM audit_log WHERE action = 'supplier.found_by_order' AND subject = ?", o.id)).toBe(1);
  });

  it('asked, it holds none: sent once more, and recorded', async () => {
    quiet();
    const o = await paidOrder();
    const sup = supplier({ failWith: () => Object.assign(new Error('socket hang up'), { status: 503 }), failTimes: 1, find: true });
    expect(await processSupplierJob(env, job(o.id), 1, { client: sup })).toBe('retry');
    expect(await ship(o.id)).toMatchObject({ reach: 'maybe' });
    expect(await processSupplierJob(env, job(o.id), 2, { client: sup })).toBe('submitted');
    expect(sup.finds).toEqual([o.id]);
    expect(sup.orders).toEqual([o.id]);
    expect(await ship(o.id)).toMatchObject({ status: 'submitted', reach: 'none' });
    expect(await n("SELECT COUNT(*) AS n FROM audit_log WHERE action = 'supplier.none_by_order' AND subject = ?", o.id)).toBe(1);
  });

  it('asked, no answer: nothing sent, still maybe, retried; a row by code', async () => {
    const o = await paidOrder();
    const sup = supplier({ failWith: () => new Error('timeout-ish'), failTimes: 1, find: true, findFails: true });
    const rows = await logged(async () => {
      await processSupplierJob(env, job(o.id), 1, { client: sup });
      expect(await processSupplierJob(env, job(o.id), 2, { client: sup })).toBe('retry');
    });
    expect(sup.calls).toBe(1);
    expect(await ship(o.id)).toMatchObject({ status: 'failed', reach: 'maybe' });
    expect(rows.some((r) => r.includes('supplier.find_failed') && r.includes('"code":"http_502"'))).toBe(true);
    expect(rows.join('\n')).not.toMatch(/Orna|נועה/);
  });

  it('cannot be asked, documented to deduplicate by our order number: sent again', async () => {
    quiet();
    const o = await paidOrder();
    const sup = supplier({ failWith: () => new Error('ECONNRESET'), failTimes: 1, dedupes: true });
    await processSupplierJob(env, job(o.id), 1, { client: sup });
    expect(await processSupplierJob(env, job(o.id), 2, { client: sup })).toBe('submitted');
    expect(sup.calls).toBe(2);
  });

  it('cannot be asked and does not deduplicate: nothing sent, a person checks; "none" sends it again, "found" records it', async () => {
    quiet();
    for (const outcome of ['none', 'found'] as const) {
      const o = await paidOrder();
      const sup = supplier({ hangMs: 60 });
      await processSupplierJob(env, job(o.id), 1, { client: sup, callTimeoutMs: 15 });
      await sleep(70);
      expect(await processSupplierJob(env, job(o.id), 2, { client: sup })).toBe('skipped');
      expect(sup.calls).toBe(1);
      expect(await ship(o.id)).toMatchObject({ status: 'failed', reach: 'maybe' });
      expect(await status(o.id)).toBe('supplier_error');
      expect(await n("SELECT COUNT(*) AS n FROM audit_log WHERE action = 'supplier.resend_needs_person' AND subject = ?", o.id)).toBe(1);
      // the admin lists it as needing attention
      const list = (await (await req('/api/admin/orders?filter=attention', { headers: admin })).json()) as { orders: { id: string }[] };
      expect(list.orders.map((x) => x.id)).toContain(o.id);
      const body = outcome === 'found' ? { outcome, supplier_order_id: 'SUP-BY-HAND', note: 'נמצאה אצל הספק' } : { outcome, note: 'אין אצל הספק' };
      expect((await req(`/api/admin/orders/${o.id}/supplier-check`, json(body, 'POST', admin))).status).toBe(200);
      if (outcome === 'none') {
        expect(queued).toEqual([job(o.id)]);
        expect(await status(o.id)).toBe('paid');
        expect(await ship(o.id)).toMatchObject({ reach: 'checked' });
        expect(await processSupplierJob(env, job(o.id), 1, { client: sup })).toBe('submitted');
        expect(sup.calls).toBe(2);
      } else {
        expect(queued).toEqual([]);
        expect(await status(o.id)).toBe('sent_to_supplier');
        expect(await ship(o.id)).toMatchObject({ status: 'submitted', supplier_order_id: 'SUP-BY-HAND' });
      }
      queued.length = 0;
    }
  });

  it('a cancellation waiting on the same check: "none" cancels and refunds, and sends nothing', async () => {
    quiet();
    const o = await paidOrder();
    const sup = supplier({ hangMs: 60 });
    await processSupplierJob(env, job(o.id), 1, { client: sup, callTimeoutMs: 15 });
    await sleep(70);
    await processSupplierJob(env, job(o.id), 2, { client: sup });
    expect(await cancelOrder(env, o.id, 'admin', 'בקשת הלקוח', { supplier: sup })).toMatchObject({ code: 'supplier_check_needed' });
    expect((await req(`/api/admin/orders/${o.id}/supplier-check`, json({ outcome: 'none', note: 'אין' }, 'POST', admin))).status).toBe(200);
    expect(queued).toEqual([]);
    expect(await cancelOrder(env, o.id, 'admin', 'בקשת הלקוח', { supplier: sup })).toMatchObject({ outcome: 'canceled', stage: 'before_supplier' });
    expect(sup.calls).toBe(1);
  });

  it('a claim whose run died mid-call is taken over as maybe: asked first, never sent twice', async () => {
    quiet();
    const o = await paidOrder();
    const sup = supplier({ find: true });
    // the first run claimed and called (the supplier created the order), then died before recording
    sup.orders.push(o.id);
    await env.DB.prepare("UPDATE supplier_shipments SET supplier = 'mock', status = 'submitting', updated_at = ? WHERE order_id = ?")
      .bind(new Date(Date.now() - SUBMIT_LEASE_MS - 60_000).toISOString(), o.id)
      .run();
    expect(await processSupplierJob(env, job(o.id), 2, { client: sup })).toBe('submitted');
    expect(sup.calls).toBe(0);
    expect(sup.orders).toEqual([o.id]);
    expect(await ship(o.id)).toMatchObject({ status: 'submitted', supplier_order_id: `SUP-${o.id}-1` });
  });
});

// ---------------------------------------------------------------- AN1
describe('AN1: no analytics beacon in the admin, and the order page cannot load one', () => {
  it('the admin screen: no beacon, and its policy does not allow Cloudflare’s analytics hosts', async () => {
    const o = await paidOrder();
    for (const path of ['/admin/', `/admin/orders/${o.id}`]) {
      const r = await req(path, { headers: admin });
      expect(r.status, path).toBe(200);
      expect(await r.text()).not.toMatch(/cloudflareinsights|data-cf-beacon/);
      expect(r.headers.get('content-security-policy') ?? '').not.toMatch(/cloudflareinsights/);
    }
  });
  it('the order page’s policy leaves out the analytics hosts; the site’s allows them', async () => {
    const assets = { fetch: async () => new Response('<!doctype html><title>order</title>', { headers: { 'content-type': 'text/html' } }) };
    const r = await req('/order/1234567890/', undefined, { ...env, ASSETS: assets } as unknown as Env);
    const csp = r.headers.get('content-security-policy') ?? '';
    expect(csp).toMatch(/script-src 'self';/);
    expect(csp).not.toMatch(/cloudflareinsights/);
    const { SITE_CSP } = await import('../src/lib/http');
    expect(SITE_CSP).toContain("script-src 'self' https://static.cloudflareinsights.com;");
    expect(SITE_CSP).toContain("connect-src 'self' https://cloudflareinsights.com;");
  });
});
