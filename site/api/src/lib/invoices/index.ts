/**
 * S9: the tax invoice, a job after "paid" (W2: the acquirer's invoicing module, else Morning; docs/architecture.md §8).
 * The provider is chosen by INVOICE_PROVIDER (lib/config.ts): `mock` outside production only; a real provider is added
 * when its documentation is in the repo (none is, so none is guessed).
 *
 * S12, QA S8–S10:
 * - **ת16, one invoice per order, whatever runs at once or crashes.** The order is claimed in D1 before the provider is
 *   called: a row in `invoices` (order_id PRIMARY KEY), `INSERT … ON CONFLICT DO NOTHING`. Only the run that made the row
 *   calls the provider, with the order id as the idempotency key. Another run while the claim is fresh is retried later.
 *   A claim left without a result (a crash between the call and the record) is resolved by asking the provider for the
 *   invoice of that order, never by issuing again; a provider that cannot be asked and does not honour the key leaves it
 *   `unresolved`, loudly, for a person.
 * - **ת18, only a paid order.** `paid_at` is set and the status is one a paid order can be in (a closed list), checked in
 *   the claim itself, so an order canceled or refunded before it was paid is never invoiced.
 */
import { providerOf, refuseLoudly } from '../config';

export type InvoiceInput = {
  order_id: string;
  issued_at: string;
  customer: { full_name: string; email: string; phone: string };
  lines: { name_he: string; qty: number; unit_price_agorot: number }[];
  shipping_agorot: number;
  total_agorot: number;
  /** VAT included in every price (studio rules ה: 18% on the whole price, shipping included) */
  vat_rate: number;
};
export type IssuedInvoice = { invoice_id: string; url: string | null };

/** S13 (2.5): a credit note (חשבונית זיכוי) against the order's invoice, for one refund. */
export type CreditNoteInput = {
  order_id: string;
  refund_id: string;
  /** the provider's number of the invoice it credits */
  invoice_id: string;
  amount_agorot: number;
  issued_at: string;
  customer: { full_name: string; email: string; phone: string };
  reason: string;
  vat_rate: number;
};
export type IssuedCreditNote = { credit_note_id: string; url: string | null };

export interface InvoiceProvider {
  readonly id: string;
  /** the provider honours the idempotency key: the same key again returns the first invoice, never a second one */
  readonly idempotent: boolean;
  /** issues the invoice for the order, with our idempotency key (the order id) where the provider takes one */
  issue(input: InvoiceInput, opts: { idempotency_key: string }): Promise<IssuedInvoice>;
  /** the invoice the provider already issued for this order (our reference), null when there is none; absent when it cannot be asked */
  find?(orderId: string): Promise<IssuedInvoice | null>;
  /** S13: a credit note for a refund, with our idempotency key (the refund's id); InvoiceRefused when nothing was issued */
  creditNote?(input: CreditNoteInput, opts: { idempotency_key: string }): Promise<IssuedCreditNote>;
  /** S13: the credit note already issued for this key, null when none; absent when it cannot be asked */
  findCreditNote?(idempotencyKey: string): Promise<IssuedCreditNote | null>;
}

/** A refusal the provider gives before issuing anything (a total that does not add up): the claim is released. */
export class InvoiceRefused extends Error {}

/** Development, tests and preview: a deterministic number per order; idempotent per key within the Worker instance */
export function mockInvoices(): InvoiceProvider {
  const issued = new Map<string, IssuedInvoice>();
  const credits = new Map<string, IssuedCreditNote>();
  return {
    id: 'mock',
    idempotent: true,
    async issue(input, { idempotency_key }) {
      if (!Number.isInteger(input.total_agorot) || input.total_agorot <= 0) throw new InvoiceRefused('invoice_total_invalid');
      const sum = input.lines.reduce((n, l) => n + l.qty * l.unit_price_agorot, 0) + input.shipping_agorot;
      if (sum !== input.total_agorot) throw new InvoiceRefused('invoice_total_mismatch');
      const have = issued.get(idempotency_key);
      if (have) return have;
      const inv = { invoice_id: `MOCK-INV-${input.order_id}`, url: null };
      issued.set(idempotency_key, inv);
      return inv;
    },
    async find(orderId) {
      return issued.get(orderId) ?? null;
    },
    async creditNote(input, { idempotency_key }) {
      const have = credits.get(idempotency_key);
      if (have) return have;
      if (!Number.isInteger(input.amount_agorot) || input.amount_agorot <= 0) throw new InvoiceRefused('credit_amount_invalid');
      if (!input.invoice_id) throw new InvoiceRefused('credit_without_invoice');
      const c = { credit_note_id: `MOCK-CN-${input.refund_id}`, url: null };
      credits.set(idempotency_key, c);
      return c;
    },
    async findCreditNote(key) {
      return credits.get(key) ?? null;
    },
  };
}

export type InvoiceChoice = { ok: true; provider: InvoiceProvider } | { ok: false; reason: string };

/** The provider INVOICE_PROVIDER names (lib/config.ts), or why none runs: production never gets the mock (ת17). */
export function invoiceProvider(env: { ENVIRONMENT?: string; INVOICE_PROVIDER?: string }): InvoiceChoice {
  const c = providerOf(env, 'INVOICE_PROVIDER');
  if (!c.ok) return c;
  if (c.mock) return { ok: true, provider: mockInvoices() };
  // Grow's module or Morning: added with their documentation (docs/ops/deploy-runbook.md, "Invoices")
  return { ok: false, reason: `invoice provider "${c.id}" is not built yet: its documentation is needed` };
}

/** ת18: the statuses a paid order can be in; with paid_at set. Anything else is never invoiced. */
export const INVOICEABLE = ['paid', 'sent_to_supplier', 'supplier_error', 'shipped', 'delivered'] as const;
const PAID_SQL = `paid_at IS NOT NULL AND status IN (${INVOICEABLE.map((s) => `'${s}'`).join(', ')})`;
/** how long a claim stands before a run may treat it as left behind by a crash */
export const INVOICE_LEASE_MS = 10 * 60_000;

export type InvoiceOutcome = 'invoiced' | 'skipped' | 'retry' | 'unresolved';
type Db = { DB: D1Database };
type Claim = { state: 'claimed' | 'issued' | 'unresolved'; claimed_at: string; attempts: number };

/**
 * The job: a paid order's invoice, once. `provider` is the configured one when not given (a test passes its own).
 * `invoiced`: this run issued (or found and recorded) it; `skipped`: nothing to do; `retry`: another run holds the claim,
 * or the provider failed; `unresolved`: a claim without a result that cannot be resolved safely (a person decides).
 */
export async function processInvoiceJob(
  env: Db & { ENVIRONMENT?: string; INVOICE_PROVIDER?: string },
  orderId: string,
  provider?: InvoiceProvider,
  opts: { vatRate?: number; now?: () => number } = {},
): Promise<InvoiceOutcome> {
  const now = opts.now ?? Date.now;
  const iso = () => new Date(now()).toISOString();
  if (!provider) {
    const c = invoiceProvider(env);
    if (!c.ok) {
      refuseLoudly('the invoice job', c.reason, orderId);
      return 'retry';
    }
    provider = c.provider;
  }
  const order = await env.DB.prepare(`SELECT id FROM orders WHERE id = ? AND ${PAID_SQL}`).bind(orderId).first<{ id: string }>();
  if (!order) return 'skipped';

  // the claim, before the provider is called; the paid re-check is in the same statement (ת18)
  const claimedAt = iso();
  const claim = await env.DB.prepare(
    `INSERT INTO invoices (order_id, state, provider, idempotency_key, attempts, claimed_at)
     SELECT id, 'claimed', ?, id, 1, ? FROM orders WHERE id = ? AND ${PAID_SQL}
     ON CONFLICT(order_id) DO NOTHING`,
  )
    .bind(provider.id, claimedAt, orderId)
    .run();
  let ours = claimedAt;
  if (!claim.meta.changes) {
    const row = await env.DB.prepare('SELECT state, claimed_at, attempts FROM invoices WHERE order_id = ?').bind(orderId).first<Claim>();
    if (!row) return 'skipped'; // the order stopped being paid between the two reads
    if (row.state === 'issued') return 'skipped';
    if (row.state === 'unresolved') return 'unresolved';
    // another run holds a fresh claim: it may be calling the provider right now
    if (now() - Date.parse(row.claimed_at) < INVOICE_LEASE_MS) return 'retry';
    // a claim left behind (a crash between the call and the record): ask the provider, never issue blindly
    if (provider.find) {
      const found = await provider.find(orderId);
      if (found) return (await record(env, orderId, provider.id, found, iso())) ? 'invoiced' : 'skipped';
    } else if (!provider.idempotent) {
      const reason = `a claim of ${row.claimed_at} has no result, and ${provider.id} can neither be asked nor deduplicates: a person checks the provider`;
      await env.DB.prepare("UPDATE invoices SET state = 'unresolved', last_error = ? WHERE order_id = ? AND state = 'claimed'").bind(reason, orderId).run();
      await audit(env, provider.id, 'invoice.unresolved', orderId, reason, iso());
      refuseLoudly('the invoice job', reason, orderId);
      return 'unresolved';
    }
    // the provider has none (or will return the first one for the same key): take the claim over, compare-and-swap
    ours = iso();
    const take = await env.DB.prepare(
      "UPDATE invoices SET claimed_at = ?, attempts = attempts + 1, provider = ? WHERE order_id = ? AND state = 'claimed' AND claimed_at = ?",
    )
      .bind(ours, provider.id, orderId, row.claimed_at)
      .run();
    if (!take.meta.changes) return 'retry';
  }

  const head = await env.DB.prepare('SELECT shipping_agorot, total_agorot, customer_id FROM orders WHERE id = ?')
    .bind(orderId)
    .first<{ shipping_agorot: number; total_agorot: number; customer_id: string }>();
  const customer = await env.DB.prepare('SELECT full_name, email, phone FROM customers WHERE id = ?')
    .bind(head!.customer_id)
    .first<{ full_name: string; email: string; phone: string }>();
  const { results } = await env.DB.prepare('SELECT name_he, qty, unit_price_agorot FROM order_items WHERE order_id = ? ORDER BY line')
    .bind(orderId)
    .all<{ name_he: string; qty: number; unit_price_agorot: number }>();
  let inv: IssuedInvoice;
  try {
    inv = await provider.issue(
      {
        order_id: orderId,
        issued_at: iso(),
        customer: customer ?? { full_name: '', email: '', phone: '' },
        lines: results,
        shipping_agorot: head!.shipping_agorot,
        total_agorot: head!.total_agorot,
        vat_rate: opts.vatRate ?? 0.18,
      },
      { idempotency_key: orderId },
    );
  } catch (err) {
    const msg = (err instanceof Error ? err.message : String(err)).slice(0, 500);
    // a refusal issued nothing: the claim goes, so the next run claims afresh; any other failure may have issued one,
    // so the claim stays and the next run asks the provider once the lease is over
    if (err instanceof InvoiceRefused)
      await env.DB.prepare("DELETE FROM invoices WHERE order_id = ? AND state = 'claimed' AND claimed_at = ?").bind(orderId, ours).run();
    else await env.DB.prepare('UPDATE invoices SET last_error = ? WHERE order_id = ? AND claimed_at = ?').bind(msg, orderId, ours).run();
    refuseLoudly('the invoice provider', msg, orderId);
    return 'retry';
  }
  return (await record(env, orderId, provider.id, inv, iso())) ? 'invoiced' : 'skipped';
}

/** The result, in one batch: the claim becomes the invoice, the order carries its number, the audit log says so. */
async function record(env: Db, orderId: string, providerId: string, inv: IssuedInvoice, at: string): Promise<boolean> {
  const [done] = await env.DB.batch([
    env.DB.prepare(
      "UPDATE invoices SET state = 'issued', provider = ?, provider_invoice_id = ?, url = ?, issued_at = ?, last_error = NULL WHERE order_id = ? AND state = 'claimed'",
    ).bind(providerId, inv.invoice_id, inv.url, at, orderId),
    env.DB.prepare(
      "UPDATE orders SET invoice_provider = ?, invoice_number = ?, invoice_url = ?, updated_at = ? WHERE id = ? AND EXISTS (SELECT 1 FROM invoices WHERE order_id = ? AND state = 'issued' AND provider_invoice_id = ?)",
    ).bind(providerId, inv.invoice_id, inv.url, at, orderId, orderId, inv.invoice_id),
    env.DB.prepare(
      "INSERT INTO audit_log (at, actor, action, subject, detail) SELECT ?, ?, 'order.invoiced', ?, ? WHERE NOT EXISTS (SELECT 1 FROM audit_log WHERE action = 'order.invoiced' AND subject = ?)",
    ).bind(at, `invoice:${providerId}`, orderId, JSON.stringify(inv), orderId),
  ]);
  return !!done?.meta.changes;
}

async function audit(env: Db, providerId: string, action: string, orderId: string, detail: string, at: string): Promise<void> {
  await auditAs(env, `invoice:${providerId}`, action, orderId, detail, at);
}
async function auditAs(env: Db, actor: string, action: string, orderId: string, detail: string, at: string): Promise<void> {
  await env.DB.prepare('INSERT INTO audit_log (at, actor, action, subject, detail) VALUES (?, ?, ?, ?, ?)').bind(at, actor, action, orderId, detail).run();
}

/**
 * S13 (2.5): the credit note of a refund, once, the same way as the invoice (ת16): the refund row is claimed before the
 * provider is called, the refund's id is the idempotency key, a claim left behind is resolved by asking the provider,
 * and a provider that can neither be asked nor deduplicates leaves it `unresolved` for a person.
 * - **No invoice, no credit note:** an order canceled before its invoice was issued (S12 question 1) needs none
 *   (`not_needed`). An invoice still on its way: retried later.
 * - `credited`: issued (or found) and recorded; `skipped`: nothing to do; `retry`: later; `unresolved`: a person.
 */
export async function processCreditNoteJob(
  env: Db & { ENVIRONMENT?: string; INVOICE_PROVIDER?: string },
  refundId: string,
  provider?: InvoiceProvider,
  opts: { vatRate?: number; now?: () => number } = {},
): Promise<'credited' | 'skipped' | 'retry' | 'unresolved'> {
  const now = opts.now ?? Date.now;
  const iso = () => new Date(now()).toISOString();
  const r = await env.DB.prepare('SELECT id, order_id, amount_agorot, reason, state, credit_state, credit_claimed_at FROM refunds WHERE id = ?')
    .bind(refundId)
    .first<{ id: string; order_id: string; amount_agorot: number; reason: string; state: string; credit_state: string; credit_claimed_at: string | null }>();
  if (!r || r.state !== 'refunded' || r.credit_state === 'issued' || r.credit_state === 'not_needed') return 'skipped';
  if (r.credit_state === 'unresolved') return 'unresolved';
  const inv = await env.DB.prepare('SELECT state, provider_invoice_id FROM invoices WHERE order_id = ?')
    .bind(r.order_id)
    .first<{ state: string; provider_invoice_id: string | null }>();
  if (!inv) {
    const invoiceable = await env.DB.prepare(`SELECT 1 AS y FROM orders WHERE id = ? AND ${PAID_SQL}`).bind(r.order_id).first();
    if (invoiceable) return 'retry'; // its invoice job has not run yet
    await env.DB.prepare("UPDATE refunds SET credit_state = 'not_needed' WHERE id = ? AND credit_state = 'pending'").bind(refundId).run();
    await auditAs(env, 'system', 'refund.credit_not_needed', r.order_id, JSON.stringify({ refund: refundId, why: 'no invoice was issued' }), iso());
    return 'skipped';
  }
  if (inv.state !== 'issued' || !inv.provider_invoice_id) return 'retry';
  if (!provider) {
    const c = invoiceProvider(env);
    if (!c.ok) {
      refuseLoudly('the credit note job', c.reason, r.order_id);
      return 'retry';
    }
    provider = c.provider;
  }
  if (!provider.creditNote) {
    refuseLoudly('the credit note job', `${provider.id} has no credit note call`, r.order_id);
    return 'retry';
  }
  const at = iso();
  const claim = await env.DB.prepare("UPDATE refunds SET credit_state = 'claimed', credit_claimed_at = ? WHERE id = ? AND credit_state = 'pending'")
    .bind(at, refundId)
    .run();
  let ours = at;
  if (!claim.meta.changes) {
    // claimed by another run: fresh, it may be calling the provider; stale, a crash between the call and the record
    if (r.credit_state !== 'claimed' || !r.credit_claimed_at || now() - Date.parse(r.credit_claimed_at) < INVOICE_LEASE_MS) return 'retry';
    if (provider.findCreditNote) {
      const found = await provider.findCreditNote(refundId);
      if (found) return (await recordCredit(env, r.order_id, refundId, provider.id, found, iso())) ? 'credited' : 'skipped';
    } else if (!provider.idempotent) {
      const reason = `a credit note claim of ${r.credit_claimed_at} has no result, and ${provider.id} can neither be asked nor deduplicates: a person checks the provider`;
      await env.DB.prepare("UPDATE refunds SET credit_state = 'unresolved', credit_error = ? WHERE id = ? AND credit_state = 'claimed'")
        .bind(reason, refundId)
        .run();
      await auditAs(env, `invoice:${provider.id}`, 'refund.credit_unresolved', r.order_id, reason, iso());
      refuseLoudly('the credit note job', reason, r.order_id);
      return 'unresolved';
    }
    ours = iso();
    const take = await env.DB.prepare("UPDATE refunds SET credit_claimed_at = ? WHERE id = ? AND credit_state = 'claimed' AND credit_claimed_at = ?")
      .bind(ours, refundId, r.credit_claimed_at)
      .run();
    if (!take.meta.changes) return 'retry';
  }
  const head = await env.DB.prepare('SELECT o.customer_id, c.full_name, c.email, c.phone FROM orders o JOIN customers c ON c.id = o.customer_id WHERE o.id = ?')
    .bind(r.order_id)
    .first<{ full_name: string; email: string; phone: string }>();
  let cn: IssuedCreditNote;
  try {
    cn = await provider.creditNote(
      {
        order_id: r.order_id,
        refund_id: refundId,
        invoice_id: inv.provider_invoice_id,
        amount_agorot: r.amount_agorot,
        issued_at: iso(),
        customer: { full_name: head?.full_name ?? '', email: head?.email ?? '', phone: head?.phone ?? '' },
        reason: r.reason,
        vat_rate: opts.vatRate ?? 0.18,
      },
      { idempotency_key: refundId },
    );
  } catch (err) {
    const msg = (err instanceof Error ? err.message : String(err)).slice(0, 500);
    if (err instanceof InvoiceRefused)
      await env.DB.prepare("UPDATE refunds SET credit_state = 'pending', credit_claimed_at = NULL, credit_error = ? WHERE id = ? AND credit_claimed_at = ?")
        .bind(msg, refundId, ours)
        .run();
    else await env.DB.prepare('UPDATE refunds SET credit_error = ? WHERE id = ? AND credit_claimed_at = ?').bind(msg, refundId, ours).run();
    refuseLoudly('the credit note provider', msg, r.order_id);
    return 'retry';
  }
  return (await recordCredit(env, r.order_id, refundId, provider.id, cn, iso())) ? 'credited' : 'skipped';
}

async function recordCredit(env: Db, orderId: string, refundId: string, providerId: string, cn: IssuedCreditNote, at: string): Promise<boolean> {
  const [done] = await env.DB.batch([
    env.DB.prepare(
      "UPDATE refunds SET credit_state = 'issued', credit_note_id = ?, credit_issued_at = ?, credit_error = NULL WHERE id = ? AND credit_state = 'claimed'",
    ).bind(cn.credit_note_id, at, refundId),
    env.DB.prepare(
      "INSERT INTO audit_log (at, actor, action, subject, detail) SELECT ?, ?, 'refund.credit_note', ?, ? WHERE EXISTS (SELECT 1 FROM refunds WHERE id = ? AND credit_state = 'issued' AND credit_note_id = ? AND credit_issued_at = ?)",
    ).bind(at, `invoice:${providerId}`, orderId, JSON.stringify({ refund: refundId, credit_note: cn.credit_note_id }), refundId, cn.credit_note_id, at),
  ]);
  return !!done?.meta.changes;
}
