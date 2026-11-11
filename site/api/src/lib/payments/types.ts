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

/** S13 (2.5): a refund of a paid order, full or partial, through the provider that took the payment. */
export type RefundInput = {
  order_id: string;
  /** the provider's reference of the payment (our payment session) */
  payment_ref: string;
  amount_agorot: number;
  /** what the order paid, and what was refunded before this one: a provider refuses more than what is left */
  paid_agorot: number;
  refunded_before_agorot: number;
  reason: string;
};
export type IssuedRefund = { refund_id: string; raw?: unknown };

/** A refusal the provider gives before anything moved (more than what is left, a payment it does not know). */
export class RefundRefused extends Error {}

export interface PaymentProvider {
  readonly id: string;
  createSession(input: CreateSessionInput): Promise<{ session_id: string; redirect_url: string }>;
  verifyWebhook(headers: Headers, rawBody: string, nowSec: number): Promise<VerifiedWebhook>;
  /**
   * S13: the provider honours the idempotency key on refunds: the same key again returns the first refund, never a
   * second one. A provider that does not cannot be retried blindly after a failure that may have refunded.
   */
  readonly refundsIdempotent?: boolean;
  /** S13: refunds the amount, with our idempotency key (the refund's id); throws RefundRefused when nothing moved */
  refund?(input: RefundInput, opts: { idempotency_key: string; signal?: AbortSignal }): Promise<IssuedRefund>;
  /** S13: the refund the provider already made for this key, null when none; absent when it cannot be asked */
  findRefund?(idempotencyKey: string): Promise<IssuedRefund | null>;
}
