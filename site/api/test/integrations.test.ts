/**
 * S9: the contracts every real provider must meet, run against what is built (the mocks), and the skeletons that wait
 * for keys and documentation: they refuse loudly and never call out with a guessed request.
 */
import { describe, expect, it } from 'vitest';
import { mockProvider, signMockEvent, MOCK_SIGNATURE_HEADER } from '../src/lib/payments/mock';
import { growProvider } from '../src/lib/payments/grow';
import type { PaymentProvider } from '../src/lib/payments/types';
import { mockInvoices } from '../src/lib/invoices';
import { cjSupplier, CJ_BASE } from '../src/lib/suppliers';

const SECRET = 'test-secret-not-real';
const NOW = 1_800_000_000;

/** the payment contract: a hosted page for a session, and a webhook believed only when it verifies */
async function paymentContract(p: PaymentProvider, signed: (body: object) => Promise<{ headers: Headers; body: string }>) {
  const s = await p.createSession({
    order_id: '1234567890',
    amount_agorot: 25800,
    description_he: 'הזמנה',
    customer: { full_name: 'נועה כהן', email: 'noa@example.com', phone: '050-1234567' },
    return_url: 'https://example.co.il/order/1234567890/',
    cancel_url: 'https://example.co.il/checkout/?canceled=1',
    webhook_url: 'https://example.co.il/api/payments/webhook',
  });
  expect(s.session_id).toBeTruthy();
  expect(s.redirect_url).toMatch(/^https?:\/\//);
  const event = { id: 'evt_contract_1', type: 'payment.succeeded' as const, session_id: s.session_id, amount_agorot: 25800 };
  const ok = await signed(event);
  const v = await p.verifyWebhook(ok.headers, ok.body, NOW);
  expect(v.ok && v.event).toEqual(event);
  // a body changed after signing, or an old signature, is refused
  expect((await p.verifyWebhook(ok.headers, ok.body.replace('25800', '100'), NOW)).ok).toBe(false);
  expect((await p.verifyWebhook(ok.headers, ok.body, NOW + 3600)).ok).toBe(false);
}

describe('payments (W1)', () => {
  it('the mock meets the contract every adapter must meet', async () => {
    await paymentContract(mockProvider(SECRET, 'https://example.co.il'), async (e) => {
      const { body, signature } = await signMockEvent(SECRET, e as never, NOW);
      return { headers: new Headers({ [MOCK_SIGNATURE_HEADER]: signature }), body };
    });
  });

  it('Grow waits for its keys and its documentation: it refuses, and believes no webhook', async () => {
    for (const g of [growProvider({}), growProvider({ userId: 'u', pageCode: 'p', apiKey: 'k' })]) {
      await expect(g.createSession({} as never)).rejects.toMatchObject({ status: 503 });
      expect((await g.verifyWebhook(new Headers(), '{}', NOW)).ok).toBe(false);
    }
  });
});

describe('the tax invoice (W2)', () => {
  const input = {
    order_id: '1234567890',
    issued_at: '2026-11-10T10:00:00Z',
    customer: { full_name: 'נועה כהן', email: 'noa@example.com', phone: '050-1234567' },
    lines: [{ name_he: 'אגרטל', qty: 1, unit_price_agorot: 22900 }],
    shipping_agorot: 2900,
    total_agorot: 25800,
    vat_rate: 0.18,
  };
  it('issues one invoice per order, again the same one, and refuses a total that does not add up', async () => {
    const p = mockInvoices();
    const a = await p.issue(input);
    expect(a.invoice_id).toBeTruthy();
    expect(await p.issue(input)).toEqual(a);
    await expect(p.issue({ ...input, order_id: '2', total_agorot: 1 })).rejects.toThrow(/mismatch/);
  });
});

describe('the supplier (CJ)', () => {
  it('asks for its token with the documented call, and never sends an order with a guessed one', async () => {
    const calls: string[] = [];
    const fetcher = async (url: string, init?: RequestInit) => {
      calls.push(`${init?.method} ${url} ${String(init?.body)}`);
      return new Response(JSON.stringify({ result: true, data: { accessToken: 'tok' } }), { status: 200 });
    };
    const cj = cjSupplier('key-not-real', fetcher);
    expect(await cj.token()).toBe('tok');
    expect(await cj.token()).toBe('tok'); // cached
    expect(calls).toEqual([`POST ${CJ_BASE}/authentication/getAccessToken {"apiKey":"key-not-real"}`]);
    const order = {
      order_id: '1',
      lines: [{ supplier_sku: 'CJ1', product_id: 'p', qty: 1 }],
      ship_to: { full_name: 'א', phone: '1', email: 'e', city: 'c', street: 's', house: '1', apartment: '', zip: '' },
      shipping_method: 'economy' as const,
    };
    await expect(cj.submitOrder(order)).rejects.toThrow('cj_order_api_docs_needed');
    await expect(cj.submitOrder({ ...order, lines: [{ supplier_sku: null, product_id: 'p', qty: 1 }] })).rejects.toThrow('cj_line_without_sku');
    await expect(cjSupplier(undefined, fetcher).submitOrder(order)).rejects.toThrow('CJ_API_KEY');
    expect(calls).toHaveLength(1);
  });
});
