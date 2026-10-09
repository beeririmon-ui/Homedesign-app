/**
 * Payment provider adapter. The site never sees card data: the buyer pays on the provider's hosted page
 * (PCI scope stays with the provider), and the order becomes "paid" only through a verified webhook.
 * Candidates (not verified, decision open): Grow (Meshulam), Cardcom, PayPlus. Each gets an adapter
 * with the same interface; `mock` is for development, tests and the artifact preview.
 */
export type CreateSessionInput = {
  order_id: string;
  amount_agorot: number;
  description_he: string;
  customer: { full_name: string; email: string; phone: string };
  return_url: string;
  cancel_url: string;
  webhook_url: string;
};

export type PaymentEvent = {
  id: string; // provider event id (idempotency key)
  type: 'payment.succeeded' | 'payment.failed';
  session_id: string;
  amount_agorot: number;
};

export type VerifiedWebhook = { ok: true; event: PaymentEvent } | { ok: false; reason: string };

export interface PaymentProvider {
  readonly id: string;
  createSession(input: CreateSessionInput): Promise<{ session_id: string; redirect_url: string }>;
  verifyWebhook(headers: Headers, rawBody: string, nowSec: number): Promise<VerifiedWebhook>;
}
