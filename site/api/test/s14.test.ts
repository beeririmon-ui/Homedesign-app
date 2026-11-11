/**
 * S14, fixes from QA S11–S12 (qa/reports/2026-11-11-site-track-qa-s11-s12.md), on the Worker:
 *  - ת27: the supplier line carries the variant's SKU, never the card's product-level SKU: the floor lamp, and every
 *    product sold with sale exclusions or as one SKU, on the real cards and a real build (made here, into
 *    .generated/catalog.vitest-s14-api.*), through checkout, payment and the supplier job.
 *  - ת31: a provider call never outlives its claim's lease (a deadline far below it), and only the claim's holder
 *    records: QA's "lease overrun" (a call that hangs past the lease while another run takes the claim over), for the
 *    invoice, the credit note and the supplier order.
 */
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { execFileSync } from 'node:child_process';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { signWebhook, type FullCatalog } from '@hd/shared';
import { app } from '../src/app';
import type { Env, SupplierJob } from '../src/env';
import { buildSeedSql } from '../scripts/seed';
import { createD1, migrate } from './d1-shim';
import { catalog as fixture } from './fixture';
import { processSupplierJob, SUBMIT_CALL_TIMEOUT_MS, SUBMIT_LEASE_MS } from '../src/lib/fulfillment';
import {
  INVOICE_CALL_TIMEOUT_MS,
  INVOICE_LEASE_MS,
  processCreditNoteJob,
  processInvoiceJob,
  type InvoiceProvider,
  type IssuedInvoice,
} from '../src/lib/invoices';
import { CallTimedOut, PROVIDER_CALL_TIMEOUT_MS, withDeadline } from '../src/lib/deadline';

const here = dirname(fileURLToPath(import.meta.url));
const SITE = resolve(here, '../..');
const REPO = resolve(SITE, '..');
const SECRET = 'test-webhook-secret-s14-not-a-key';

let env: Env;
function envWith(cat: FullCatalog): Env {
  const DB = createD1();
  migrate(DB, buildSeedSql(cat));
  return {
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
}
const req = (path: string, init?: RequestInit) => app.request(`http://localhost${path}`, init, env);
const json = (body: unknown, method = 'POST'): RequestInit => ({ method, headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
const one = async <T>(sql: string, ...b: unknown[]) =>
  (await env.DB.prepare(sql)
    .bind(...b)
    .first<T>())!;
const n = async (sql: string, ...b: unknown[]) => (await one<{ n: number }>(sql, ...b)).n;
async function paidOrder(items: { variant_id: string; qty: number }[]): Promise<string> {
  const { id } = (await (await req('/api/cart', { method: 'POST' })).json()) as { id: string };
  for (const i of items) {
    const r = await req(`/api/cart/${id}/items`, json(i, 'PUT'));
    expect(r.status, `${i.variant_id}: ${await r.clone().text()}`).toBe(200);
  }
  const c = (await (
    await req(
      '/api/checkout',
      json({
        cart_id: id,
        customer: { full_name: 'ישראלה ישראלי', email: 'buyer@example.com', phone: '050-1234567' },
        address: { city: 'תל אביב', street: 'הרצל', house: '10' },
        shipping_method: 'economy',
        consents: { terms: true, marketing: false },
      }),
    )
  ).json()) as { order_id: string };
  const o = await one<{ payment_session_id: string; total_agorot: number }>('SELECT payment_session_id, total_agorot FROM orders WHERE id = ?', c.order_id);
  const body = JSON.stringify({ id: `evt_${c.order_id}`, type: 'payment.succeeded', session_id: o.payment_session_id, amount_agorot: o.total_agorot });
  const r = await req('/api/webhooks/payment/mock', {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-mock-signature': await signWebhook(SECRET, body, Math.floor(Date.now() / 1000)) },
    body,
  });
  expect(((await r.json()) as { outcome: string }).outcome).toBe('paid');
  return c.order_id;
}

// ---------- ת27, on the real cards and a real build ----------
type Card = { id: string; supplier?: { sku?: string | null }; options?: { default_sku: string; skus: { id: string }[] } | null };
const walk = (d: string): string[] =>
  readdirSync(d).flatMap((f) => (statSync(join(d, f)).isDirectory() ? walk(join(d, f)) : f.endsWith('.json') ? [join(d, f)] : []));
const cards = new Map<string, Card>();
for (const f of walk(join(REPO, 'data/products'))) {
  try {
    const c = JSON.parse(readFileSync(f, 'utf8')) as Card;
    if (typeof c.id === 'string') cards.set(c.id, c);
  } catch {
    /* not a card */
  }
}
const exclusions = (JSON.parse(readFileSync(join(REPO, 'data/catalog/sale-exclusions.json'), 'utf8')) as { exclusions: { card_id: string }[] }).exclusions;
let real: FullCatalog;

describe('ת27: the supplier line carries the variant’s SKU (real cards, a real build)', () => {
  beforeAll(() => {
    execFileSync(
      process.execPath,
      [
        '--import',
        'tsx',
        'tools/build-catalog.ts',
        '--rooms=living-room',
        '--products=../data/story/story.json,tools/house/living-room.warm-modern.json',
        '--out=vitest-s14-api',
      ],
      { cwd: SITE, stdio: 'pipe' },
    );
    real = JSON.parse(readFileSync(join(SITE, '.generated/catalog.vitest-s14-api.full.json'), 'utf8')) as FullCatalog;
  }, 120_000);
  beforeEach(() => {
    env = envWith(real);
  });

  it('the floor lamp, bought and paid: the order line and the supplier request carry CJYD224754407GT, never CJYD2247544', async () => {
    const lamp = real.products.find((p) => p.card_id === 'floor-lamp-cj-pleated-walnut-stem-158')!;
    const orderId = await paidOrder([{ variant_id: lamp.variants_full![0]!.id, qty: 1 }]);
    expect((await one<{ supplier_sku: string }>('SELECT supplier_sku FROM order_items WHERE order_id = ?', orderId)).supplier_sku).toBe('CJYD224754407GT');
    expect(await processSupplierJob(env, { kind: 'submit-order', order_id: orderId }, 1)).toBe('submitted');
    const sent = JSON.parse((await one<{ request_json: string }>('SELECT request_json FROM supplier_shipments WHERE order_id = ?', orderId)).request_json) as {
      lines: [string, number][];
    };
    expect(sent.lines).toEqual([['CJYD224754407GT', 1]]);
  });

  it('every product with sale exclusions or one SKU sold, in one order: each supplier line is the variant’s SKU', async () => {
    const excluded = new Set(exclusions.map((e) => e.card_id));
    const picked = real.products.filter((p) => {
      const card = cards.get(p.card_id ?? '');
      return card && p.availability.status === 'available' && p.price_agorot !== null && (excluded.has(card.id) || !p.options);
    });
    expect(picked.map((p) => p.card_id)).toEqual(
      expect.arrayContaining([
        'floor-lamp-cj-pleated-walnut-stem-158',
        'accent-sconces-cj-ribbed-travertine-half-cylinder-wood-bracket',
        'bowl-cj-glutinous-white-belly-bowl-21',
      ]),
    );
    const items = picked.flatMap((p) => p.variants_full!.filter((v) => v.active && !v.set_part).map((v) => ({ variant_id: v.id, qty: 1 })));
    const orderId = await paidOrder(items);
    expect(await processSupplierJob(env, { kind: 'submit-order', order_id: orderId }, 1)).toBe('submitted');
    const sent = JSON.parse((await one<{ request_json: string }>('SELECT request_json FROM supplier_shipments WHERE order_id = ?', orderId)).request_json) as {
      lines: [string, number][];
    };
    const { results } = await env.DB.prepare('SELECT product_id, supplier_sku FROM order_items WHERE order_id = ? ORDER BY line').bind(orderId).all<{
      product_id: string;
      supplier_sku: string;
    }>();
    expect(results.length).toBe(items.length);
    for (const r of results) {
      const card = cards.get(real.products.find((p) => p.id === r.product_id)!.card_id!)!;
      const skus = card.options?.skus.map((s) => s.id) ?? [];
      // with options: one of the card's option SKUs; without: never a product-level code (the two CJ ones resolved)
      if (skus.length) expect(skus, `${card.id}: ${r.supplier_sku}`).toContain(r.supplier_sku);
      expect(r.supplier_sku, card.id).not.toMatch(/^(CJYD2247544|CJJT1610110|CJYD2389779)$/);
      expect(sent.lines.map((l) => l[0])).toContain(r.supplier_sku);
    }
    const bowl = results.find((r) => real.products.find((p) => p.id === r.product_id)!.card_id === 'bowl-cj-glutinous-white-belly-bowl-21')!;
    expect(bowl.supplier_sku).toBe('CJYD238977901AZ');
  });

  it('every active variant in the seeded shop, of a card with options: its supplier SKU is one of the card’s option SKUs', async () => {
    const { results } = await env.DB.prepare(
      'SELECT v.id, v.supplier_sku, v.set_skus_json, p.source_path FROM product_variants v JOIN products p ON p.id = v.product_id WHERE v.active = 1 AND v.set_part = 0',
    ).all<{ id: string; supplier_sku: string | null; set_skus_json: string | null; source_path: string }>();
    expect(results.length).toBeGreaterThan(100);
    const bad: string[] = [];
    for (const r of results) {
      const card = cards.get(
        r.source_path
          .split('/')
          .pop()!
          .replace(/\.json$/, ''),
      );
      if (!card?.options) continue;
      const skus = new Set(card.options.skus.map((s) => s.id));
      if (!r.supplier_sku || !skus.has(r.supplier_sku)) bad.push(`${r.id}: ${r.supplier_sku}`);
      for (const part of r.set_skus_json ? (JSON.parse(r.set_skus_json) as string[]) : []) if (!skus.has(part)) bad.push(`${r.id}: part ${part}`);
    }
    expect(bad).toEqual([]);
  });
});

// ---------- ת31, on the test catalog ----------
describe('ת31: a provider call never outlives its claim, and only the claim’s holder records', () => {
  beforeEach(() => {
    env = envWith(fixture);
  });

  it('the deadline is far below every lease; past it the call is aborted and fails as "may have issued"', async () => {
    expect(PROVIDER_CALL_TIMEOUT_MS * 5).toBeLessThanOrEqual(INVOICE_LEASE_MS);
    expect(INVOICE_CALL_TIMEOUT_MS * 5).toBeLessThanOrEqual(INVOICE_LEASE_MS);
    expect(SUBMIT_CALL_TIMEOUT_MS * 5).toBeLessThanOrEqual(SUBMIT_LEASE_MS);
    let aborted: unknown = null;
    const hung = withDeadline('hung', 30, (signal) => new Promise<never>(() => signal.addEventListener('abort', () => (aborted = signal.reason))));
    await expect(hung).rejects.toBeInstanceOf(CallTimedOut);
    expect(aborted).toBeInstanceOf(CallTimedOut);
    expect(await withDeadline('quick', 1000, async () => 7)).toBe(7);
  });

  /** a provider whose first issue hangs until released (QA's adversarial case); it can be asked (find), does not dedupe */
  function hanging() {
    let release!: () => void;
    const hang = new Promise<void>((r) => (release = r));
    const issued: IssuedInvoice[] = [];
    let calls = 0;
    const p: InvoiceProvider = {
      id: 'hanging',
      idempotent: false,
      async issue(input) {
        const first = ++calls === 1;
        if (first) await hang;
        const inv = { invoice_id: `INV-${input.order_id}-${issued.length + 1}${first ? '-late' : ''}`, url: null };
        issued.push(inv);
        return inv;
      },
      async find() {
        return issued[0] ?? null;
      },
    };
    return { p, issued, release };
  }

  it('QA "lease overrun": the hung call is given up at its deadline, the takeover records, and the late answer records nothing', async () => {
    const orderId = await paidOrder([{ variant_id: 'vase-a:default', qty: 1 }]);
    const { p, issued, release } = hanging();
    const err = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    let t = Date.now();
    const now = () => t;
    // the first run: its call hangs; at the deadline the run gives up (a failure that may have issued): the claim stays
    expect(await processInvoiceJob(env, orderId, p, { now, callTimeoutMs: 40 })).toBe('retry');
    expect((await one<{ state: string; last_error: string }>('SELECT state, last_error FROM invoices WHERE order_id = ?', orderId)).state).toBe('claimed');
    expect((await one<{ last_error: string }>('SELECT last_error FROM invoices WHERE order_id = ?', orderId)).last_error).toMatch(/no answer within/);
    // within the lease another run waits; after it, the provider is asked (nothing yet), the claim is taken over, issued
    expect(await processInvoiceJob(env, orderId, p, { now, callTimeoutMs: 40 })).toBe('retry');
    t += INVOICE_LEASE_MS + 1;
    expect(await processInvoiceJob(env, orderId, p, { now, callTimeoutMs: 40 })).toBe('invoiced');
    // the first call answers late: its run is long gone, so nothing records it
    release();
    await new Promise((r) => setTimeout(r, 20));
    expect(await one('SELECT state, provider_invoice_id FROM invoices WHERE order_id = ?', orderId)).toEqual({
      state: 'issued',
      provider_invoice_id: `INV-${orderId}-1`,
    });
    expect(await n("SELECT COUNT(*) AS n FROM audit_log WHERE action = 'order.invoiced' AND subject = ?", orderId)).toBe(1);
    expect(issued.map((i) => i.invoice_id)).toEqual([`INV-${orderId}-1`, `INV-${orderId}-2-late`]);
    err.mockRestore();
  });

  it('a run that lost its claim (it answered after a takeover) records nothing, and says so for a person', async () => {
    const orderId = await paidOrder([{ variant_id: 'vase-a:default', qty: 1 }]);
    const err = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    // the provider answers, but by then another run holds the claim (its claimed_at moved: a takeover)
    const p: InvoiceProvider = {
      id: 'slow',
      idempotent: false,
      async issue(input) {
        await env.DB.prepare("UPDATE invoices SET claimed_at = '2099-01-01T00:00:00.000Z' WHERE order_id = ?").bind(input.order_id).run();
        return { invoice_id: `INV-LOST-${input.order_id}`, url: null };
      },
    };
    expect(await processInvoiceJob(env, orderId, p)).toBe('retry');
    expect(await one('SELECT state, provider_invoice_id FROM invoices WHERE order_id = ?', orderId)).toEqual({ state: 'claimed', provider_invoice_id: null });
    expect((await one<{ invoice_number: string | null }>('SELECT invoice_number FROM orders WHERE id = ?', orderId)).invoice_number).toBeNull();
    expect(await n("SELECT COUNT(*) AS n FROM audit_log WHERE action = 'order.invoiced' AND subject = ?", orderId)).toBe(0);
    const lost = await one<{ detail: string }>("SELECT detail FROM audit_log WHERE action = 'invoice.claim_lost' AND subject = ?", orderId);
    expect(lost.detail).toContain(`INV-LOST-${orderId}`);
    expect(err).toHaveBeenCalled();
    err.mockRestore();
  });

  it('the credit note: the same deadline, and a lost claim records nothing', async () => {
    const orderId = await paidOrder([{ variant_id: 'vase-a:default', qty: 1 }]);
    expect(await processInvoiceJob(env, orderId)).toBe('invoiced');
    await env.DB.prepare(
      "INSERT INTO refunds (id, order_id, kind, amount_agorot, reason, state, provider, requested_by, claimed_at, completed_at, credit_state) VALUES ('rf-1', ?, 'partial', 1000, 'בדיקה', 'refunded', 'mock', 'test', ?, ?, 'pending')",
    )
      .bind(orderId, new Date().toISOString(), new Date().toISOString())
      .run();
    const err = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const base: InvoiceProvider = { id: 'cn', idempotent: false, issue: async () => ({ invoice_id: 'x', url: null }) };
    // hangs: given up at the deadline, the claim stays
    const hung: InvoiceProvider = { ...base, creditNote: () => new Promise(() => undefined) };
    expect(await processCreditNoteJob(env, 'rf-1', hung, { callTimeoutMs: 30 })).toBe('retry');
    expect(
      (await one<{ credit_state: string; credit_error: string }>('SELECT credit_state, credit_error FROM refunds WHERE id = ?', 'rf-1')).credit_error,
    ).toMatch(/no answer within/);
    // answers after a takeover: not recorded
    await env.DB.prepare("UPDATE refunds SET credit_state = 'pending', credit_claimed_at = NULL WHERE id = 'rf-1'").run();
    const late: InvoiceProvider = {
      ...base,
      async creditNote() {
        await env.DB.prepare("UPDATE refunds SET credit_claimed_at = '2099-01-01T00:00:00.000Z' WHERE id = 'rf-1'").run();
        return { credit_note_id: 'CN-LOST', url: null };
      },
    };
    expect(await processCreditNoteJob(env, 'rf-1', late)).toBe('retry');
    expect(await one('SELECT credit_state, credit_note_id FROM refunds WHERE id = ?', 'rf-1')).toEqual({ credit_state: 'claimed', credit_note_id: null });
    expect(await n("SELECT COUNT(*) AS n FROM audit_log WHERE action = 'refund.credit_claim_lost' AND subject = ?", orderId)).toBe(1);
    err.mockRestore();
  });

  it('the supplier order: a hung call is given up at the deadline (the order stays paid), and a lost claim records nothing', async () => {
    const orderId = await paidOrder([{ variant_id: 'vase-a:default', qty: 1 }]);
    const err = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const hung = { id: 'mock', submitOrder: () => new Promise<never>(() => undefined) };
    expect(await processSupplierJob(env, { kind: 'submit-order', order_id: orderId }, 1, { callTimeoutMs: 30, client: hung })).toBe('retry');
    expect(await one('SELECT status, last_error FROM supplier_shipments WHERE order_id = ?', orderId)).toEqual({
      status: 'failed',
      last_error: expect.stringMatching(/no answer within/),
    });
    expect((await one<{ status: string }>('SELECT status FROM orders WHERE id = ?', orderId)).status).toBe('paid');
    const late = {
      id: 'mock',
      async submitOrder(input: { order_id: string }) {
        // another run took the claim over while this call ran
        await env.DB.prepare("UPDATE supplier_shipments SET updated_at = '2099-01-01T00:00:00.000Z' WHERE order_id = ?").bind(input.order_id).run();
        return { supplier_order_id: `LOST-${input.order_id}`, raw: {} };
      },
    };
    expect(await processSupplierJob(env, { kind: 'submit-order', order_id: orderId }, 2, { client: late })).toBe('skipped');
    expect(await one('SELECT status, supplier_order_id FROM supplier_shipments WHERE order_id = ?', orderId)).toEqual({
      status: 'submitting',
      supplier_order_id: null,
    });
    expect((await one<{ status: string }>('SELECT status FROM orders WHERE id = ?', orderId)).status).toBe('paid');
    expect(await n("SELECT COUNT(*) AS n FROM audit_log WHERE action = 'supplier.submitted' AND subject = ?", orderId)).toBe(0);
    expect((await one<{ detail: string }>("SELECT detail FROM audit_log WHERE action = 'supplier.claim_lost' AND subject = ?", orderId)).detail).toContain(
      `LOST-${orderId}`,
    );
    err.mockRestore();
  });
});
