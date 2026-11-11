/**
 * S7: nothing the customer's browser can receive names a supplier or carries a supplier's listing number: not a page,
 * a script, a stylesheet, a data file, nor a media path (QA on S3–S5, ת2). Scans the built site (web/dist), the story
 * behind the flag included: every file's path, and the text of every text file. `_redirects` and `_headers` are the
 * host's configuration, never served (the old addresses live there on purpose).
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';

const DIST = resolve(dirname(fileURLToPath(import.meta.url)), '../web/dist');
const TEXT = /\.(html|js|mjs|css|json|xml|txt|svg|webmanifest)$/;
const CONFIG = new Set(['_redirects', '_headers']);
/** a supplier's name as a word of an id or a path ("-cj-", "/aliexpress-"), or written out anywhere */
const SUPPLIER_IN_ID = /(?:^|[-/"'_.])(cj|aliexpress|zendrop|temu|alibaba|cjdropshipping|dsers|spocket)(?=[-/"'_.])/i;
const SUPPLIER_WORD = /\b(aliexpress|zendrop|cjdropshipping|alibaba)\b/i;
/** a listing number: six digits or more as a word of an id or a path ("…-vase-589009") */
const LISTING = /[a-z]-\d{6,}(?=[-/"'.:+]|$)/i;
/** our own content hashes (an option picture is "opt-<10 hex>") can be all digits: not a listing */
const OURS = /opt-[0-9a-f]{10}/g;

function* files(dir: string): Generator<string> {
  for (const name of readdirSync(dir)) {
    const f = join(dir, name);
    if (statSync(f).isDirectory()) yield* files(f);
    else yield f;
  }
}

test('no supplier name and no listing number in anything the site serves (paths, pages, scripts, data)', () => {
  const found: string[] = [];
  let scanned = 0;
  for (const f of files(DIST)) {
    const rel = relative(DIST, f);
    if (CONFIG.has(rel)) continue;
    scanned++;
    for (const re of [SUPPLIER_IN_ID, LISTING]) {
      const m = re.exec(`/${rel}`.replace(OURS, 'opt-h'));
      if (m) found.push(`path ${rel}: "${m[0]}"`);
    }
    if (!TEXT.test(rel)) continue;
    const text = readFileSync(f, 'utf8').replace(OURS, 'opt-h');
    for (const re of [SUPPLIER_IN_ID, SUPPLIER_WORD, LISTING]) {
      const m = re.exec(text);
      if (m) found.push(`${rel}: "…${text.slice(Math.max(0, m.index - 40), m.index + m[0].length + 20).replace(/\s+/g, ' ')}…"`);
    }
  }
  expect(scanned).toBeGreaterThan(100);
  expect(found.slice(0, 25)).toEqual([]);
});

/**
 * S13: the admin is the Worker's (api/src/routes/admin-ui.ts, behind Access); none of its code, routes or headers is in
 * the public build, and nothing in it calls the Admin API.
 */
test('no admin code in the public build: no admin route, API call, dev header or admin screen text', () => {
  const ADMIN = /\/api\/admin|\/admin\/orders|x-hd-dev-admin|ADMIN_DEV|cf-access-jwt|ניהול הזמנות|mock-supplier/;
  const found: string[] = [];
  for (const f of files(DIST)) {
    const rel = relative(DIST, f);
    if (CONFIG.has(rel) || !TEXT.test(rel)) continue;
    const m = ADMIN.exec(readFileSync(f, 'utf8'));
    if (m) found.push(`${rel}: "${m[0]}"`);
    if (/(^|\/)admin(\/|$)/.test(rel)) found.push(`path ${rel}`);
  }
  expect(found).toEqual([]);
});
