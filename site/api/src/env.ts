export type RateLimiter = { limit(options: { key: string }): Promise<{ success: boolean }> };

export type SupplierJob = { kind: 'submit-order'; order_id: string } | { kind: 'issue-invoice'; order_id: string };

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
};

export type AppEnv = { Bindings: Env; Variables: { actor: string } };
