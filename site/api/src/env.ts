export type RateLimiter = { limit(options: { key: string }): Promise<{ success: boolean }> };

export type SupplierJob =
  | { kind: 'submit-order'; order_id: string }
  | { kind: 'issue-invoice'; order_id: string }
  /** S13 (2.5): the credit note of a refund, through the invoice provider, once per refund */
  | { kind: 'credit-note'; order_id: string; refund_id: string }
  /** S13 (6.3): the new-order alert (NOTIFY_PROVIDER), once per order */
  | { kind: 'notify-order'; order_id: string };

/** Bindings and variables (wrangler.jsonc) plus secrets (wrangler secret / .dev.vars). */
export type Env = {
  DB: D1Database;
  ASSETS?: Fetcher;
  SUPPLIER_QUEUE: Queue<SupplierJob>;
  RL_WRITE?: RateLimiter;
  RL_CHECKOUT?: RateLimiter;
  ENVIRONMENT: 'development' | 'preview' | 'production' | 'preview-local' | 'test';
  PAYMENT_PROVIDER: string;
  SUPPLIER_PROVIDER: string;
  ACCESS_TEAM_DOMAIN: string;
  ACCESS_AUD: string;
  // secrets
  PAYMENT_WEBHOOK_SECRET?: string;
  PAYMENT_API_KEY?: string;
  CJ_API_KEY?: string;
  INVOICE_API_KEY?: string;
  /** S9: mock | grow | morning (only mock is built: the others need their documentation) */
  INVOICE_PROVIDER?: string;
  /** S9, Grow (W1): wrangler secrets, never in the repo */
  GROW_USER_ID?: string;
  GROW_PAGE_CODE?: string;
  GROW_API_KEY?: string;
  /** set to "1" only when Grow's documentation is in the repo and the adapter is finished */
  GROW_DOCS_CONFIRMED?: string;
  ADMIN_DEV_BYPASS?: string;
  /**
   * S13: local runs only (development, test, preview-local): a request to /admin or /api/admin carrying this value in
   * `x-hd-dev-admin` is let in as `dev-token`. The e2e suite reads it from api/.dev.vars. Ignored in preview and production.
   */
  ADMIN_DEV_TOKEN?: string;
  /** S13 (6.3): the new-order alert's provider; `mock` (a log row) outside production; none is built yet */
  NOTIFY_PROVIDER?: string;
};

export type AppEnv = { Bindings: Env; Variables: { actor: string } };
