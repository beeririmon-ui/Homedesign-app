/**
 * S18: the customer's email (an order confirmation, a tax invoice, a shipping update). None is built: today the shop
 * sends the customer no email at all (lib/notify is the owner's new-order alert only).
 *
 * - **`EMAIL_PROVIDER`** in api/wrangler.jsonc names the provider of each environment. It is `UNDECIDED` in all of them,
 *   and it has no mock: a mock would let a page promise an email that nobody sends.
 * - **The copy** (site/copy/promises.he.json) words every line that would promise an email twice: `email`, used only
 *   when the environment's provider really sends what that line needs (its `needs`), and `no_email` otherwise
 *   (tools/build-copy.ts). A `no_email` line never promises an email, an SMS or an update (tools/lib/promises.ts).
 * - **S20, QA ת62: capabilities, not one switch.** A provider joins `EMAIL_PROVIDERS` only with its adapter, and it
 *   declares the jobs that adapter really runs (`EMAIL_CAPABILITIES`). A provider that sends only the order confirmation
 *   brings back only the lines that need `order_confirmation`; the shipping, delay, back-in-stock, invoice and marketing
 *   lines stay in their wording without an email. The Worker reads the same declaration: the waiting list (`back_in_stock`)
 *   and the marketing consent (`marketing`) are stored only where they are real (QA ת57).
 */

/** what an adapter can send the customer (the brief's four, and the two the S18 controls need) */
export const EMAIL_CAPABILITIES = [
  /** the order's confirmation, after the payment */
  'order_confirmation',
  /** the order left for shipping, with its tracking */
  'shipping_update',
  /** a delay in the delivery date (master-designer §7, the third sentence) */
  'delay_notice',
  /** the tax invoice, by email */
  'invoice_email',
  /** one message when a product on hold is back (PRE1's waiting list) */
  'back_in_stock',
  /** marketing email, only with the customer's consent */
  'marketing',
] as const;
export type EmailCapability = (typeof EMAIL_CAPABILITIES)[number];
export type EmailProviders = Readonly<Record<string, readonly EmailCapability[]>>;

/** The providers that are built, each with what its adapter really sends. None yet (EMAIL1). */
export const EMAIL_PROVIDERS: EmailProviders = {};
/** the placeholder for a provider not chosen yet (the same word as api/src/lib/config.ts `UNDECIDED`) */
export const EMAIL_UNDECIDED = 'UNDECIDED';

const own = (providers: EmailProviders, value: string): boolean => Object.prototype.hasOwnProperty.call(providers, value);

/** Why a value of EMAIL_PROVIDER would not run, or null when it is UNDECIDED or a provider from the closed list. */
export function emailProviderIssue(value: unknown, providers: EmailProviders = EMAIL_PROVIDERS): string | null {
  if (value === EMAIL_UNDECIDED) return null;
  if (typeof value !== 'string' || value === '') return `EMAIL_PROVIDER is not set (it is ${EMAIL_UNDECIDED} until a customer email is built)`;
  if (own(providers, value)) return null;
  if (value === 'mock') return 'EMAIL_PROVIDER=mock is refused: the customer email has no mock, and a page would promise an email nobody sends';
  const names = Object.keys(providers);
  const list = names.length ? names.join(', ') : `none is built yet: ${EMAIL_UNDECIDED}`;
  return `EMAIL_PROVIDER="${value.slice(0, 40)}" is not a provider (${list})`;
}

/** What the provider a value names really sends, in the order of EMAIL_CAPABILITIES. UNDECIDED, mock, a typo or nothing: none. */
export function emailCapabilities(value: unknown, providers: EmailProviders = EMAIL_PROVIDERS): EmailCapability[] {
  if (typeof value !== 'string' || !own(providers, value)) return [];
  const declared = new Set(providers[value]);
  return EMAIL_CAPABILITIES.filter((c) => declared.has(c));
}

/** Whether the provider a value names really sends this. */
export const canEmail = (value: unknown, capability: EmailCapability, providers: EmailProviders = EMAIL_PROVIDERS): boolean =>
  emailCapabilities(value, providers).includes(capability);

/** Whether a value names a provider that really sends the customer anything. UNDECIDED, mock, a typo or nothing never do. */
export const emailSends = (value: unknown, providers: EmailProviders = EMAIL_PROVIDERS): boolean => emailCapabilities(value, providers).length > 0;
