/**
 * S18, the build check: with no email provider (EMAIL_PROVIDER=UNDECIDED, @hd/shared/email), nothing the customer reads
 * promises an email, an SMS, a message or an update (tools/lib/promises.ts). Runs after every build (`npm run build`),
 * like check:rights, and fails it on any finding.
 *
 * - **The pages:** every HTML page in dist (the prerendered routes, the order shell, 404, the story layer behind the
 *   flag), but the design test page (dist/test, a review page that never ships: vite.config.ts). What is read: the text
 *   (block by block), the attributes people read (aria-label, title, alt, placeholder, content) and JSON-LD.
 * - **The code:** every string in every JS chunk those pages load, statically or lazily (what the client renders after
 *   hydration: the checkout, the order page, the wheel). Chunks only the test page loads are listed, not scanned.
 * - **The Worker:** every string in api/src the customer can be shown (an error's message_he, the mock payment page),
 *   but the owner's screens and alerts (OWNER_ONLY).
 * - **The build's choice:** .generated/copy.he.json must be the choice for this build's EMAIL_PROVIDER (a stale file
 *   from another build fails). With a provider that really sends, the email wording is allowed, and only that is checked.
 *   npx --no-install tsx tools/check-promises.ts [--dist=<dir>] [--api=<dir>|--api=none] [--copy-out=<file>] [--json=<out>]
 */
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
import { COPY_OUT, WRANGLER_FILE, emailTarget, promiseFindings, type PromiseFinding } from './lib/promises';
import { OWNER_ONLY, codeStrings, htmlTexts, loadedChunks, walk } from './lib/promise-scan';
import { sitePath } from './lib/paths';

const arg = (name: string): string | undefined => process.argv.find((a) => a.startsWith(`--${name}=`))?.slice(name.length + 3);
const DIST = resolve(arg('dist') ?? sitePath('web/dist'));
const API = arg('api') === 'none' ? null : resolve(arg('api') ?? sitePath('api/src'));
const COPY = resolve(arg('copy-out') ?? COPY_OUT);
const WRANGLER = resolve(arg('wrangler') ?? WRANGLER_FILE);
const JSON_OUT = arg('json');

type Finding = PromiseFinding & { file: string };
const findings: Finding[] = [];
const scan = (file: string, texts: string[]) => {
  for (const t of texts) for (const f of promiseFindings(t)) findings.push({ ...f, file });
};

const t0 = Date.now();
const target = emailTarget({ publicBuild: process.env.HD_PUBLIC === '1', wrangler: WRANGLER });
const problems: string[] = [];
if (target.issue) problems.push(`${target.env}: ${target.issue}`);
// the choice the web was built with must be this build's
let chosen: { email_provider?: unknown; sends?: unknown } = {};
try {
  chosen = JSON.parse(readFileSync(COPY, 'utf8')) as typeof chosen;
} catch {
  problems.push(`${relative(sitePath(), COPY)} is missing: the copy was not built (tools/build-copy.ts runs in prepare:data)`);
}
if (chosen.email_provider !== undefined && (chosen.email_provider !== target.value || chosen.sends !== target.sends))
  problems.push(
    `${relative(sitePath(), COPY)} was built for EMAIL_PROVIDER=${String(chosen.email_provider)}, this build is for ${String(target.value)} (${target.env}): rebuild`,
  );

const pages = existsSync(DIST) ? walk(DIST, (r) => r.endsWith('.html') && !r.startsWith('test/')) : [];
if (!pages.length) problems.push(`no pages in ${DIST}: build the site first`);
const { loaded, all } = pages.length ? loadedChunks(DIST, pages) : { loaded: new Set<string>(), all: [] };
const skipped = all.filter((f) => !loaded.has(f));
const apiFiles = API ? walk(API, (r) => r.endsWith('.ts') && !OWNER_ONLY.includes(r)) : [];

if (!target.sends) {
  for (const p of pages) scan(relative(DIST, p), htmlTexts(readFileSync(p, 'utf8')));
  for (const f of loaded) scan(f, codeStrings(readFileSync(join(DIST, f), 'utf8'), f));
  for (const f of apiFiles) scan(`api/src/${relative(API!, f).split('\\').join('/')}`, codeStrings(readFileSync(f, 'utf8'), f));
}

const report = {
  email_provider: target.value,
  env: target.env,
  sends: target.sends,
  pages: pages.length,
  chunks: loaded.size,
  skipped_chunks: skipped,
  worker_files: apiFiles.length,
  problems,
  findings,
};
if (JSON_OUT) writeFileSync(resolve(JSON_OUT), JSON.stringify(report, null, 1) + '\n');
const where = `${pages.length} pages, ${loaded.size} chunks${skipped.length ? ` (not loaded by them, not scanned: ${skipped.join(', ')})` : ''}, ${apiFiles.length} Worker files`;
if (problems.length || findings.length) {
  console.error(`check-promises (S18): EMAIL_PROVIDER=${String(target.value)} (${target.env}): the build stops.`);
  for (const p of problems) console.error(`  ${p}`);
  for (const f of findings) console.error(`  ${f.file}: promises (${f.rule}: "${f.match}"): "${f.sentence}"`);
  console.error(`  scanned: ${where}`);
  process.exit(1);
}
console.log(
  target.sends
    ? `check-promises (S18): EMAIL_PROVIDER=${String(target.value)} (${target.env}) sends: the email wording is allowed`
    : `check-promises (S18): EMAIL_PROVIDER=${String(target.value)} (${target.env}): 0 promises of an email in ${where} (${Date.now() - t0} ms)`,
);
