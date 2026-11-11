import { z } from 'zod';
import { randomToken, signWebhook, verifyWebhook } from '@hd/shared';
import { RefundRefused, type IssuedRefund, type PaymentProvider, type PaymentEvent } from './types';

const MockEventSchema = z.object({
  id: z.string().min(8).max(80),
  type: z.enum(['payment.succeeded', 'payment.failed']),
  session_id: z.string().min(8).max(80),
  amount_agorot: z.number().int().nonnegative(),
});

export const MOCK_SIGNATURE_HEADER = 'x-mock-signature';

/**
 * S13: the mock's refunds, per idempotency key, for the life of the Worker instance (like the mock invoices). It refuses
 * what a real acquirer refuses: a refund above what is left of the payment.
 */
const mockRefunds = new Map<string, IssuedRefund>();

/** Hosted-page simulator: /mock-pay/<session> on this Worker. Same signature scheme a real adapter must verify. */
export function mockProvider(secret: string, origin: string): PaymentProvider {
  return {
    id: 'mock',
    refundsIdempotent: true,
    async refund(input, { idempotency_key }) {
      const have = mockRefunds.get(idempotency_key);
      if (have) return have;
      if (!Number.isInteger(input.amount_agorot) || input.amount_agorot <= 0) throw new RefundRefused('refund_amount_invalid');
      if (input.refunded_before_agorot + input.amount_agorot > input.paid_agorot) throw new RefundRefused('refund_exceeds_payment');
      const r = { refund_id: `MOCK-RF-${input.order_id}-${mockRefunds.size + 1}`, raw: { mocked: true } };
      mockRefunds.set(idempotency_key, r);
      return r;
    },
    async findRefund(key) {
      return mockRefunds.get(key) ?? null;
    },
    async createSession() {
      const session_id = `ms_${randomToken(18)}`;
      return { session_id, redirect_url: `${origin}/mock-pay/${session_id}` };
    },
    async verifyWebhook(headers, rawBody, nowSec) {
      const v = await verifyWebhook(secret, headers.get(MOCK_SIGNATURE_HEADER), rawBody, nowSec);
      if (!v.ok) return { ok: false, reason: v.reason };
      let json: unknown;
      try {
        json = JSON.parse(rawBody);
      } catch {
        return { ok: false, reason: 'json' };
      }
      const parsed = MockEventSchema.safeParse(json);
      return parsed.success ? { ok: true, event: parsed.data } : { ok: false, reason: 'shape' };
    },
  };
}

export async function signMockEvent(secret: string, event: PaymentEvent, nowSec: number) {
  const body = JSON.stringify(event);
  return { body, signature: await signWebhook(secret, body, nowSec) };
}
