import type { Env } from '../../env';
import type { SupplierClient } from './types';

/** Development and preview: records the order without calling a supplier. */
const mockSupplier: SupplierClient = {
  id: 'mock',
  async submitOrder(input) {
    return { supplier_order_id: `MOCK-${input.order_id}`, raw: { mocked: true, lines: input.lines.length } };
  },
};

/**
 * CJ Dropshipping (API 2.0). Not implemented in this phase: needs CJ_API_KEY (wrangler secret), the access-token
 * flow, logistic name mapping for economy/express, and a sandbox order test. Endpoints and terms are "לא אומת".
 */
const cjSupplier = (apiKey: string | undefined): SupplierClient => ({
  id: 'cj',
  async submitOrder() {
    if (!apiKey) throw new Error('CJ_API_KEY is not set');
    throw new Error('CJ adapter not implemented yet');
  },
});

export function supplierClient(env: Env): SupplierClient {
  return env.SUPPLIER_PROVIDER === 'cj' ? cjSupplier(env.CJ_API_KEY) : mockSupplier;
}
