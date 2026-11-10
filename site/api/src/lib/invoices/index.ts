/**
 * S9: the tax invoice, a job after "paid" (W2: the acquirer's invoicing module, else Morning; docs/architecture.md §8).
 * The provider is chosen by INVOICE_PROVIDER: `mock` records the invoice in the order's events; a real provider is
 * added when its documentation is in the repo (none is, so none is guessed). Idempotent per order: the job may run
 * twice (a queue retry) and issues one invoice.
 */
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

export interface InvoiceProvider {
  readonly id: string;
  /** issues the invoice for the order; the same order again returns the first invoice */
  issue(input: InvoiceInput): Promise<IssuedInvoice>;
}

/** Development, tests and preview: a deterministic number per order, kept in memory per Worker instance */
export function mockInvoices(): InvoiceProvider {
  const issued = new Map<string, IssuedInvoice>();
  return {
    id: 'mock',
    async issue(input) {
      if (!Number.isInteger(input.total_agorot) || input.total_agorot <= 0) throw new Error('invoice_total_invalid');
      const sum = input.lines.reduce((n, l) => n + l.qty * l.unit_price_agorot, 0) + input.shipping_agorot;
      if (sum !== input.total_agorot) throw new Error('invoice_total_mismatch');
      const have = issued.get(input.order_id);
      if (have) return have;
      const inv = { invoice_id: `MOCK-INV-${input.order_id}`, url: null };
      issued.set(input.order_id, inv);
      return inv;
    },
  };
}

export function invoiceProvider(id: string | undefined): InvoiceProvider {
  if (!id || id === 'mock') return mockInvoices();
  // Grow's module or Morning: added with their documentation (docs/ops/deploy-runbook.md, "Invoices")
  throw new Error(`invoice provider "${id}" is not built yet: its documentation is needed`);
}

/**
 * The job: a paid order's invoice, once. The order, its lines and its customer from D1; the result in the audit log
 * (`order.invoiced`); an order already invoiced, or not paid, is skipped.
 */
export async function processInvoiceJob(
  env: { DB: D1Database; INVOICE_PROVIDER?: string },
  orderId: string,
  provider: InvoiceProvider = invoiceProvider(env.INVOICE_PROVIDER),
  vatRate = 0.18,
): Promise<'invoiced' | 'skipped'> {
  const order = await env.DB.prepare('SELECT id, status, created_at, shipping_agorot, total_agorot, customer_id FROM orders WHERE id = ?')
    .bind(orderId)
    .first<{ id: string; status: string; created_at: string; shipping_agorot: number; total_agorot: number; customer_id: string }>();
  if (!order || order.status === 'pending_payment' || order.status === 'payment_failed') return 'skipped';
  const done = await env.DB.prepare("SELECT 1 AS x FROM audit_log WHERE action = 'order.invoiced' AND subject = ?").bind(orderId).first<{ x: number }>();
  if (done) return 'skipped';
  const customer = await env.DB.prepare('SELECT full_name, email, phone FROM customers WHERE id = ?')
    .bind(order.customer_id)
    .first<{ full_name: string; email: string; phone: string }>();
  const { results } = await env.DB.prepare('SELECT name_he, qty, unit_price_agorot FROM order_items WHERE order_id = ? ORDER BY line')
    .bind(orderId)
    .all<{ name_he: string; qty: number; unit_price_agorot: number }>();
  const inv = await provider.issue({
    order_id: order.id,
    issued_at: new Date().toISOString(),
    customer: customer ?? { full_name: '', email: '', phone: '' },
    lines: results,
    shipping_agorot: order.shipping_agorot,
    total_agorot: order.total_agorot,
    vat_rate: vatRate,
  });
  await env.DB.prepare('INSERT INTO audit_log (at, actor, action, subject, detail) VALUES (?, ?, ?, ?, ?)')
    .bind(new Date().toISOString(), `invoice:${provider.id}`, 'order.invoiced', orderId, JSON.stringify(inv))
    .run();
  return 'invoiced';
}
