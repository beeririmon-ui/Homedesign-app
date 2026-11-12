/**
 * S18: the customer's email (an order confirmation, a tax invoice, a shipping update). None is built: today the shop
 * sends the customer no email at all (lib/notify is the owner's new-order alert only).
 *
 * - **`EMAIL_PROVIDER`** in api/wrangler.jsonc names the provider of each environment. It is `UNDECIDED` in all of them,
 *   and it has no mock: a mock would let a page promise an email that nobody sends.
 * - **The copy** (site/copy/promises.he.json) words every line that would promise an email twice: `email`, used only
 *   when the environment the site is built for names a provider from this list, and `no_email` otherwise
 *   (tools/build-copy.ts). A `no_email` line never promises an email, an SMS or an update (tools/lib/promises.ts).
 * - **A provider joins this list only with its adapter**, the job that really sends, the way the payment, invoice and
 *   supplier providers do (api/src/lib/config.ts). Then the email lines come back with the next build.
 */
export const EMAIL_PROVIDERS: readonly string[] = [];
/** the placeholder for a provider not chosen yet (the same word as api/src/lib/config.ts `UNDECIDED`) */
export const EMAIL_UNDECIDED = 'UNDECIDED';

/** Why a value of EMAIL_PROVIDER would not run, or null when it is UNDECIDED or a provider from the closed list. */
export function emailProviderIssue(value: unknown): string | null {
  if (value === EMAIL_UNDECIDED) return null;
  if (typeof value !== 'string' || value === '') return `EMAIL_PROVIDER is not set (it is ${EMAIL_UNDECIDED} until a customer email is built)`;
  if (EMAIL_PROVIDERS.includes(value)) return null;
  if (value === 'mock') return 'EMAIL_PROVIDER=mock is refused: the customer email has no mock, and a page would promise an email nobody sends';
  const list = EMAIL_PROVIDERS.length ? EMAIL_PROVIDERS.join(', ') : `none is built yet: ${EMAIL_UNDECIDED}`;
  return `EMAIL_PROVIDER="${value.slice(0, 40)}" is not a provider (${list})`;
}

/** Whether a value names a provider that really sends the customer an email. UNDECIDED, mock, a typo or nothing never do. */
export const emailSends = (value: unknown): boolean => typeof value === 'string' && EMAIL_PROVIDERS.includes(value);
