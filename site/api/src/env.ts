export type RateLimiter = { limit(options: { key: string }): Promise<{ success: boolean }> };

export type SupplierJob = { kind: 'submit-order'; order_id: string };

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
  ADMIN_DEV_BYPASS?: string;
};

export type AppEnv = { Bindings: Env; Variables: { actor: string } };
