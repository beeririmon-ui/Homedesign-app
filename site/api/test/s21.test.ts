/**
 * S21, the fixes of QA S19 (briefs/site-s21-qa-fixes-2026-11-12.md), the Worker's side:
 * - ת64: a known order's values end at anything but a letter: "_" and digits are not letters, so a name glued to them
 *   in a provider's text leaves the row too ("consignee_dana_rejected", "DANA_GAT", "dana1985", "gat123"); camel case is
 *   two words ("DanaGat"); ordinary words keep their letters (QA's K1) and our own ids stay (K5).
 * - ת65: a system code only from a closed list: a provider's code shaped like one ("E_ORNA") never becomes error_code.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { signWebhook } from '@hd/shared';
import type { Env, SupplierJob } from '../src/env';
import { app } from '../src/app';
import { buildSeedSql } from '../scripts/seed';
import { createD1, migrate } from './d1-shim';
import { catalog } from './fixture';
import { processSupplierJob } from '../src/lib/fulfillment';
import { SYSTEM_CODES, configureLog, errorCode, knownValues, logRow, stripKnown } from '../src/lib/log';
import { CodedError } from '../src/lib/errors';
import type { SupplierClient, SupplierOrderInput } from '../src/lib/suppliers/types';

const SECRET = 'test-webhook-secret-s21-not-a-key';
const DANA = { full_name: 'Dana Gat', email: 'dana.gat@example.invalid', phone: '054-7716204' };
const DANA_ADDRESS = { city: 'Tel Aviv', street: 'Herzl', house: '12', apartment: '4', zip: '6100000', notes: '' };
const HEBREW = { full_name: 'נועה בן־דוד', email: 'buyer.s21@example.com', phone: '052-1234567' };
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
    ADMIN_DEV_TOKEN: 'dev-admin-token-for-tests-only-s21-0123456789',
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

// ---------------------------------------------------------------- ת64
describe('ת64: a known order’s values end at anything but a letter', () => {
  const k = knownValues({ ...DANA, address: DANA_ADDRESS });

  it('QA’s K3: a name glued to "_" or to digits leaves the row; camel case too', () => {
    const cases: [string, string][] = [
      ['consignee_dana_rejected: address dana', 'consignee_[customer]_rejected: address [customer]'],
      ['DANA_GAT', '[customer]_[customer]'],
      ['user_dana', 'user_[customer]'],
      ['dana2', '[customer]2'],
      ['dana1985', '[customer]1985'],
      ['gat123', '[customer]123'],
      // S23 (ת76): the name without its space is a value of its own, so "DanaGat" goes whole
      ['DanaGat', '[customer]'],
      ['herzl_12_tel_aviv', '[customer]_12_[customer]_[customer]'],
      // S21 left "danagat" (letters on both sides); S23 (QA ת76) takes the value without its space too
      ['danagat', '[customer]'],
    ];
    for (const [text, want] of cases) expect(stripKnown(text, k), text).toBe(want);
  });

  it('QA’s K1: ordinary words keep their letters; a value inside a longer word stays (letters on its side)', () => {
    const words = 'commit hotel complete invalid gateway navigate telemetry levitate danaher Gatsby iPhone MacBook regatta agate';
    expect(stripKnown(words, k)).toBe(words);
  });

  it('a value written in camel case still goes whole ("McDonald"), and "iPhone" stays', () => {
    const mc = knownValues({ full_name: 'Ron McDonald' });
    expect(stripKnown('for McDonald and mcdonald_ron; iPhone', mc)).toBe('for [customer] and [customer]_[customer]; iPhone');
  });

  it('Hebrew: the prefix Hebrew writes on a value, and a value glued to a digit or "_"', () => {
    const he = knownValues({ full_name: HEBREW.full_name, address: HEBREW_ADDRESS });
    expect(stripKnown('נשלח לנועה ובבאר שבע, נועה_2, ברחוב הערבה', he)).toBe('נשלח [customer] [customer], [customer]_2, [customer]');
  });

  it('QA’s K5: error_id, order_id, the event and the path are kept by their shape', () => {
    configureLog({ ENVIRONMENT: 'production' });
    const row = logRow(
      'error',
      'supplier.submit_failed',
      { error_id: 'E-DANA2345', order_id: '9722123456', path: '/api/orders/9722123456/complete', reason: 'consignee_dana_rejected' },
      new Error('refused DanaGat at herzl_12'),
      k,
    );
    expect(row).toMatchObject({ event: 'supplier.submit_failed', error_id: 'E-DANA2345', order_id: '9722123456', path: '/api/orders/9722123456/complete' });
    expect(row.reason).toBe('consignee_[customer]_rejected');
    // S23 (ת76): "DanaGat" is the name without its space, one value
    expect(row.error_message).toBe('refused [customer] at [customer]_12');
  });

  it('through the supplier job: a provider’s text with the name glued to "_" and digits reaches no row', async () => {
    const id = await paidOrder(DANA, DANA_ADDRESS);
    const client: SupplierClient = {
      id: 'mock',
      async submitOrder(_i: SupplierOrderInput) {
        throw new CodedError('supplier_refused', 'consignee_dana_rejected: DANA_GAT dana1985 gat123 DanaGat');
      },
    };
    const rows = await logged(() => processSupplierJob(env, job(id), 1, { client }));
    expect(rows.join('\n')).not.toMatch(/dana|gat123|gat\b|DanaGat/i);
  });
});

// ---------------------------------------------------------------- ת65
describe('ת65: a system code only from a closed list', () => {
  it('QA’s list passes; a provider’s code shaped like one does not (it falls back to the status, else "Error")', () => {
    expect([...SYSTEM_CODES].sort()).toEqual([
      'EAI_AGAIN',
      'ECONNABORTED',
      'ECONNREFUSED',
      'ECONNRESET',
      'EHOSTUNREACH',
      'ENETUNREACH',
      'ENOTFOUND',
      'EPIPE',
      'ETIMEDOUT',
    ]);
    for (const c of SYSTEM_CODES) expect(errorCode(Object.assign(new Error('x'), { code: c }))).toBe(c);
    for (const c of ['E_ORNA', 'E_CONSIGNEE_ORNA', 'EORNA', 'ERR_ORNA', 'E_DANA_GAT', 'EADDRINUSE_X'])
      expect(errorCode(Object.assign(new Error('x'), { code: c })), c).toBe('Error');
    expect(errorCode(Object.assign(new Error('x'), { code: 'E_ORNA', status: 422 }))).toBe('http_422');
    // our own classes keep their own codes, as before
    expect(errorCode(new CodedError('set_composition_missing', 'x'))).toBe('set_composition_missing');
  });

  it('through the supplier job (QA’s C2): a provider error with code E_ORNA logs "Error", and the name is in no row', async () => {
    const id = await paidOrder(DANA, DANA_ADDRESS);
    const client: SupplierClient = {
      id: 'mock',
      async submitOrder(_i: SupplierOrderInput) {
        throw Object.assign(new Error('refused'), { code: 'E_ORNA' });
      },
    };
    const rows = await logged(() => processSupplierJob(env, job(id), 1, { client }));
    const row = rows.find((r) => r.includes('supplier.submit_failed'))!;
    expect(row).toContain('"code":"Error"');
    expect(rows.join('\n')).not.toContain('ORNA');
  });
});
