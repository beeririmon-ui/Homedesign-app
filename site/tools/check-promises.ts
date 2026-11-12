/**
 * S18, the build check: nothing the customer reads promises an email, an SMS, a message or an update that the shop does
 * not send (tools/lib/promises.ts). Runs after every build (`npm run build`), like check:rights, and fails it on any
 * finding.
 *
 * - **The pages:** every HTML page in dist (the prerendered routes, the order shell, 404, the story layer behind the
 *   flag), but the design review pages (dist/test, which never ship: vite.config.ts). S20 (QA ת60): the text with
 *   inline elements joined, every attribute, every JSON island (the story's data), inline scripts and styles.
 * - **The code:** every script anywhere in dist, by any URL, but the ones only the review pages load; strings, and the
 *   text they render together (JSX children, templates, "+").
 * - **Every other file in dist** that is text: stylesheets (CSS `content`), JSON, SVG, XML, robots, headers.
 * - **The Worker:** every string in api/src (.ts and .json) and in the shared modules it imports (ORDER_STATUS_HE is
 *   served as `status_he`), and in its bundle (api/dist/index.js, when built), but the owner's screens and alerts
 *   (OWNER_ONLY) and the strings that come from them.
 * - **The build's choice:** .generated/copy.he.json must be the choice for this build's EMAIL_PROVIDER, its
 *   capabilities and its contact details (a stale file from another build fails). S20 (QA ת62): with a provider that
 *   sends, the scan still runs; a promise passes only when it is the email wording of a line whose needs are real.
 *   npx --no-install tsx tools/check-promises.ts [--dist=<dir>] [--api=<dir>|--api=none] [--shared=<dir>] [--worker-bundle=<file>|none]
 *     [--copy-out=<file>] [--wrangler=<file>] [--json=<out>]
 */
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
import { contactOf } from '@hd/shared/contact';
import { COPY_FILE, COPY_OUT, WRANGLER_FILE, allowedPromises, emailTarget, loadCopy, promiseFindings, type PromiseFinding } from './lib/promises';
import { OWNER_ONLY, codeStrings, fileTexts, htmlTexts, scriptsOf, walk, workerSources } from './lib/promise-scan';
import { sitePath } from './lib/paths';

const arg = (name: string): string | undefined => process.argv.find((a) => a.startsWith(`--${name}=`))?.slice(name.length + 3);
const DIST = resolve(arg('dist') ?? sitePath('web/dist'));
const API = arg('api') === 'none' ? null : resolve(arg('api') ?? sitePath('api/src'));
const SHARED = resolve(arg('shared') ?? sitePath('shared/src'));
const BUNDLE = arg('worker-bundle') === 'none' ? null : resolve(arg('worker-bundle') ?? sitePath('api/dist/index.js'));
const COPY = resolve(arg('copy-out') ?? COPY_OUT);
const WRANGLER = resolve(arg('wrangler') ?? WRANGLER_FILE);
const JSON_OUT = arg('json');

type Finding = PromiseFinding & { file: string };
const findings: Finding[] = [];
let allowedHits = 0;

const t0 = Date.now();
const target = emailTarget({ publicBuild: process.env.HD_PUBLIC === '1', wrangler: WRANGLER });
const contact = contactOf(target.vars);
const problems: string[] = [];
if (target.issue) problems.push(`${target.env}: ${target.issue}`);
// the choice the web was built with must be this build's
let chosen: { email_provider?: unknown; capabilities?: unknown; sends?: unknown; contact?: unknown } = {};
try {
  chosen = JSON.parse(readFileSync(COPY, 'utf8')) as typeof chosen;
} catch {
  problems.push(`${relative(sitePath(), COPY)} is missing: the copy was not built (tools/build-copy.ts runs in prepare:data)`);
}
const same = (a: unknown, b: unknown) => JSON.stringify(a ?? null) === JSON.stringify(b ?? null);
if (
  chosen.email_provider !== undefined &&
  (chosen.email_provider !== target.value || !same(chosen.capabilities, target.capabilities) || chosen.sends !== target.sends || !same(chosen.contact, contact))
)
  problems.push(
    `${relative(sitePath(), COPY)} was built for EMAIL_PROVIDER=${String(chosen.email_provider)} (${JSON.stringify(chosen.capabilities ?? [])}, contact ${JSON.stringify(chosen.contact ?? null)}), this build is for ${String(target.value)} (${JSON.stringify(target.capabilities)}, contact ${JSON.stringify(contact)}) (${target.env}): rebuild`,
  );

// the promises this build may make: the email wording of a line whose needs are real (none without a provider)
let allowed = new Set<string>();
try {
  allowed = allowedPromises(loadCopy(COPY_FILE), target.capabilities);
} catch {
  // the copy check (build-copy) reports a broken copy file
}
const seen = new Set<string>();
const scan = (file: string, texts: string[]) => {
  for (const t of texts)
    for (const f of promiseFindings(t)) {
      // one finding per sentence and rule in a file (a page is read twice: inline elements glued, and spaced)
      const key = `${file}\u0000${f.rule}\u0000${f.sentence}`;
      if (seen.has(key)) continue;
      seen.add(key);
      if (allowed.has(f.sentence)) allowedHits++;
      else findings.push({ ...f, file });
    }
};

const isReview = (r: string) => r.startsWith('test/') || r.startsWith('media/test/');
const pages = existsSync(DIST) ? walk(DIST, (r) => /\.html?$/.test(r) && !isReview(r)) : [];
const reviewPages = existsSync(DIST) ? walk(DIST, (r) => /\.html?$/.test(r) && isReview(r)) : [];
if (!pages.length) problems.push(`no pages in ${DIST}: build the site first`);
const scripts = pages.length ? scriptsOf(DIST, pages, reviewPages) : { loaded: new Set<string>(), reviewOnly: [], unreferenced: [], all: [] };
const others = existsSync(DIST) ? walk(DIST, (r) => !isReview(r) && !/\.(?:html?|m?js)$/.test(r) && !r.endsWith('.map')) : [];
const apiFiles = API ? workerSources(API, SHARED) : [];
const bundle = BUNDLE && existsSync(BUNDLE) ? BUNDLE : null;

for (const p of pages) scan(relative(DIST, p), htmlTexts(readFileSync(p, 'utf8')));
for (const f of scripts.all) if (!scripts.reviewOnly.includes(f)) scan(f, codeStrings(readFileSync(join(DIST, f), 'utf8'), f));
let textFiles = 0;
for (const f of others) {
  const texts = fileTexts(f);
  if (!texts) continue;
  textFiles++;
  scan(relative(DIST, f), texts);
}
const rel = (f: string) => {
  const under = (dir: string | null, name: string) => (dir && !relative(dir, f).startsWith('..') ? `${name}/${relative(dir, f)}` : null);
  return (under(API, 'api/src') ?? under(SHARED, 'shared/src') ?? relative(sitePath(), f)).split('\\').join('/');
};
for (const f of apiFiles) scan(rel(f), f.endsWith('.json') ? (fileTexts(f) ?? []) : codeStrings(readFileSync(f, 'utf8'), f));
if (bundle) {
  // the owner's strings are in the bundle too: leave out what comes from OWNER_ONLY
  const owner = new Set(API ? OWNER_ONLY.flatMap((o) => (existsSync(join(API, o)) ? codeStrings(readFileSync(join(API, o), 'utf8'), o) : [])) : []);
  scan(
    rel(bundle),
    codeStrings(readFileSync(bundle, 'utf8'), bundle).filter((s) => !owner.has(s)),
  );
}

const report = {
  email_provider: target.value,
  capabilities: target.capabilities,
  contact: contact?.email ?? null,
  env: target.env,
  sends: target.sends,
  pages: pages.length,
  scripts: scripts.all.length - scripts.reviewOnly.length,
  scripts_unreferenced: scripts.unreferenced,
  scripts_review_only: scripts.reviewOnly,
  text_files: textFiles,
  worker_files: apiFiles.length,
  worker_bundle: bundle ? rel(bundle) : null,
  allowed_promises: allowedHits,
  problems,
  findings,
};
if (JSON_OUT) writeFileSync(resolve(JSON_OUT), JSON.stringify(report, null, 1) + '\n');
const where =
  `${pages.length} pages, ${report.scripts} scripts (${scripts.loaded.size} loaded by the pages${scripts.unreferenced.length ? `, ${scripts.unreferenced.length} by no page, scanned all the same` : ''}; ` +
  `${scripts.reviewOnly.length} only the review pages load, not scanned), ${textFiles} other text files, ${apiFiles.length} Worker files${bundle ? ' and its bundle' : ''}`;
const label = `check-promises (S18, S20): EMAIL_PROVIDER=${String(target.value)} (${target.env})`;
if (problems.length || findings.length) {
  console.error(`${label}: the build stops.`);
  for (const p of problems) console.error(`  ${p}`);
  for (const f of findings) console.error(`  ${f.file}: promises (${f.rule}: "${f.match}"): "${f.sentence}"`);
  console.error(`  scanned: ${where}`);
  process.exit(1);
}
console.log(
  target.sends
    ? `${label} sends ${target.capabilities.join(', ')}: ${allowedHits} promises, all the email wording of lines whose needs are real, in ${where} (${Date.now() - t0} ms)`
    : `${label}: 0 promises of an email in ${where} (${Date.now() - t0} ms)`,
);
