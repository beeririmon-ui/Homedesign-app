/** Deletes the local (Miniflare) D1 state so `db:reset` starts from an empty database. Local only. */
import { rmSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const state = resolve(dirname(fileURLToPath(import.meta.url)), '../../.wrangler-state/v3/d1');
rmSync(state, { recursive: true, force: true });
console.log('local D1 state cleared:', state);
