/**
 * S12, fixes from QA S8–S10 (qa/reports/2026-11-10-site-track-qa-s8-s10.md) and the S11 addendum, on the Worker:
 * ת16 one invoice per order (concurrent runs, a crash between the call and the record), ת17 production fails closed on
 * every provider variable, ת18 only a paid order is invoiced, ת19 a message fails alone, ת20 only the configured
 * provider's webhook is heard, the triptych goes to the supplier as its three SKUs, and ת21 the line keeps its house.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { signWebhook } from '@hd/shared';
import { app } from '../src/app';
import worker from '../src/index';
import type { Env, SupplierJob } from '../src/env';
import { buildSeedSql } from '../scripts/seed';
import { createD1, migrate } from './d1-shim';
import { catalog } from './fixture';
import { processSupplierJob, supplierLines } from '../src/lib/fulfillment';
import { INVOICE_LEASE_MS, InvoiceRefused, processInvoiceJob, type InvoiceProvider, type IssuedInvoice } from '../src/lib/invoices';
import { PROVIDERS, configIssues, isProduction, providerOf, type ProviderVar } from '../src/lib/config';
import { supplierClient } from '../src/lib/suppliers';
import { parseJsonc } from '../scripts/jsonc';

const SECRET = 'test-webhook-secret-s12-not-a-key';
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
    ACCESS_TEAM_DOMAIN: '',
    ACCESS_AUD: '',
    PAYMENT_WEBHOOK_SECRET: SECRET,
  };
});

const req = (path: string, init?: RequestInit) => app.request(`http://localhost${path}`, init, env);
const json = (body: unknown, method = 'POST'): RequestInit => ({ method, headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
const checkoutBody = (cart_id: string) => ({
  cart_id,
  customer: { full_name: 'ישראלה ישראלי', email: 'buyer@example.com', phone: '050-1234567' },
  address: { city: 'תל אביב', street: 'הרצל', house: '10' },
  shipping_method: 'express',
  consents: { terms: true, marketing: false },
});
async function cartWith(items: { variant_id: string; qty: number; house?: string }[]) {
  const { id } = (await (await req('/api/cart', { method: 'POST' })).json()) as { id: string };
  for (const i of items) expect((await req(`/api/cart/${id}/items`, json(i, 'PUT'))).status, i.variant_id).toBe(200);
  return id;
}
async function pendingOrder(items = [{ variant_id: 'vase-a:default', qty: 1 }]) {
  const r = (await (await req('/api/checkout', json(checkoutBody(await cartWith(items))))).json()) as { order_id: string; order_token: string };
  const o = await env.DB.prepare('SELECT payment_session_id, total_agorot FROM orders WHERE id = ?')
    .bind(r.order_id)
    .first<{ payment_session_id: string; total_agorot: number }>();
  return { orderId: r.order_id, token: r.order_token, session: o!.payment_session_id, total: o!.total_agorot };
}
async function postEvent(event: object, provider = 'mock') {
  const body = JSON.stringify(event);
  return req(`/api/webhooks/payment/${provider}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-mock-signature': await signWebhook(SECRET, body, Math.floor(Date.now() / 1000)) },
    body,
  });
}
async function paidOrder(items?: { variant_id: string; qty: number; house?: string }[]) {
  const o = await pendingOrder(items);
  const r = (await (await postEvent({ id: `evt_${o.orderId}`, type: 'payment.succeeded', session_id: o.session, amount_agorot: o.total })).json()) as {
    outcome: string;
  };
  expect(r.outcome).toBe('paid');
  return o;
}
const one = async <T>(sql: string, ...b: unknown[]) =>
  (await env.DB.prepare(sql)
    .bind(...b)
    .first<T>())!;
const n = async (sql: string, ...b: unknown[]) => (await one<{ n: number }>(sql, ...b)).n;
const invoiceRows = (id: string) => n("SELECT COUNT(*) AS n FROM audit_log WHERE action = 'order.invoiced' AND subject = ?", id);

/** a provider like a network one: slow, counting every invoice it issues, with the key it was given */
function provider(o: { delayMs?: number; find?: boolean; idempotent?: boolean } = {}): InvoiceProvider & { issued: { order: string; key: string }[] } {
  const issued: { order: string; key: string }[] = [];
  const byKey = new Map<string, IssuedInvoice>();
  const p: InvoiceProvider & { issued: typeof issued } = {
    id: 'counting',
    idempotent: o.idempotent ?? false,
    issued,
    async issue(input, { idempotency_key }) {
      await new Promise((r) => setTimeout(r, o.delayMs ?? 5));
      if (p.idempotent && byKey.has(idempotency_key)) return byKey.get(idempotency_key)!;
      issued.push({ order: input.order_id, key: idempotency_key });
      const inv = { invoice_id: `INV-${input.order_id}-${issued.length}`, url: null };
      byKey.set(idempotency_key, inv);
      return inv;
    },
  };
  if (o.find) p.find = async (orderId) => byKey.get(orderId) ?? null;
  return p;
}
/** the database, with the invoice's record step failing once (a crash between the provider call and the record) */
function crashOnceAtRecord(e: Env): Env {
  const prepare = e.DB.prepare.bind(e.DB);
  let fail = true;
  return {
    ...e,
    DB: {
      ...e.DB,
      batch: e.DB.batch.bind(e.DB),
      prepare: (sql: string) => {
        if (fail && sql.startsWith("UPDATE invoices SET state = 'issued'")) {
          fail = false;
          return { bind: () => ({ run: async () => Promise.reject(new Error('D1 unavailable')) }) } as unknown as ReturnType<typeof prepare>;
        }
        return prepare(sql);
      },
    } as unknown as D1Database,
  };
}

describe('ת16: one invoice per order, claimed in D1 before the provider is called', () => {
  it('two (and three) runs at once issue one invoice; the others are retried and then skip', async () => {
    const { orderId } = await paidOrder();
    const p = provider();
    const r = await Promise.all([processInvoiceJob(env, orderId, p), processInvoiceJob(env, orderId, p), processInvoiceJob(env, orderId, p)]);
    expect(r.sort()).toEqual(['invoiced', 'retry', 'retry']);
    expect(p.issued).toEqual([{ order: orderId, key: orderId }]);
    expect(await invoiceRows(orderId)).toBe(1);
    expect(await one(`SELECT state, provider_invoice_id FROM invoices WHERE order_id = ?`, orderId)).toEqual({
      state: 'issued',
      provider_invoice_id: `INV-${orderId}-1`,
    });
    // the order carries the number; the retried runs now skip
    expect(await one('SELECT invoice_provider, invoice_number FROM orders WHERE id = ?', orderId)).toEqual({
      invoice_provider: 'counting',
      invoice_number: `INV-${orderId}-1`,
    });
    expect(await processInvoiceJob(env, orderId, p)).toBe('skipped');
    expect(p.issued).toHaveLength(1);
  });

  it('the queue delivers the invoice message twice in one batch, and again later: one invoice', async () => {
    const { orderId } = await paidOrder();
    const msg = () => ({ body: { kind: 'issue-invoice', order_id: orderId } as SupplierJob, attempts: 1, ack: vi.fn(), retry: vi.fn() });
    const batch = [msg(), msg()];
    await worker.queue!({ messages: batch } as unknown as MessageBatch<SupplierJob>, env);
    await worker.queue!({ messages: [msg()] } as unknown as MessageBatch<SupplierJob>, env);
    expect(await invoiceRows(orderId)).toBe(1);
    expect(await n('SELECT COUNT(*) AS n FROM invoices WHERE order_id = ?', orderId)).toBe(1);
  });

  it('a crash between the call and the record: the retry asks the provider (find) and records the first invoice, never a second', async () => {
    const { orderId } = await paidOrder();
    const p = provider({ find: true });
    await expect(processInvoiceJob(crashOnceAtRecord(env), orderId, p)).rejects.toThrow('D1 unavailable');
    expect(p.issued).toHaveLength(1);
    expect(await one('SELECT state FROM invoices WHERE order_id = ?', orderId)).toEqual({ state: 'claimed' });
    // at once: the claim is fresh (a run may still be calling), so the job is retried later, nothing issued
    expect(await processInvoiceJob(env, orderId, p)).toBe('retry');
    // after the lease: the provider is asked for the order's invoice, and that one is recorded
    const later = () => Date.now() + INVOICE_LEASE_MS + 1000;
    expect(await processInvoiceJob(env, orderId, p, { now: later })).toBe('invoiced');
    expect(p.issued).toHaveLength(1);
    expect(await one('SELECT state, provider_invoice_id FROM invoices WHERE order_id = ?', orderId)).toEqual({
      state: 'issued',
      provider_invoice_id: `INV-${orderId}-1`,
    });
    expect(await invoiceRows(orderId)).toBe(1);
  });

  it('a crash with a provider that dedupes by the key: the retry sends the same key, and the provider returns the first invoice', async () => {
    const { orderId } = await paidOrder();
    const p = provider({ idempotent: true });
    await expect(processInvoiceJob(crashOnceAtRecord(env), orderId, p)).rejects.toThrow('D1 unavailable');
    expect(await processInvoiceJob(env, orderId, p, { now: () => Date.now() + INVOICE_LEASE_MS + 1000 })).toBe('invoiced');
    expect(p.issued).toEqual([{ order: orderId, key: orderId }]);
    expect(await one('SELECT provider_invoice_id, attempts FROM invoices WHERE order_id = ?', orderId)).toEqual({
      provider_invoice_id: `INV-${orderId}-1`,
      attempts: 2,
    });
  });

  it('a crash with a provider that can neither be asked nor dedupes: unresolved, loudly, for a person; never a second invoice', async () => {
    const { orderId } = await paidOrder();
    const p = provider();
    const err = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    await expect(processInvoiceJob(crashOnceAtRecord(env), orderId, p)).rejects.toThrow('D1 unavailable');
    expect(await processInvoiceJob(env, orderId, p, { now: () => Date.now() + INVOICE_LEASE_MS + 1000 })).toBe('unresolved');
    expect(await processInvoiceJob(env, orderId, p, { now: () => Date.now() + 2 * INVOICE_LEASE_MS })).toBe('unresolved');
    expect(p.issued).toHaveLength(1);
    expect((await one<{ state: string }>('SELECT state FROM invoices WHERE order_id = ?', orderId)).state).toBe('unresolved');
    expect(await n("SELECT COUNT(*) AS n FROM audit_log WHERE action = 'invoice.unresolved' AND subject = ?", orderId)).toBe(1);
    expect(err).toHaveBeenCalled();
    err.mockRestore();
  });

  it('a refusal (nothing issued) releases the claim; another failure keeps it, so the provider is asked before any new invoice', async () => {
    const { orderId } = await paidOrder();
    const err = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const refusing: InvoiceProvider = {
      id: 'refusing',
      idempotent: false,
      issue: async () => {
        throw new InvoiceRefused('invoice_total_mismatch');
      },
    };
    expect(await processInvoiceJob(env, orderId, refusing)).toBe('retry');
    expect(await n('SELECT COUNT(*) AS n FROM invoices WHERE order_id = ?', orderId)).toBe(0);
    const timeout: InvoiceProvider = {
      id: 'timeout',
      idempotent: false,
      issue: async () => {
        throw new Error('network timeout');
      },
    };
    expect(await processInvoiceJob(env, orderId, timeout)).toBe('retry');
    expect(await one('SELECT state, last_error FROM invoices WHERE order_id = ?', orderId)).toEqual({ state: 'claimed', last_error: 'network timeout' });
    const p = provider();
    expect(await processInvoiceJob(env, orderId, p)).toBe('retry');
    expect(p.issued).toHaveLength(0);
    err.mockRestore();
  });

  it('the migration backfills an order invoiced before S12 (its audit row): the new job never issues it again', async () => {
    const { orderId } = await paidOrder();
    const raw = (env.DB as unknown as { _raw: { exec(sql: string): void } })._raw;
    raw.exec('DELETE FROM invoices');
    raw.exec(
      `INSERT INTO audit_log (at, actor, action, subject, detail) VALUES ('2026-11-09T10:00:00Z', 'invoice:mock', 'order.invoiced', '${orderId}', '{"invoice_id":"MOCK-INV-${orderId}","url":null}')`,
    );
    const sql = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), '../migrations/0005_invoices_set_parts_house.sql'), 'utf8');
    raw.exec(sql.split('\nALTER TABLE')[0]!.replace(/CREATE TABLE invoices \([\s\S]*?\);\n/, ''));
    expect(await one('SELECT state, provider, provider_invoice_id FROM invoices WHERE order_id = ?', orderId)).toEqual({
      state: 'issued',
      provider: 'mock',
      provider_invoice_id: `MOCK-INV-${orderId}`,
    });
    const p = provider();
    expect(await processInvoiceJob(env, orderId, p)).toBe('skipped');
    expect(p.issued).toHaveLength(0);
  });
});

describe('ת18: only a paid order is invoiced (paid_at, and a closed list of statuses), re-checked in the job', () => {
  it('pending, failed, and canceled or refunded without a payment: never; paid, sent and supplier_error: once', async () => {
    const p = provider({ delayMs: 0 });
    const { orderId: pending } = await pendingOrder();
    for (const status of ['pending_payment', 'payment_failed', 'canceled', 'refunded']) {
      await env.DB.prepare('UPDATE orders SET status = ? WHERE id = ?').bind(status, pending).run();
      expect(await processInvoiceJob(env, pending, p), status).toBe('skipped');
    }
    // a status a paid order can be in, but no payment recorded: never
    await env.DB.prepare("UPDATE orders SET status = 'paid' WHERE id = ?").bind(pending).run();
    expect(await processInvoiceJob(env, pending, p)).toBe('skipped');
    expect(p.issued).toEqual([]);
    expect(await n('SELECT COUNT(*) AS n FROM invoices')).toBe(0);
    for (const status of ['paid', 'sent_to_supplier', 'supplier_error']) {
      const { orderId } = await paidOrder();
      await env.DB.prepare('UPDATE orders SET status = ? WHERE id = ?').bind(status, orderId).run();
      expect(await processInvoiceJob(env, orderId, p), status).toBe('invoiced');
    }
    expect(p.issued).toHaveLength(3);
  });

  it('a paid order canceled before its invoice job runs is not invoiced (the claim re-checks)', async () => {
    const { orderId } = await paidOrder();
    await env.DB.prepare("UPDATE orders SET status = 'canceled' WHERE id = ?").bind(orderId).run();
    const p = provider({ delayMs: 0 });
    expect(await processInvoiceJob(env, orderId, p)).toBe('skipped');
    expect(p.issued).toEqual([]);
  });
});

describe('ת17: production fails closed on every provider variable', () => {
  const VARS = Object.keys(PROVIDERS) as ProviderVar[];
  const bad = [undefined, '', 'mock', 'UNDECIDED', 'Mock', ' cj', 'CJ', 'Grow', 'morning ', 'stripe'];

  for (const name of VARS)
    it(`${name}: exactly a provider from the closed list; mock only outside production; anything else refused`, () => {
      for (const id of PROVIDERS[name]) {
        expect(providerOf({ ENVIRONMENT: 'production', [name]: id }, name)).toEqual({ ok: true, id, mock: false });
        expect(providerOf({ ENVIRONMENT: 'preview', [name]: id }, name)).toEqual({ ok: true, id, mock: false });
      }
      for (const v of bad) {
        const r = providerOf({ ENVIRONMENT: 'production', [name]: v }, name);
        expect(r.ok, `${name}=${String(v)} in production`).toBe(false);
      }
      for (const e of ['development', 'preview', 'preview-local', 'test'])
        expect(providerOf({ ENVIRONMENT: e, [name]: 'mock' }, name)).toEqual({ ok: true, id: 'mock', mock: true });
      // an ENVIRONMENT that is not a named non-production one is production: missing, misspelled, another case
      for (const e of [undefined, '', 'prod', 'Production', 'staging', 'dev'])
        expect(providerOf({ ENVIRONMENT: e, [name]: 'mock' }, name).ok, `ENVIRONMENT=${String(e)}`).toBe(false);
      // missing is never the mock, outside production either: the config names its provider
      expect(providerOf({ ENVIRONMENT: 'development' }, name).ok).toBe(false);
    });

  it('isProduction: only the named non-production environments are not production', () => {
    expect(['development', 'preview', 'preview-local', 'test'].map((e) => isProduction({ ENVIRONMENT: e }))).toEqual([false, false, false, false]);
    expect(['production', '', 'prod', 'PREVIEW'].map((e) => isProduction({ ENVIRONMENT: e }))).toEqual([true, true, true, true]);
    expect(isProduction({})).toBe(true);
  });

  it('the deploy check: every environment in wrangler.jsonc passes; mock or a typo in production fails it', () => {
    const text = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), '../wrangler.jsonc'), 'utf8');
    const cfg = parseJsonc(text) as { vars: Record<string, unknown>; env: Record<string, { vars: Record<string, unknown> }> };
    expect(configIssues(cfg.vars)).toEqual([]);
    for (const [name, e] of Object.entries(cfg.env)) expect(configIssues(e.vars), name).toEqual([]);
    const prod = cfg.env.production!.vars;
    expect(prod.ENVIRONMENT).toBe('production');
    expect(configIssues({ ...prod, SUPPLIER_PROVIDER: 'mock' })).toEqual([expect.stringContaining('SUPPLIER_PROVIDER=mock is refused in production')]);
    expect(configIssues({ ...prod, SUPPLIER_PROVIDER: 'CJ' })).toEqual([expect.stringContaining('SUPPLIER_PROVIDER="CJ" is not a provider')]);
    expect(configIssues({ ...prod, INVOICE_PROVIDER: 'mock', PAYMENT_PROVIDER: undefined })).toHaveLength(2);
    expect(configIssues({ ...prod, ENVIRONMENT: undefined })).toContain('ENVIRONMENT is not set (it is read as production)');
  });

  it('the invoice job in production with INVOICE_PROVIDER missing, mock, UNDECIDED or a typo: retried, loudly; nothing recorded as invoiced', async () => {
    const err = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    for (const v of [undefined, 'mock', 'UNDECIDED', 'Morning']) {
      const { orderId } = await paidOrder();
      const prod = { ...env, ENVIRONMENT: 'production' as const, INVOICE_PROVIDER: v };
      expect(await processInvoiceJob(prod, orderId), String(v)).toBe('retry');
      expect(await processSupplierJob(prod, { kind: 'issue-invoice', order_id: orderId }, 1)).toBe('retry');
      expect(await n('SELECT COUNT(*) AS n FROM invoices WHERE order_id = ?', orderId)).toBe(0);
      expect(await invoiceRows(orderId)).toBe(0);
      expect((await one<{ invoice_number: string | null }>('SELECT invoice_number FROM orders WHERE id = ?', orderId)).invoice_number).toBeNull();
    }
    expect(err.mock.calls.some((c) => String(c[0]).includes('INVOICE_PROVIDER'))).toBe(true);
    err.mockRestore();
  });

  it('the supplier job in production with SUPPLIER_PROVIDER missing, mock or CJ: retried, loudly; the order stays paid, never sent', async () => {
    const err = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    for (const v of [undefined, 'mock', 'CJ', 'UNDECIDED']) {
      const { orderId } = await paidOrder();
      const prod = { ...env, ENVIRONMENT: 'production' as const, SUPPLIER_PROVIDER: v as string };
      expect(await processSupplierJob(prod, { kind: 'submit-order', order_id: orderId }, 1), String(v)).toBe('retry');
      expect((await one<{ status: string }>('SELECT status FROM orders WHERE id = ?', orderId)).status).toBe('paid');
      expect(await n("SELECT COUNT(*) AS n FROM supplier_shipments WHERE order_id = ? AND status = 'submitted'", orderId)).toBe(0);
      expect(await n("SELECT COUNT(*) AS n FROM audit_log WHERE action = 'supplier.submitted' AND subject = ?", orderId)).toBe(0);
      const row = await one<{ last_error: string }>(
        "SELECT last_error FROM supplier_shipments WHERE order_id = ? AND fulfillment_source = 'dropship_cj'",
        orderId,
      );
      expect(row.last_error).toMatch(/^config: SUPPLIER_PROVIDER/);
    }
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(supplierClient({ ENVIRONMENT: 'production', SUPPLIER_PROVIDER: 'cj' }).ok).toBe(true);
    fetchSpy.mockRestore();
    err.mockRestore();
  });

  it('the payment in production: mock or a value that is not a provider leaves no order behind (503)', async () => {
    for (const v of ['mock', 'UNDECIDED', 'Grow', '']) {
      env = { ...env, ENVIRONMENT: 'production', PAYMENT_PROVIDER: v };
      const r = await req('/api/checkout', json(checkoutBody(await cartWith([{ variant_id: 'vase-a:default', qty: 1 }]))));
      expect(r.status, v).toBe(503);
    }
    expect(await n('SELECT COUNT(*) AS n FROM orders')).toBe(0);
  });
});

describe('ת19: a queue message fails alone, never the batch', () => {
  it('INVOICE_PROVIDER=UNDECIDED: the invoice message is retried; the supplier message after it in the batch is processed', async () => {
    const err = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const { orderId } = await paidOrder();
    const e = { ...env, ENVIRONMENT: 'preview' as const, INVOICE_PROVIDER: 'UNDECIDED' };
    const msg = (body: SupplierJob) => ({ body, attempts: 1, ack: vi.fn(), retry: vi.fn() });
    const m1 = msg({ kind: 'issue-invoice', order_id: orderId });
    const m2 = msg({ kind: 'submit-order', order_id: orderId });
    await worker.queue!({ messages: [m1, m2] } as unknown as MessageBatch<SupplierJob>, e);
    expect(m1.retry).toHaveBeenCalledTimes(1);
    expect(m1.ack).not.toHaveBeenCalled();
    expect(m2.ack).toHaveBeenCalledTimes(1);
    expect((await one<{ status: string }>('SELECT status FROM orders WHERE id = ?', orderId)).status).toBe('sent_to_supplier');
    err.mockRestore();
  });

  it('a message that throws (the database failing under it) is retried alone; the next one is acknowledged', async () => {
    const err = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const { orderId } = await paidOrder();
    const prepare = env.DB.prepare.bind(env.DB);
    let calls = 0;
    const flaky = {
      ...env,
      DB: {
        ...env.DB,
        batch: env.DB.batch.bind(env.DB),
        prepare: (sql: string) => {
          if (calls++ === 0) throw new Error('D1 overloaded');
          return prepare(sql);
        },
      } as unknown as D1Database,
    };
    const m1 = { body: { kind: 'submit-order', order_id: orderId } as SupplierJob, attempts: 1, ack: vi.fn(), retry: vi.fn() };
    const m2 = { body: { kind: 'issue-invoice', order_id: orderId } as SupplierJob, attempts: 1, ack: vi.fn(), retry: vi.fn() };
    await worker.queue!({ messages: [m1, m2] } as unknown as MessageBatch<SupplierJob>, flaky);
    expect(m1.retry).toHaveBeenCalledTimes(1);
    expect(m2.ack).toHaveBeenCalledTimes(1);
    expect(await invoiceRows(orderId)).toBe(1);
    expect(err.mock.calls.some((c) => String(c[0]).includes(`submit-order for order ${orderId} failed`))).toBe(true);
    err.mockRestore();
  });
});

describe('ת20: only the configured payment provider’s webhook is heard', () => {
  it('with PAYMENT_PROVIDER=grow outside production, a validly signed mock event is 404 and pays nothing', async () => {
    const o = await pendingOrder();
    env = { ...env, ENVIRONMENT: 'preview', PAYMENT_PROVIDER: 'grow' };
    const r = await postEvent({ id: 'evt_after_switch', type: 'payment.succeeded', session_id: o.session, amount_agorot: o.total });
    expect(r.status).toBe(404);
    expect((await one<{ status: string }>('SELECT status FROM orders WHERE id = ?', o.orderId)).status).toBe('pending_payment');
    expect(await n('SELECT COUNT(*) AS n FROM payment_events')).toBe(0);
    // and the mock's own page is closed too
    expect((await req(`/mock-pay/${o.session}`)).status).toBe(404);
    // back on the mock, its webhook is heard again
    env = { ...env, PAYMENT_PROVIDER: 'mock' };
    expect((await postEvent({ id: 'evt_after_back', type: 'payment.succeeded', session_id: o.session, amount_agorot: o.total })).status).toBe(200);
  });
});

describe('the triptych (S11 question 2): the supplier order carries its three SKUs, never 3 × print 1', () => {
  const SET = 'prints-a:1+40x60';
  it('checkout snapshots the parts; the supplier order is one of each print per set (2 sets: 2 of each)', async () => {
    const { orderId } = await paidOrder([
      { variant_id: SET, qty: 2 },
      { variant_id: 'candles-a:default', qty: 1 },
      { variant_id: 'vase-a:default', qty: 1 },
    ]);
    const item = await one<{ supplier_lines_json: string; unit_sell_qty: number }>(
      'SELECT supplier_lines_json, unit_sell_qty FROM order_items WHERE order_id = ? AND variant_id = ?',
      orderId,
      SET,
    );
    expect(JSON.parse(item.supplier_lines_json)).toEqual([
      { supplier_sku: 'TRIP1-40x60', qty: 1 },
      { supplier_sku: 'TRIP2-40x60', qty: 1 },
      { supplier_sku: 'TRIP3-40x60', qty: 1 },
    ]);
    expect(await processSupplierJob(env, { kind: 'submit-order', order_id: orderId }, 1)).toBe('submitted');
    const sent = JSON.parse(
      (await one<{ request_json: string }>('SELECT request_json FROM supplier_shipments WHERE order_id = ? AND supplier = ?', orderId, 'mock')).request_json,
    ) as {
      lines: [string, number][];
    };
    // the pair of candle holders is 2 × its one SKU (a pack of one SKU); the triptych is its three different prints
    expect(sent.lines).toEqual([
      ['TRIP1-40x60', 2],
      ['TRIP2-40x60', 2],
      ['TRIP3-40x60', 2],
      ['SKU1', 2],
      ['SKU1', 1],
    ]);
  });

  it('the expansion: a snapshot first; an order from before S12 takes the set’s composition; a set without one is refused, never N × its SKU', () => {
    const base = { product_id: 'prints-a', variant_id: SET, qty: 1, unit_sell_qty: 3, pack: 'set' as const, supplier_sku: 'TRIP1-40x60' };
    const comp = JSON.stringify(['TRIP1-40x60', 'TRIP2-40x60', 'TRIP3-40x60']);
    expect(supplierLines([{ ...base, supplier_lines_json: null, set_skus_json: comp, set_incomplete: null }]).map((l) => [l.supplier_sku, l.qty])).toEqual([
      ['TRIP1-40x60', 1],
      ['TRIP2-40x60', 1],
      ['TRIP3-40x60', 1],
    ]);
    expect(() => supplierLines([{ ...base, supplier_lines_json: null, set_skus_json: null, set_incomplete: 'which 3 of 8 is not named' }])).toThrow(
      'set_composition_missing',
    );
    const same = JSON.stringify([1, 2, 3].map(() => ({ supplier_sku: 'TRIP1-40x60', qty: 1 })));
    expect(() => supplierLines([{ ...base, supplier_lines_json: same, set_skus_json: null, set_incomplete: null }])).toThrow('set_parts_not_distinct');
    // not a set of distinct SKUs: its SKU × the sale's units, as before
    expect(supplierLines([{ ...base, unit_sell_qty: 2, supplier_lines_json: null, set_skus_json: null, set_incomplete: null }])).toEqual([
      { supplier_sku: 'TRIP1-40x60', product_id: 'prints-a', qty: 2 },
    ]);
  });

  it('a set whose card does not name its parts is refused (422 set_unavailable), and a cart holding it loses it before the payment', async () => {
    const id = await cartWith([{ variant_id: SET, qty: 1 }]);
    await env.DB.prepare("UPDATE product_variants SET set_skus_json = NULL, set_incomplete = 'which 3 of 8 is not named' WHERE id = ?").bind(SET).run();
    const r = await req(`/api/cart/${id}/items`, json({ variant_id: SET, qty: 2 }, 'PUT'));
    expect(r.status).toBe(422);
    expect(await r.json()).toMatchObject({ error: 'set_unavailable', message_he: 'הסט הזה עוד לא זמין להזמנה.' });
    const co = await req('/api/checkout', json(checkoutBody(id)));
    expect(co.status).toBe(409);
    expect(await n('SELECT COUNT(*) AS n FROM orders')).toBe(0);
  });
});

describe('ת21: the line keeps the house it was bought in', () => {
  it('the cart takes the house; the order line snapshots it; a line bought off the engine has none', async () => {
    const o = await paidOrder([
      { variant_id: 'cushion-a:o-beige45', qty: 1, house: 'warm-modern' },
      { variant_id: 'vase-a:default', qty: 1 },
    ]);
    const view = (await (await req(`/api/orders/${o.orderId}`, { headers: { 'x-order-token': o.token } })).json()) as {
      lines: { variant_id: string; house: string | null }[];
    };
    expect(view.lines.map((l) => [l.variant_id, l.house])).toEqual([
      ['cushion-a:o-beige45', 'warm-modern'],
      ['vase-a:default', null],
    ]);
    const { id } = (await (await req('/api/cart', { method: 'POST' })).json()) as { id: string };
    expect((await req(`/api/cart/${id}/items`, json({ variant_id: 'vase-a:default', qty: 1, house: 'Warm Modern!' }, 'PUT'))).status).toBe(422);
  });
});
