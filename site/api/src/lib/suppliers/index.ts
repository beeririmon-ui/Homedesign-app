import type { Env } from '../../env';
import { providerOf } from '../config';
import { SupplierRefused, type SupplierClient, type SupplierOrderInput } from './types';
import { CodedError } from '../errors';

/**
 * Development and preview: records the order without calling a supplier.
 * S13: a cancellation request is `requested` (the supplier answers later, as a real one does). The mock never reports
 * on its own (`tracking` is null): in development and preview the admin plays the supplier's answers (the order page's
 * "ספק מדומה" panel, lib/shipments.ts `applySupplierUpdate`), so every state can be seen without a supplier.
 */
const mockSupplier: SupplierClient = {
  id: 'mock',
  async submitOrder(input) {
    return { supplier_order_id: `MOCK-${input.order_id}`, raw: { mocked: true, lines: input.lines.length } };
  },
  async cancelOrder() {
    return { outcome: 'requested', raw: { mocked: true } };
  },
  async tracking() {
    return null;
  },
};

/**
 * CJ Dropshipping (API 2.0), S9: the order adapter's skeleton, ready for a key (CJ_API_KEY, a wrangler secret).
 * What is known from the repo's own working client (scripts/cj.py, used by sourcing): the base URL, the token call
 * (POST /authentication/getAccessToken with {apiKey}) and the CJ-Access-Token header; responses carry {result, code,
 * message, data}. The order-creation call is NOT in the repo, so it is not guessed: `submitOrder` refuses with what
 * is needed (docs/ops/deploy-runbook.md, "CJ"): the create-order call and its fields (our order number, the ship-to
 * fields for Israel, each line's vid and quantity, the logistic name for economy and express), its response (CJ's
 * order id), the payment step (balance or manual), and a sandbox order to run the contract against.
 */
export const CJ_BASE = 'https://developers.cjdropshipping.com/api2.0/v1';
type Fetch = (url: string, init?: RequestInit) => Promise<Response>;

export function cjSupplier(apiKey: string | undefined, fetcher: Fetch = (u, i) => fetch(u, i)): SupplierClient & { token(): Promise<string> } {
  let cached: { token: string; until: number } | null = null;
  const self = {
    id: 'cj',
    /** the access token (the documented call our sourcing client uses), cached for its life */
    async token(): Promise<string> {
      if (!apiKey) throw new CodedError('cj_api_key_missing', 'CJ_API_KEY is not set');
      if (cached && cached.until > Date.now()) return cached.token;
      const r = await fetcher(`${CJ_BASE}/authentication/getAccessToken`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ apiKey }),
      });
      const d = (await r.json().catch(() => ({}))) as { result?: boolean; message?: string; data?: { accessToken?: string } };
      if (!r.ok || !d.result || !d.data?.accessToken) throw new CodedError('cj_token_failed', String(d.message ?? r.status));
      cached = { token: d.data.accessToken, until: Date.now() + 12 * 3600_000 };
      return cached.token;
    },
    async submitOrder(input: SupplierOrderInput) {
      // S16 (ת35): each of these refuses before any call: nothing reaches CJ
      if (!apiKey) throw new SupplierRefused('cj_api_key_missing', 'CJ_API_KEY is not set');
      const noSku = input.lines.filter((l) => !l.supplier_sku);
      if (noSku.length) throw new SupplierRefused('cj_line_without_sku', `cj_line_without_sku: ${noSku.map((l) => l.product_id).join(', ')}`);
      // the create-order call is not in the repo's documentation: never guessed with a paid order
      throw new SupplierRefused('cj_order_api_docs_needed');
    },
    // S13: the cancel and tracking calls are not in the repo's documentation either: absent, so the admin says that a
    // person cancels at the supplier, and the cron asks nothing (docs/ops/deploy-runbook.md, "CJ"). S16 (ת35): nor is a
    // query by our order number (`findOrder`): a shipment that may be at CJ is checked there by a person.
  };
  return self;
}

export type SupplierChoice = { ok: true; client: SupplierClient } | { ok: false; reason: string };

/**
 * The supplier SUPPLIER_PROVIDER names, exactly (lib/config.ts, S12 ת17): `cj`, or `mock` outside production only. A
 * missing value, `mock` in production or a typo (`CJ`) runs nothing: the job fails loudly and is retried, and the order
 * is never marked as sent to the supplier.
 */
export function supplierClient(env: Pick<Env, 'ENVIRONMENT' | 'SUPPLIER_PROVIDER' | 'CJ_API_KEY'>): SupplierChoice {
  const c = providerOf(env, 'SUPPLIER_PROVIDER');
  if (!c.ok) return c;
  return { ok: true, client: c.mock ? mockSupplier : cjSupplier(env.CJ_API_KEY) };
}
