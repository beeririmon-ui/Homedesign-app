/** Verifies dist-artifact/ against the Artifact page contract and limits. Exits non-zero on any violation. */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { sitePath } from './lib/paths';

const OUT = sitePath('dist-artifact');
const LIMIT_BYTES = 12 * 1024 * 1024;
const LIMIT_FILES = 200;

const walk = (d: string): string[] => readdirSync(d).flatMap((n) => (statSync(join(d, n)).isDirectory() ? walk(join(d, n)) : [join(d, n)]));
const files = walk(OUT);
const bytes = files.reduce((s, f) => s + statSync(f).size, 0);
const html = readFileSync(join(OUT, 'index.html'), 'utf8');
const problems: string[] = [];
const check = (ok: boolean, msg: string) => void (ok || problems.push(msg));

check(files.length <= LIMIT_FILES, `${files.length} files > ${LIMIT_FILES}`);
check(bytes <= LIMIT_BYTES, `${(bytes / 1048576).toFixed(2)} MB > 12 MB`);
check(!/<!doctype|<html[\s>]|<head[\s>]|<body[\s>]|<\/body>|<\/html>/i.test(html), 'document skeleton tags present (doctype/html/head/body)');
check(/^<title>[^<]+<\/title>\s*<style>/.test(html), 'the page must start with <title> and then <style>');
check(/<style>:root\{[^}]*--bg:/.test(html), 'light tokens on :root must come first');
const css = /<style>([\s\S]*?)<\/style>/.exec(html)?.[1] ?? '';
const iRoot = css.indexOf(':root{');
const iDark = css.search(/@media\s*\(prefers-color-scheme:\s*dark\)\s*\{\s*:root:not\(\[data-theme=['"]?light['"]?\]\)\s*\{/);
const iForced = css.search(/:root\[data-theme=['"]?dark['"]?\]\s*\{/);
check(
  iRoot === 0 && iDark > iRoot && iForced > iDark,
  'token order: :root, then the dark media query guarded by :root:not([data-theme=light]), then :root[data-theme=dark]',
);
check(/body\{[^}]*background:/.test(css), 'body needs an explicit background');

// external resources: only Google Fonts
const external = [...html.matchAll(/(?:src|href)\s*=\s*["'](https?:)?\/\/([^/"']+)/gi)].map((m) => m[2]!);
const cssUrls = [...css.matchAll(/url\(\s*["']?(https?:)?\/\/([^/"')]+)/gi)].map((m) => m[2]!);
const allowed = new Set(['fonts.googleapis.com', 'fonts.gstatic.com']);
for (const host of [...external, ...cssUrls]) check(allowed.has(host), `external resource: ${host}`);
check(!/@import/.test(css), 'no @import in the stylesheet');
check(!/serviceWorker\s*\.\s*register/.test(html), 'service worker registration found');
check(!/location\.hash\s*=|#[a-z_]+=[^"'\s]/i.test(html.replace(/<style>[\s\S]*?<\/style>/, '')), '#key=value hash state found');
check(!/["'(]\/media\//.test(html), 'absolute /media/ path found (media must be relative)');

for (const f of files) {
  const rel = relative(OUT, f);
  if (rel === 'index.html') continue;
  check(/^media\/[A-Za-z0-9/._-]+\.webp$/.test(rel), `unexpected file: ${rel}`);
}

console.log(
  `dist-artifact: ${files.length} files, ${(bytes / 1048576).toFixed(2)} MB (index.html ${(statSync(join(OUT, 'index.html')).size / 1024).toFixed(0)} KB)`,
);
if (problems.length) {
  for (const p of problems) console.error(`FAIL  ${p}`);
  process.exit(1);
}
console.log('ok    artifact contract and limits');
