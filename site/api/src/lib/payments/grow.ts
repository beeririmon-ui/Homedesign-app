/**
 * Grow (Meshulam), W1 (2026-10-10, the owner's first acquirer for a test): the adapter's skeleton, ready for keys.
 *
 * No Grow documentation is in the repository, so no endpoint, field name or signature scheme is guessed here (S9).
 * The adapter is wired behind PAYMENT_PROVIDER=grow and refuses loudly until GROW_DOCS_CONFIRMED is set by the person
 * who brings the documentation in. What the implementation needs, exactly (docs/ops/deploy-runbook.md, "Grow"):
 *   1. the "create payment process" call: its URL (sandbox and production), method, auth, and the request fields for
 *      the amount in agorot or shekels, the description, the customer (name, email, phone), the success, cancel and
 *      notify URLs, our order id as a reference field, and the response field with the hosted page's URL and its id;
 *   2. the server-to-server notification ("webhook"): its body format, the fields for the transaction id, status,
 *      amount and our reference, and how it is authenticated (a signature header, a shared secret, or a call back to
 *      Grow to approve the transaction), with a sample payload for the contract test;
 *   3. refunds through the API (if offered): the call and its fields;
 *   4. the account values: user id, page code, API key (wrangler secrets, never in the repo).
 */
import { HttpError } from '../http';
import type { PaymentProvider } from './types';

export type GrowConfig = { userId?: string; pageCode?: string; apiKey?: string; docsConfirmed?: boolean };

export function growProvider(cfg: GrowConfig): PaymentProvider {
  const missing = [!cfg.userId && 'GROW_USER_ID', !cfg.pageCode && 'GROW_PAGE_CODE', !cfg.apiKey && 'GROW_API_KEY'].filter(Boolean);
  const refuse = (): never => {
    if (missing.length) throw new HttpError(503, 'payment_not_configured', 'התשלום עוד לא מחובר.');
    // the keys are there, the documentation is not: never a guessed call with a customer's money
    throw new HttpError(503, 'payment_provider_docs_needed', 'התשלום עוד לא מחובר.');
  };
  return {
    id: 'grow',
    async createSession() {
      return refuse();
    },
    async verifyWebhook() {
      // a webhook that cannot be verified is refused, never trusted
      return { ok: false, reason: missing.length ? 'grow_not_configured' : 'grow_docs_needed' };
    },
    // S13 (2.5): refunds through Grow's API are item 3 of the list above; never a guessed call with a customer's money
    async refund() {
      return refuse();
    },
  };
}
