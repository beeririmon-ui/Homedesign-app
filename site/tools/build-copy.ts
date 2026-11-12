/**
 * S18: the lines that could promise the customer an email, chosen for this build (tools/lib/promises.ts).
 *
 * - **Reads** master-designer's copy (site/copy/promises.he.json) and the EMAIL_PROVIDER of the environment the site is
 *   built for (api/wrangler.jsonc: `production` with HD_PUBLIC=1, the top level otherwise).
 * - **Writes** `.generated/copy.he.json`: one line per key, the `email` wording only when that provider really sends
 *   (@hd/shared/email; none does today), `no_email` otherwise. The web imports it (web/src/copy.ts), so the build ships
 *   only the lines it shows: a wording that is not chosen is not in the bundle.
 * - **Stops the build** when the copy is malformed, when a line shown without a provider promises an email, an SMS, a
 *   message or an update, or when EMAIL_PROVIDER is neither UNDECIDED nor a provider (a mock, a typo, missing).
 *   npx --no-install tsx tools/build-copy.ts [--copy=<file>] [--wrangler=<file>] [--out=<file>]
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { COPY_FILE, COPY_OUT, WRANGLER_FILE, copyIssues, emailTarget, loadCopy, promiseFindings, selectCopy } from './lib/promises';

const arg = (name: string): string | undefined => process.argv.find((a) => a.startsWith(`--${name}=`))?.slice(name.length + 3);
const copyFile = resolve(arg('copy') ?? COPY_FILE);
const wrangler = resolve(arg('wrangler') ?? WRANGLER_FILE);
const out = resolve(arg('out') ?? COPY_OUT);
const publicBuild = process.env.HD_PUBLIC === '1';

let src: ReturnType<typeof loadCopy>;
try {
  src = loadCopy(copyFile);
} catch (e) {
  console.error(`build-copy: ${copyFile} is not JSON: ${(e as Error).message}`);
  process.exit(1);
}
const target = emailTarget({ publicBuild, wrangler });
const issues = [...copyIssues(src), ...(target.issue ? [`${target.env}: ${target.issue}`] : [])];
const lines = issues.length ? {} : selectCopy(src, target.sends);
// the lines this build shows, once more: without a provider, none of them may promise (the copy check covers the
// no_email lines; this covers the choice itself)
if (!target.sends)
  for (const [key, line] of Object.entries(lines))
    for (const f of line ? promiseFindings(line) : []) issues.push(`${key}: shown with no email provider, and promises (${f.rule}: "${f.match}")`);
if (issues.length) {
  console.error(`build-copy: ${issues.length} problem(s) in the copy (${copyFile}); the build stops:\n${issues.map((i) => `  ${i}`).join('\n')}`);
  process.exit(1);
}
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, JSON.stringify({ env: target.env, email_provider: target.value, sends: target.sends, strings: lines }, null, 1) + '\n');
const hidden = Object.values(lines).filter((l) => l === null).length;
console.log(
  `build-copy (S18): EMAIL_PROVIDER=${String(target.value)} (${target.env}) → ${target.sends ? 'the email wording' : 'the wording without an email'}: ` +
    `${Object.keys(lines).length} lines, ${hidden} not shown`,
);
