import type { Env } from '../../env';
import { HttpError } from '../http';
import { mockProvider } from './mock';
import type { PaymentProvider } from './types';

export function paymentProvider(env: Env, origin: string, id = env.PAYMENT_PROVIDER): PaymentProvider {
  if (id === 'mock') {
    if (env.ENVIRONMENT === 'production') throw new HttpError(503, 'mock_payments_disabled_in_production');
    if (!env.PAYMENT_WEBHOOK_SECRET) throw new HttpError(503, 'payment_not_configured');
    return mockProvider(env.PAYMENT_WEBHOOK_SECRET, origin);
  }
  // Grow / Cardcom / PayPlus adapters are added after the user picks a provider (docs/architecture.md).
  throw new HttpError(503, 'payment_provider_not_configured', 'התשלום עוד לא מחובר.');
}
