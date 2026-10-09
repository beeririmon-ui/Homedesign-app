import { z } from 'zod';
import { randomToken, signWebhook, verifyWebhook } from '@hd/shared';
import type { PaymentProvider, PaymentEvent } from './types';

const MockEventSchema = z.object({
  id: z.string().min(8).max(80),
  type: z.enum(['payment.succeeded', 'payment.failed']),
  session_id: z.string().min(8).max(80),
  amount_agorot: z.number().int().nonnegative(),
});

export const MOCK_SIGNATURE_HEADER = 'x-mock-signature';

/** Hosted-page simulator: /mock-pay/<session> on this Worker. Same signature scheme a real adapter must verify. */
export function mockProvider(secret: string, origin: string): PaymentProvider {
  return {
    id: 'mock',
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
