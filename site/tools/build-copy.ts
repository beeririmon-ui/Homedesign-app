/**
 * S18: the lines that could promise the customer an email, chosen for this build (tools/lib/promises.ts).
 *
 * - **Reads** master-designer's copy (site/copy/promises.he.json) and the variables of the environment the site is built
 *   for (api/wrangler.jsonc: `production` with HD_PUBLIC=1, the top level otherwise): EMAIL_PROVIDER, and (S20)
 *   CONTACT_EMAIL / CONTACT_PHONE.
 * - **Writes** `.generated/copy.he.json`: one line per key. An `email` line only when the provider really sends all it
 *   needs (S20 ת62: the capabilities its adapter declares, @hd/shared/email; none today), its `no_email` line otherwise. A
 *   `contact` line only with the shop's contact details, which it writes beside the lines (S20 ת61, @hd/shared/contact).
 *   The web imports it (web/src/copy.ts), so the build ships only the lines it shows.
 * - **Stops the build** when the copy is malformed, when a line shown without a provider promises an email, an SMS, a
 *   message or an update, when EMAIL_PROVIDER is neither UNDECIDED nor a provider (a mock, a typo, missing), when the
 *   contact variables are malformed, and (S20 ת61) when the public build (HD_PUBLIC=1) has no contact details or an
 *   address reserved for examples: a shop that sells at a distance must give its customers a way to reach it
 *   (docs/ops/deploy-runbook.md, "פרטי הקשר של העסק"). Behind the flag that is a warning.
 *   npx --no-install tsx tools/build-copy.ts [--copy=<file>] [--wrangler=<file>] [--out=<file>]
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { contactIssues, contactOf, isPlaceholderEmail } from '@hd/shared/contact';
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
const contact = contactOf(target.vars);
const issues = [
  ...copyIssues(src),
  ...(target.issue ? [`${target.env}: ${target.issue}`] : []),
  ...contactIssues(target.vars).map((i) => `${target.env}: ${i}`),
];
const NO_CONTACT =
  'no business contact: CONTACT_EMAIL is UNDECIDED, so the contact block is hidden and every "כתבו לנו" line is in its wording without contact (CONTACT1)';
if (publicBuild && !contact && !contactIssues(target.vars).length)
  issues.push(`${target.env}: ${NO_CONTACT}. The public build needs the shop's contact details (docs/ops/deploy-runbook.md, "פרטי הקשר של העסק")`);
if (publicBuild && contact && isPlaceholderEmail(contact.email))
  issues.push(`${target.env}: CONTACT_EMAIL=${contact.email} is an address reserved for examples, not the shop's`);
const state = { capabilities: target.capabilities, contact: !!contact };
const lines = issues.length ? {} : selectCopy(src, state);
// the lines this build shows, once more: a promise is allowed only in an email line whose needs are real (the copy
// check covers the other wordings; this covers the choice itself)
const emailLines = new Set(Object.entries(src.strings).flatMap(([k, e]) => ('email' in e && e.email && lines[k] === e.email ? [k] : [])));
for (const [key, line] of Object.entries(lines))
  if (line && !emailLines.has(key))
    for (const f of promiseFindings(line)) issues.push(`${key}: shown without an email provider that sends it, and promises (${f.rule}: "${f.match}")`);
if (issues.length) {
  console.error(`build-copy: ${issues.length} problem(s) in the copy (${copyFile}); the build stops:\n${issues.map((i) => `  ${i}`).join('\n')}`);
  process.exit(1);
}
mkdirSync(dirname(out), { recursive: true });
writeFileSync(
  out,
  JSON.stringify({ env: target.env, email_provider: target.value, capabilities: target.capabilities, sends: target.sends, contact, strings: lines }, null, 1) +
    '\n',
);
const hidden = Object.values(lines).filter((l) => l === null).length;
if (!contact) console.warn(`build-copy: warning (${target.env}): ${NO_CONTACT}. A public build (HD_PUBLIC=1) stops here.`);
console.log(
  `build-copy (S18, S20): EMAIL_PROVIDER=${String(target.value)} (${target.env}) → ${
    target.sends ? `the email wording where its needs are real (${target.capabilities.join(', ')})` : 'the wording without an email'
  }; contact ${contact ? contact.email : 'none'}: ${Object.keys(lines).length} lines, ${hidden} not shown`,
);
