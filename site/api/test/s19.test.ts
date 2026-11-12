/**
 * S19, the fixes of QA S17 (briefs/site-s19-qa-fixes-2026-11-12.md):
 * - ת52: a known order's values leave a log row as whole words only; an e-mail as the whole address and its local part,
 *   never its domain's parts; `error_id`, `order_id`, the event and the path are never touched.
 * - ת53: `errorCode` and the row's error name take a code, a message prefix or a class name from our own classes only
 *   (lib/errors.ts), so a provider's error reaches no row as text.
 * - ת54: a dead claim that is taken over keeps its own time as the start of the failing run, so /healthz stays degraded
 *   while the order waits for a person.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { signWebhook } from '@hd/shared';
import { app } from '../src/app';
import type { Env, SupplierJob } from '../src/env';
import { buildSeedSql } from '../scripts/seed';
import { createD1, migrate } from './d1-shim';
import { catalog } from './fixture';
import { SUBMIT_LEASE_MS, processSupplierJob, supplierLines } from '../src/lib/fulfillment';
import { configureLog, errorCode, errorName, knownValues, log, logRow, pathForLog, stripKnown } from '../src/lib/log';
import { CodedError, OwnError } from '../src/lib/errors';
import { HttpError } from '../src/lib/http';
import { CallTimedOut } from '../src/lib/deadline';
import { InvoiceRefused } from '../src/lib/invoices';
import { RefundRefused } from '../src/lib/payments/types';
import { SUPPLIER_FAILING_MS } from '../src/routes/health';
import { SupplierRefused, type SupplierClient, type SupplierOrderInput } from '../src/lib/suppliers/types';

const SECRET = 'test-webhook-secret-s19-not-a-key';
/** QA's over-redaction (ת52): a customer whose values hold "com", "tel" and "invalid" as words */
const DANA = { full_name: 'Dana Levi', email: 'dana.levi@example.invalid', phone: '054-7716204' };
const DANA_ADDRESS = { city: 'Tel Aviv', street: 'Herzl', house: '12', apartment: '4', zip: '6100000', notes: '' };
const HEBREW = { full_name: 'נועה בן־דוד', email: 'buyer.s19@example.com', phone: '052-1234567' };
const HEBREW_ADDRESS = { city: 'באר שבע', street: 'רחוב הערבה', house: '17', apartment: '3', zip: '8410000', notes: '' };

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
    ADMIN_DEV_TOKEN: 'dev-admin-token-for-tests-only-s19-0123456789',
  };
  configureLog(env);
});
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  configureLog({ ENVIRONMENT: 'production' });
});

const req = (path: string, init?: RequestInit, e: Env = env) => app.request(`http://localhost${path}`, init, e);
const json = (body: unknown): RequestInit => ({ method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
async function paidOrder(customer = HEBREW, address = HEBREW_ADDRESS) {
  const { id: cart } = (await (await req('/api/cart', { method: 'POST' })).json()) as { id: string };
  expect((await req(`/api/cart/${cart}/items`, { ...json({ variant_id: 'vase-a:default', qty: 1 }), method: 'PUT' })).status).toBe(200);
  const body = { cart_id: cart, customer, address, shipping_method: 'express', consents: { terms: true, marketing: false } };
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
  queued.length = 0;
  orderTokens.set(r.order_id, r.order_token);
  return r.order_id;
}
const orderTokens = new Map<string, string>();
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
const job = (id: string): SupplierJob => ({ kind: 'submit-order', order_id: id });
const quiet = () => {
  vi.spyOn(console, 'error').mockImplementation(() => undefined);
  vi.spyOn(console, 'warn').mockImplementation(() => undefined);
};

// ---------------------------------------------------------------- ת52
describe('ת52: a known order’s values leave a row as whole words, and our own fields are never touched', () => {
  const k = knownValues({ ...DANA, address: DANA_ADDRESS });

  it('QA’s words: "commit", "hotel", "/complete", "invalid" stay whole; the customer’s values still go', () => {
    expect(stripKnown('commit failed at the hotel: invalid state, /api/complete, telemetry, levitate, danaher', k)).toBe(
      'commit failed at the hotel: invalid state, /api/complete, telemetry, levitate, danaher',
    );
    expect(stripKnown('for Dana Levi (DANA, levi) in Tel Aviv, Herzl 12; phone 0547716204', k)).toBe(
      'for [customer] ([customer], [customer]) in [customer], [customer] 12; phone [phone]',
    );
  });

  it('the e-mail: the whole address and its local part, never its domain’s parts', () => {
    expect(stripKnown('dana.levi@example.invalid / dana.levi / example / invalid / example.invalid', k)).toBe(
      '[customer] / [customer] / example / invalid / example.invalid',
    );
    const gmail = knownValues({ full_name: 'Orna Bodeket', email: 'ob@gmail.com' });
    // a local part under three letters is not a word of its own; the whole address still goes
    expect(stripKnown('ob@gmail.com, gmail, com, ob', gmail)).toBe('[customer], gmail, com, ob');
  });

  it('Hebrew: a value with the prefix Hebrew writes on it ("לנועה", "ובבאר שבע") goes too', () => {
    const he = knownValues({ full_name: HEBREW.full_name, address: HEBREW_ADDRESS });
    expect(stripKnown('נשלח לנועה ובבאר שבע, ברחוב הערבה', he)).toBe('נשלח [customer] [customer], [customer]');
  });

  it('QA’s planted error_id E-DANA2345, an order number shaped like a phone, the event and the path stay as written', () => {
    configureLog({ ENVIRONMENT: 'production' });
    const err = new Error('refused Dana Levi at Herzl');
    const row = logRow(
      'error',
      'request.unhandled',
      { error_id: 'E-DANA2345', order_id: '9722123456', path: '/api/orders/9722123456/complete', event: 'dana', reason: 'for Dana' },
      err,
      k,
    );
    expect(row).toMatchObject({ event: 'request.unhandled', error_id: 'E-DANA2345', order_id: '9722123456', path: '/api/orders/9722123456/complete' });
    expect(row.reason).toBe('for [customer]');
    expect(row.error_message).toBe('refused [customer] at [customer]');
    // through the logger: the id it returns is the id in the row
    const rows: unknown[][] = [];
    vi.spyOn(console, 'error').mockImplementation((...a: unknown[]) => void rows.push(a));
    const id = log.forOrder(k).error('admin.action_failed', { error_id: 'E-DANA2345', order_id: '9722123456' }, err);
    expect(id).toBe('E-DANA2345');
    expect(rows[0]![0]).toMatchObject({ error_id: 'E-DANA2345', order_id: '9722123456' });
  });

  it('a path keeps its order numbers; any other piece of it is scrubbed of an e-mail or a phone; a field that is not an id is redacted as before', () => {
    expect(pathForLog('/api/orders/9722123456/complete')).toBe('/api/orders/9722123456/complete');
    expect(pathForLog('/api/x/dana@example.com/0547716204/972547716204')).toBe('/api/x/[email]/[phone]/[phone]');
    // an order_id or an error_id not of our shape is redacted like any field
    expect(logRow('info', 'x', { order_id: 'call 054-7716204', error_id: 'dana@example.com' })).toMatchObject({
      order_id: 'call [phone]',
      error_id: '[email]',
    });
  });

  it('QA’s ת46 case still holds through a request: the known order’s Latin values leave the row, and its number stays', async () => {
    const id = await paidOrder(DANA, DANA_ADDRESS);
    const leak = `commit failed for DANA levi at herzl 12, tel aviv; 972547716204; dana.levi@example.invalid`;
    const broken = {
      ...env,
      DB: new Proxy(env.DB, {
        get(t, key) {
          if (key !== 'prepare') return Reflect.get(t, key);
          return (sql: string) => {
            if (/LEFT JOIN customers c/.test(sql)) return t.prepare(sql);
            throw new Error(leak);
          };
        },
      }),
    } as Env;
    const rows = await logged(async () =>
      expect((await req(`/api/orders/${id}`, { headers: { 'x-order-token': orderTokens.get(id)! } }, broken)).status).toBe(500),
    );
    const text = rows.join('\n');
    expect(text).toContain('commit failed for [customer] at [customer] 12, [customer]; [phone]; [email]');
    expect(text).toContain(`"path":"/api/orders/${id}"`);
    expect(text).not.toMatch(/dana|levi|herzl|aviv|7716204/i);
  });
});

// ---------------------------------------------------------------- ת53
describe('ת53: a code, a message prefix and a class name only from our own classes', () => {
  it('a provider’s error: its snake_case prefix and the name it chose reach no row', () => {
    expect(errorCode(new Error('consignee_orna_rejected: Orna Bodeket'))).toBe('Error');
    const named = Object.assign(new Error('x'), { name: 'Orna' });
    expect(errorCode(named)).toBe('Error');
    expect(errorName(named)).toBe('Error');
    class Orna extends Error {
      constructor() {
        super('bad_consignee_orna: no');
        this.name = 'Orna';
      }
    }
    expect(errorCode(new Orna())).toBe('Error');
    configureLog({ ENVIRONMENT: 'production' });
    expect(logRow('error', 'x', {}, new Orna())).toMatchObject({ error_name: 'Error', error_code: 'Error' });
    // what a provider’s error may still say: its HTTP status, a system code, a timeout, the runtime’s class
    expect(errorCode(Object.assign(new Orna(), { status: 422 }))).toBe('http_422');
    expect(errorCode(Object.assign(new Error('x'), { code: 'ECONNRESET' }))).toBe('ECONNRESET');
    expect(errorCode(new TypeError('fetch failed'))).toBe('TypeError');
    expect(errorCode(Object.assign(new Error('x'), { name: 'AbortError' }))).toBe('aborted');
  });

  it('our own classes keep their codes, prefixes and names', () => {
    expect(new HttpError(409, 'not_cancelable')).toBeInstanceOf(OwnError);
    expect(errorCode(new HttpError(409, 'not_cancelable'))).toBe('not_cancelable');
    expect(errorCode(new SupplierRefused('cj_order_api_docs_needed'))).toBe('cj_order_api_docs_needed');
    expect(errorName(new SupplierRefused('x'))).toBe('SupplierRefused');
    expect(errorCode(new InvoiceRefused('invoice_total_mismatch'))).toBe('invoice_total_mismatch');
    expect(errorCode(new RefundRefused('refund_exceeds_payment'))).toBe('refund_exceeds_payment');
    expect(errorCode(new CallTimedOut('mock submitOrder', 15))).toBe('timeout');
    expect(errorCode(new CodedError('set_composition_missing', 'prints-a:set'))).toBe('set_composition_missing');
    // our own refusal of a set without its composition, as the supplier job meets it
    const base = { product_id: 'prints-a', variant_id: 'prints-a:set', qty: 1, unit_sell_qty: 3, pack: 'set' as const, supplier_sku: 'T1' };
    let thrown: unknown;
    try {
      supplierLines([{ ...base, supplier_lines_json: null, set_skus_json: null, set_incomplete: 'which 3' }]);
    } catch (e) {
      thrown = e;
    }
    expect(errorCode(thrown)).toBe('set_composition_missing');
  });

  it('through the rows QA named: a failed send whose provider error names the buyer logs by status or "Error" only', async () => {
    const id = await paidOrder(DANA, DANA_ADDRESS);
    class Dana extends Error {
      constructor() {
        super('consignee_dana_levi_rejected: Dana Levi, Herzl 12');
        this.name = 'DanaLevi';
      }
    }
    const client: SupplierClient = {
      id: 'mock',
      async submitOrder(_i: SupplierOrderInput) {
        throw new Dana();
      },
    };
    const rows = await logged(() => processSupplierJob(env, job(id), 1, { client }));
    const row = rows.find((r) => r.includes('supplier.submit_failed'))!;
    expect(row).toContain('"code":"Error"');
    expect(rows.join('\n')).not.toMatch(/dana|levi|herzl/i);
  });
});

// ---------------------------------------------------------------- ת54
describe('ת54: a dead claim taken over and left to a person keeps /healthz degraded', () => {
  const health = async () => ((await (await req('/healthz')).json()) as { checks: { supplier: string } }).checks.supplier;
  const ago = (ms: number) => new Date(Date.now() - ms).toISOString();
  /** the first run claimed the shipment at `at` and died: no failure before it */
  const dead = (id: string, at: string) =>
    env.DB.prepare(
      "UPDATE supplier_shipments SET supplier = 'mock', status = 'submitting', failing_since = NULL, last_error = NULL, updated_at = ? WHERE order_id = ?",
    )
      .bind(at, id)
      .run();
  /** a supplier that cannot be asked and does not deduplicate: the takeover leaves the order to a person */
  const blind: SupplierClient = {
    id: 'mock',
    async submitOrder() {
      throw new Error('never called');
    },
  };
  const failingSince = async (id: string) =>
    (await env.DB.prepare('SELECT failing_since FROM supplier_shipments WHERE order_id = ?').bind(id).first<{ failing_since: string | null }>())!.failing_since;

  it('QA’s case: the first claim died at T1; degraded at T1+30.5 min; the takeover at T1+31 leaves it to a person, and it stays degraded', async () => {
    quiet();
    const id = await paidOrder();
    const T1 = ago(31 * 60_000);
    await dead(id, T1);
    expect(await health()).toBe('degraded');
    expect(await processSupplierJob(env, job(id), 2, { client: blind })).toBe('skipped');
    const s = await env.DB.prepare('SELECT status, reach FROM supplier_shipments WHERE order_id = ?').bind(id).first<{ status: string; reach: string }>();
    expect(s).toMatchObject({ status: 'failed', reach: 'maybe' });
    expect((await env.DB.prepare('SELECT status FROM orders WHERE id = ?').bind(id).first<{ status: string }>())!.status).toBe('supplier_error');
    // the run of failures started with the dead claim, not with the takeover
    expect(await failingSince(id)).toBe(T1);
    expect(await health()).toBe('degraded');
  });

  it('a claim that died 12 minutes ago: ok now (the 30 minutes are not over), degraded 30 minutes after the claim, not after the takeover', async () => {
    quiet();
    const id = await paidOrder();
    const T1 = ago(SUBMIT_LEASE_MS + 2 * 60_000);
    await dead(id, T1);
    expect(await processSupplierJob(env, job(id), 2, { client: blind })).toBe('skipped');
    expect(await failingSince(id)).toBe(T1);
    expect(await health()).toBe('ok');
    // 19 minutes on: 31 minutes after the dead claim (before S19 the run started at the takeover: 19 minutes, ok)
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(Date.parse(T1) + SUPPLIER_FAILING_MS + 60_000);
    expect(await health()).toBe('degraded');
  });

  it('a takeover that finds the order at the supplier, or sends it, ends the run: ok', async () => {
    quiet();
    const id = await paidOrder();
    await dead(id, ago(31 * 60_000));
    const asked: SupplierClient = {
      id: 'mock',
      async submitOrder() {
        throw new Error('never called');
      },
      async findOrder(our) {
        return { supplier_order_id: `SUP-${our}` };
      },
    };
    expect(await processSupplierJob(env, job(id), 2, { client: asked })).toBe('submitted');
    expect(await failingSince(id)).toBeNull();
    expect(await health()).toBe('ok');
  });

  it('a takeover whose lookup fails keeps the dead claim’s time: degraded past 30 minutes, retried', async () => {
    quiet();
    const id = await paidOrder();
    const T1 = ago(31 * 60_000);
    await dead(id, T1);
    const down: SupplierClient = {
      id: 'mock',
      async submitOrder() {
        throw new Error('never called');
      },
      async findOrder() {
        throw Object.assign(new Error('lookup down'), { status: 503 });
      },
    };
    expect(await processSupplierJob(env, job(id), 2, { client: down })).toBe('retry');
    expect(await failingSince(id)).toBe(T1);
    expect(await health()).toBe('degraded');
  });
});
