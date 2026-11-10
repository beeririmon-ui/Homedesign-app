/**
 * S12, QA S8–S10 ת17: the deploy check. Every environment in wrangler.jsonc names its providers exactly, from the closed
 * list (src/lib/config.ts): `mock` only outside production, `UNDECIDED` the one placeholder (it fails closed at run time),
 * and nothing else. Runs before the Worker's build (`npm run build -w @hd/api`), so a typo never reaches a deploy.
 *   npx tsx api/scripts/check-config.ts [path/to/wrangler.jsonc]
 */
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { configIssues } from '../src/lib/config';
import { parseJsonc } from './jsonc';

const file = process.argv[2] ?? resolve(dirname(fileURLToPath(import.meta.url)), '../wrangler.jsonc');
const cfg = parseJsonc(readFileSync(file, 'utf8')) as { vars?: Record<string, unknown>; env?: Record<string, { vars?: Record<string, unknown> }> };
const envs: [string, Record<string, unknown>][] = [
  ['(top level)', cfg.vars ?? {}],
  ...Object.entries(cfg.env ?? {}).map(([k, v]) => [k, v.vars ?? {}] as [string, Record<string, unknown>]),
];
const bad = envs.flatMap(([name, vars]) => configIssues(vars).map((i) => `${name}: ${i}`));
if (bad.length) {
  console.error(`check-config: ${bad.length} provider settings would not run:\n${bad.map((b) => `  ${b}`).join('\n')}`);
  process.exit(1);
}
console.log(
  `check-config: ${envs.map(([name, v]) => `${name} ${v.ENVIRONMENT} (payment ${String(v.PAYMENT_PROVIDER)}, invoices ${String(v.INVOICE_PROVIDER)}, supplier ${String(v.SUPPLIER_PROVIDER)})`).join('; ')}`,
);
