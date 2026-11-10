import type { Env } from '../../env';
import { HttpError } from '../http';
import { growProvider } from './grow';
import { mockProvider } from './mock';
import type { PaymentProvider } from './types';

export function paymentProvider(env: Env, origin: string, id = env.PAYMENT_PROVIDER): PaymentProvider {
  if (id === 'mock') {
    if (env.ENVIRONMENT === 'production') throw new HttpError(503, 'mock_payments_disabled_in_production');
    if (!env.PAYMENT_WEBHOOK_SECRET) throw new HttpError(503, 'payment_not_configured');
    return mockProvider(env.PAYMENT_WEBHOOK_SECRET, origin);
  }
  // W1: Grow, behind config; it refuses until its keys and its documentation are in (lib/payments/grow.ts)
  if (id === 'grow')
    return growProvider({ userId: env.GROW_USER_ID, pageCode: env.GROW_PAGE_CODE, apiKey: env.GROW_API_KEY, docsConfirmed: env.GROW_DOCS_CONFIRMED === '1' });
  throw new HttpError(503, 'payment_provider_not_configured', 'התשלום עוד לא מחובר.');
}
