import type { Env } from '../../env';
import { providerOf } from '../config';
import { HttpError } from '../http';
import { growProvider } from './grow';
import { mockProvider } from './mock';
import type { PaymentProvider } from './types';

/**
 * The payment provider PAYMENT_PROVIDER names, exactly (lib/config.ts, S12 ת17): the mock outside production only.
 * `id` is the provider a webhook's path names: S12 ת20, only the configured provider's webhook is heard (another one,
 * the mock's too, is 404), so a mock signature can never pay an order once a real provider is configured.
 */
export function paymentProvider(env: Env, origin: string, id = env.PAYMENT_PROVIDER): PaymentProvider {
  if (id !== env.PAYMENT_PROVIDER) throw new HttpError(404, 'not_found');
  const c = providerOf(env, 'PAYMENT_PROVIDER');
  if (!c.ok) {
    if (id === 'mock') throw new HttpError(503, 'mock_payments_disabled_in_production');
    throw new HttpError(503, 'payment_provider_not_configured', 'התשלום עוד לא מחובר.');
  }
  if (c.mock) {
    if (!env.PAYMENT_WEBHOOK_SECRET) throw new HttpError(503, 'payment_not_configured');
    return mockProvider(env.PAYMENT_WEBHOOK_SECRET, origin);
  }
  // W1: Grow, behind config; it refuses until its keys and its documentation are in (lib/payments/grow.ts)
  if (id === 'grow')
    return growProvider({ userId: env.GROW_USER_ID, pageCode: env.GROW_PAGE_CODE, apiKey: env.GROW_API_KEY, docsConfirmed: env.GROW_DOCS_CONFIRMED === '1' });
  throw new HttpError(503, 'payment_provider_not_configured', 'התשלום עוד לא מחובר.');
}
