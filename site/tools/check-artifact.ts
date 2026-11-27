/** Verifies dist-artifact/ against the Artifact page contract and limits. Exits non-zero on any violation. */
import { mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join, relative } from 'node:path';
import { GENERATED, sitePath } from './lib/paths';

const OUT = sitePath('dist-artifact');
// MOCK4: the Artifact's own limits (the publish tool, 2026-11): one publish sends at most 255 files and 64 MB, and a
// binary file is at most 15 MB (the page itself 16 MB). MOCK1–3 held themselves to 200 files and 12 MB, before videos.
// MOCK11 (2026-11-27, briefs/site-mock11-route-legs-2026-11-27.md): a version holds up to 511 files and 256 MB, sent in
// publishes of at most 255 files and 64 MB each (later publishes to the same url add to it). Over 60 MB the files are
// split in two: the first publish holds the page and everything but the route's new legs (legs 2 and on: their videos
// and posters), the second only those; .generated/artifact-batches.json lists both.
const LIMIT_BYTES = 256 * 1024 * 1024;
const LIMIT_FILES = 511;
const LIMIT_FILE = 15 * 1024 * 1024;
const PUBLISH = { bytes: 64 * 1024 * 1024, files: 255, split: 60 * 1024 * 1024 } as const;

const walk = (d: string): string[] => readdirSync(d).flatMap((n) => (statSync(join(d, n)).isDirectory() ? walk(join(d, n)) : [join(d, n)]));
const files = walk(OUT);
const bytes = files.reduce((s, f) => s + statSync(f).size, 0);
const html = readFileSync(join(OUT, 'index.html'), 'utf8');
const problems: string[] = [];
const check = (ok: boolean, msg: string) => void (ok || problems.push(msg));

check(files.length <= LIMIT_FILES, `${files.length} files > ${LIMIT_FILES}`);
check(bytes <= LIMIT_BYTES, `${(bytes / 1048576).toFixed(2)} MB > ${LIMIT_BYTES / 1048576} MB`);
for (const f of files) check(statSync(f).size <= LIMIT_FILE, `${relative(OUT, f)} is ${(statSync(f).size / 1048576).toFixed(2)} MB > 15 MB`);
check(!/<!doctype|<html[\s>]|<head[\s>]|<body[\s>]|<\/body>|<\/html>/i.test(html), 'document skeleton tags present (doctype/html/head/body)');
check(/^<title>[^<]+<\/title>\s*<style>/.test(html), 'the page must start with <title> and then <style>');
// the light tokens first: since S5 the first :root block is the magazine system's (styles/system.css, --paper …), which
// tokens.css imports before its own aliases (--bg …); no dark mode at launch (ART3). S13: the rule reads either.
check(/<style>:root\{[^}]*--(?:paper|bg):/.test(html), 'light tokens on :root must come first');
const css = /<style>([\s\S]*?)<\/style>/.exec(html)?.[1] ?? '';
// one paper, no dark mode at launch (ART3, 2026-11-03): the tokens start the stylesheet and no dark block follows
check(css.indexOf(':root{') === 0, 'the tokens on :root must start the stylesheet');
check(!/prefers-color-scheme:\s*dark|data-theme/.test(css), 'no dark theme at launch (ART3)');
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
  // WebP pictures, and (MOCK4) the arrival's two walks as H.264 MP4, (MOCK9) and the route's legs
  check(/^media\/[A-Za-z0-9/._-]+\.webp$/.test(rel) || /^media\/tour\/(arrival|route)\/[A-Za-z0-9._-]+\.mp4$/.test(rel), `unexpected file: ${rel}`);
}

// the publishes: one, or the page and the rest, then the route's new legs (MOCK11)
const size = (fs: string[]) => fs.reduce((n, f) => n + statSync(f).size, 0);
const later = (f: string) => /^media\/tour\/route\/leg(?:[2-9]|\d\d+)\./.test(relative(OUT, f));
const batches = bytes <= PUBLISH.split ? [files] : [files.filter((f) => !later(f)), files.filter(later)];
batches.forEach((b, i) => {
  check(b.length <= PUBLISH.files, `publish ${i + 1}: ${b.length} files > ${PUBLISH.files}`);
  check(size(b) <= PUBLISH.bytes, `publish ${i + 1}: ${(size(b) / 1048576).toFixed(2)} MB > ${PUBLISH.bytes / 1048576} MB`);
});
mkdirSync(GENERATED, { recursive: true });
writeFileSync(
  join(GENERATED, 'artifact-batches.json'),
  JSON.stringify(batches.map((b) => ({ files: b.length, mb: +(size(b) / 1048576).toFixed(2), paths: b.map((f) => relative(OUT, f)).sort() }))),
);

const biggest = files.reduce((a, f) => (statSync(f).size > statSync(a).size ? f : a));
console.log(
  `dist-artifact: ${files.length} files, ${(bytes / 1048576).toFixed(2)} MB (index.html ${(statSync(join(OUT, 'index.html')).size / 1024).toFixed(0)} KB; ` +
    `the largest ${relative(OUT, biggest)} ${(statSync(biggest).size / 1048576).toFixed(2)} MB)`,
);
if (problems.length) {
  for (const p of problems) console.error(`FAIL  ${p}`);
  process.exit(1);
}
if (batches.length > 1)
  batches.forEach((b, i) =>
    console.log(`publish ${i + 1}: ${b.length} files, ${(size(b) / 1048576).toFixed(2)} MB${i ? `: ${b.map((f) => relative(OUT, f)).join(', ')}` : ''}`),
  );
console.log('ok    artifact contract and limits');
