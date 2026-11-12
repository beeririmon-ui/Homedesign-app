/**
 * S12, QA S8–S10 ת17: the deploy check. Every environment in wrangler.jsonc names its providers exactly, from the closed
 * list (src/lib/config.ts): `mock` only outside production, `UNDECIDED` the one placeholder (it fails closed at run time),
 * and nothing else. S18: the customer's email (`EMAIL_PROVIDER`) too: `UNDECIDED` or a provider, never a mock. S20: the
 * shop's contact details (`CONTACT_EMAIL`, `CONTACT_PHONE`): `UNDECIDED` or well formed. S22 (QA ת69, ה25): the same
 * rule as the public build: a sample address or phone (reserved for examples, our own test values, a placeholder;
 * @hd/shared/contact-samples) fails `production`, so a deploy cannot pass with one; in the other environments it is a
 * warning.
 * Runs before the Worker's build (`npm run build -w @hd/api`), so a typo never reaches a deploy.
 *   npx --no-install tsx api/scripts/check-config.ts [path/to/wrangler.jsonc]
 */
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { contactSampleIssues } from '@hd/shared/contact-samples';
import { configIssues, contactConfigIssues, emailConfigIssues, isProduction } from '../src/lib/config';
import { parseJsonc } from './jsonc';

const file = process.argv[2] ?? resolve(dirname(fileURLToPath(import.meta.url)), '../wrangler.jsonc');
const cfg = parseJsonc(readFileSync(file, 'utf8')) as { vars?: Record<string, unknown>; env?: Record<string, { vars?: Record<string, unknown> }> };
const envs: [string, Record<string, unknown>][] = [
  ['(top level)', cfg.vars ?? {}],
  ...Object.entries(cfg.env ?? {}).map(([k, v]) => [k, v.vars ?? {}] as [string, Record<string, unknown>]),
];
const bad = envs.flatMap(([name, vars]) => [...configIssues(vars), ...emailConfigIssues(vars), ...contactConfigIssues(vars)].map((i) => `${name}: ${i}`));
// S22 (ה25): a sample contact fails production (what the public site and the deploy read), and warns elsewhere
for (const [name, vars] of envs)
  for (const i of contactSampleIssues(vars)) {
    if (isProduction(vars as { ENVIRONMENT?: string })) bad.push(`${name}: ${i}`);
    else console.warn(`check-config: warning (${name}): ${i}`);
  }
if (bad.length) {
  console.error(`check-config: ${bad.length} provider settings would not run:\n${bad.map((b) => `  ${b}`).join('\n')}`);
  process.exit(1);
}
console.log(
  `check-config: ${envs.map(([name, v]) => `${name} ${v.ENVIRONMENT} (payment ${String(v.PAYMENT_PROVIDER)}, invoices ${String(v.INVOICE_PROVIDER)}, supplier ${String(v.SUPPLIER_PROVIDER)}, alerts ${String(v.NOTIFY_PROVIDER)}, customer email ${String(v.EMAIL_PROVIDER)}, contact ${String(v.CONTACT_EMAIL)})`).join('; ')}`,
);
