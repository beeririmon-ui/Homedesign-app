/**
 * Local only. Deletes the local (Miniflare) D1 state so `db:reset` starts from an empty database, and creates
 * api/.dev.vars on first run with a random local webhook secret for the mock payment provider (gitignored; never
 * a real credential). Real secrets live only in `wrangler secret` (docs/architecture.md, "אבטחה").
 */
import { existsSync, rmSync, writeFileSync } from 'node:fs';
import { randomBytes } from 'node:crypto';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const state = resolve(here, '../../.wrangler-state/v3/d1');
rmSync(state, { recursive: true, force: true });
console.log('local D1 state cleared:', state);

const devVars = resolve(here, '../.dev.vars');
if (!existsSync(devVars)) {
  writeFileSync(
    devVars,
    [
      '# Created by api/scripts/reset-local-db.ts for local development only (gitignored). Not a real credential.',
      `PAYMENT_WEBHOOK_SECRET=local-${randomBytes(18).toString('hex')}`,
      'ADMIN_DEV_BYPASS=1',
      '',
    ].join('\n'),
  );
  console.log('created api/.dev.vars (local mock secret)');
}
