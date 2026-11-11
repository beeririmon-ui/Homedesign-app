/**
 * S12, QA S8–S10 ת17: which provider runs, from a closed list, matched exactly. Production fails closed.
 *
 * - **Production** is every ENVIRONMENT that is not one of the named non-production ones: a missing or misspelled
 *   ENVIRONMENT is production, so it can never switch a mock on by accident.
 * - **A provider variable** must name a provider exactly (`cj`, never `CJ`). `mock` is allowed only outside production.
 *   Anything else (missing, `mock` in production, `UNDECIDED`, a typo) is refused: the job that needs it fails loudly and
 *   is retried, and the order stays in its real state (never "sent to the supplier", never "invoiced").
 * - **The same rules check the deploy** (api/scripts/check-config.ts, run by `npm run build`): a value in wrangler.jsonc
 *   that is not a provider fails the build; `UNDECIDED` is the one placeholder allowed there, and it fails closed at run time.
 */
import { log } from './log';

export const NON_PRODUCTION = ['development', 'preview', 'preview-local', 'test'] as const;

export const PROVIDERS = {
  /** W1: Grow; `grow` refuses until its documentation is in (lib/payments/grow.ts) */
  PAYMENT_PROVIDER: ['grow'],
  /** W2: the acquirer's invoicing module (Grow), else Morning; neither is built until its documentation is in */
  INVOICE_PROVIDER: ['grow', 'morning'],
  /** CJ (API 2.0); it refuses to create an order until its documentation is in (lib/suppliers) */
  SUPPLIER_PROVIDER: ['cj'],
  /**
   * S13 (6.3): the new-order alert. None is built: email or Telegram is the owner's choice (lib/notify). Production
   * carries `UNDECIDED` until then, and an order is never held up by its alert.
   */
  NOTIFY_PROVIDER: [],
} as const;
export type ProviderVar = keyof typeof PROVIDERS;
/** the placeholder wrangler.jsonc may carry for a provider not chosen yet: it fails closed at run time */
export const UNDECIDED = 'UNDECIDED';

export type ProviderChoice = { ok: true; id: string; mock: boolean } | { ok: false; reason: string };

export const isProduction = (env: { ENVIRONMENT?: string }): boolean => !(NON_PRODUCTION as readonly string[]).includes(env.ENVIRONMENT ?? '');

/** The provider a variable names, or why none runs. Never a fallback: a value that is not exactly a provider is refused. */
export function providerOf(env: Partial<Record<ProviderVar, string>> & { ENVIRONMENT?: string }, name: ProviderVar): ProviderChoice {
  const raw = env[name];
  const real: readonly string[] = PROVIDERS[name];
  if (raw === undefined || raw === '') return { ok: false, reason: `${name} is not set` };
  if (real.includes(raw)) return { ok: true, id: raw, mock: false };
  if (raw === 'mock')
    return isProduction(env)
      ? { ok: false, reason: `${name}=mock is refused in production (ENVIRONMENT=${env.ENVIRONMENT ?? 'unset'})` }
      : { ok: true, id: 'mock', mock: true };
  if (raw === UNDECIDED) return { ok: false, reason: `${name} is ${UNDECIDED}: no provider is chosen yet` };
  return { ok: false, reason: `${name}="${raw.slice(0, 40)}" is not a provider (${[...real, 'mock'].join(', ')})` };
}

/** The deploy check of one environment's variables (wrangler.jsonc): what would not run, and why. */
export function configIssues(vars: Record<string, unknown>): string[] {
  const env = vars as Partial<Record<ProviderVar, string>> & { ENVIRONMENT?: string };
  const out: string[] = [];
  if (typeof env.ENVIRONMENT !== 'string' || !env.ENVIRONMENT) out.push('ENVIRONMENT is not set (it is read as production)');
  for (const name of Object.keys(PROVIDERS) as ProviderVar[]) {
    const raw = env[name];
    // the one placeholder allowed in the config: the provider is not chosen yet, and the job refuses at run time
    if (raw === UNDECIDED) continue;
    const c = providerOf(env, name);
    if (!c.ok) out.push(c.reason);
  }
  return out;
}

/** Loud, once per call: the operator reads it in the Worker's logs (observability is on). S13: a structured row. */
export function refuseLoudly(what: string, reason: string, subject?: string): void {
  log.error('config.refused', { what, reason, ...(subject ? { order_id: subject } : {}) });
}
