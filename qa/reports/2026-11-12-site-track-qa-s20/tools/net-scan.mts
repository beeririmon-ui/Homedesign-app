/** QA S20: reused from QA S18 (qa/reports/2026-11-12-site-track-qa-s18/tools), only the type paths changed.
 *
 * QA S18: a broad net over everything a build ships and the Worker can say, wider than the gate, for review by hand.
 * - dist: every HTML page (text, every attribute value, JSON islands of any type), every .js anywhere in dist (all
 *   strings, chunks the gate skips included), every other text file (json, xml, txt, css, svg, webmanifest, _headers);
 * - api/src and shared/src: every string (OWNER_ONLY files marked, not dropped);
 * - .generated/seed.sql: the strings the Worker serves from D1.
 * Each sentence that hits the net is listed with where it is, and whether the gate's promiseFindings catches it.
 *   cd <copy>/site && node node_modules/tsx/dist/cli.mjs <this> --site=<copy>/site --dist=<dist> --out=<json>
 */
import { existsSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join, relative } from 'node:path';
import { pathToFileURL } from 'node:url';
import { NET } from './net-scan-net.mts';

const arg = (n: string) => process.argv.find((a) => a.startsWith(`--${n}=`))?.slice(n.length + 3);
const SITE = arg('site')!;
const DIST = arg('dist') ?? join(SITE, 'web/dist');
const OUT = arg('out')!;
const { promiseFindings, sentences } = (await import(pathToFileURL(join(SITE, 'tools/lib/promises.ts')).href)) as typeof import('../build-s20/site/tools/lib/promises');
const { codeStrings, OWNER_ONLY } = (await import(pathToFileURL(join(SITE, 'tools/lib/promise-scan.ts')).href)) as typeof import('../build-s20/site/tools/lib/promise-scan');


const walk = (dir: string, keep: (r: string) => boolean, root = dir): string[] => {
  if (!existsSync(dir)) return [];
  const out: string[] = [];
  for (const e of readdirSync(dir)) {
    const p = join(dir, e);
    const r = relative(root, p).split('\\').join('/');
    if (statSync(p).isDirectory()) {
      if (r === 'media' || r.startsWith('media/')) continue;
      out.push(...walk(p, keep, root));
    } else if (keep(r)) out.push(p);
  }
  return out;
};
const decode = (s: string) =>
  s
    .replace(/&#x([0-9a-f]+);/gi, (_m, h: string) => String.fromCodePoint(parseInt(h, 16)))
    .replace(/&#(\d+);/g, (_m, d: string) => String.fromCodePoint(parseInt(d, 10)))
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&apos;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&');

type Hit = { sentence: string; where: string[]; kinds: string[]; gate: string | null; owner_only: boolean };
const hits = new Map<string, Hit>();
const add = (text: string, where: string, kind: string, ownerOnly = false) => {
  for (const s of sentences(text)) {
    if (!NET.test(s)) continue;
    if (s.length > 400) continue; // code-ish blobs: listed separately below
    const h = hits.get(s) ?? { sentence: s, where: [], kinds: [], gate: null, owner_only: ownerOnly };
    if (!h.where.includes(where)) h.where.push(where);
    if (!h.kinds.includes(kind)) h.kinds.push(kind);
    h.owner_only = h.owner_only && ownerOnly;
    const f = promiseFindings(s);
    h.gate = f.length ? `${f[0]!.rule}:${f[0]!.match}` : null;
    hits.set(s, h);
  }
};
/** a string worth reading: has Hebrew, or is an English phrase of 3+ words (not code identifiers) */
const readable = (s: string) => /[\u05D0-\u05EA]/.test(s) || (/^[A-Za-z][A-Za-z ,.'’!?-]{10,}$/.test(s.trim()) && s.trim().split(/\s+/).length >= 3);

const counts = { html: 0, js: 0, other: 0, api: 0, shared: 0, seed: 0 };
// HTML pages: text, every attribute, every JSON island
for (const p of walk(DIST, (r) => r.endsWith('.html'))) {
  counts.html++;
  const rel = relative(DIST, p);
  const html = readFileSync(p, 'utf8');
  for (const m of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)) {
    if (/type="application\/(?:ld\+)?json"/i.test(m[1]!)) {
      try {
        JSON.parse(m[2]!, (_k, v: unknown) => (typeof v === 'string' && readable(v) && add(v, rel, 'html-json'), v));
      } catch {
        add(m[2]!, rel, 'html-json-raw');
      }
    } else if (m[2]!.trim()) for (const s of codeStrings(m[2]!, 'inline.js')) if (readable(s)) add(s, rel, 'html-inline-js');
  }
  const body = html.replace(/<script\b[\s\S]*?<\/script>/gi, '\n').replace(/<style\b[\s\S]*?<\/style>/gi, '\n').replace(/<!--[\s\S]*?-->/g, '');
  for (const m of body.matchAll(/\s([a-zA-Z_:][-\w:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)')/g)) {
    const v = decode(m[2] ?? m[3] ?? '');
    if (readable(v)) add(v, rel, `html-attr:${m[1]!.toLowerCase()}`);
  }
  // the text, inline elements glued (as a person reads it), blocks split
  const text = decode(body.replace(/<\/?(?:p|div|li|h[1-6]|br|dt|dd|section|article|header|footer|nav|main|form|label|button|option|title|td|th|figcaption|legend|summary)\b[^>]*>/gi, '\n').replace(/<[^>]+>/g, ''));
  add(text, rel, 'html-text');
}
// every .js in dist, wherever it is
for (const p of walk(DIST, (r) => /\.(?:m?js|cjs)$/.test(r))) {
  counts.js++;
  const rel = relative(DIST, p);
  for (const s of codeStrings(readFileSync(p, 'utf8'), rel)) if (readable(s)) add(s, rel, 'js');
}
// every other text file in dist
for (const p of walk(DIST, (r) => /\.(?:json|xml|txt|css|svg|webmanifest)$|(?:^|\/)_headers$|(?:^|\/)_redirects$/.test(r))) {
  counts.other++;
  const rel = relative(DIST, p);
  const t = readFileSync(p, 'utf8');
  if (rel.endsWith('.json')) {
    try {
      JSON.parse(t, (_k, v: unknown) => (typeof v === 'string' && readable(v) && add(v, rel, 'dist-json'), v));
      continue;
    } catch {
      /* fall through */
    }
  }
  if (rel.endsWith('.css')) for (const m of t.matchAll(/content:\s*(["'])((?:\\.|(?!\1).)*)\1/g)) add(m[2]!, rel, 'css-content');
  else add(t.replace(/<[^>]+>/g, '\n'), rel, `dist-${rel.split('.').pop()}`);
}
// the Worker and shared code
for (const [dir, kind] of [
  ['api/src', 'api'],
  ['shared/src', 'shared'],
] as const) {
  for (const p of walk(join(SITE, dir), (r) => /\.(?:ts|tsx|json)$/.test(r))) {
    const rel = relative(join(SITE, dir), p).split('\\').join('/');
    counts[kind]++;
    const owner = kind === 'api' && OWNER_ONLY.includes(rel);
    const t = readFileSync(p, 'utf8');
    const strs = p.endsWith('.json') ? (() => { const o: string[] = []; JSON.parse(t, (_k, v: unknown) => (typeof v === 'string' && o.push(v), v)); return o; })() : codeStrings(t, p);
    for (const s of strs) if (readable(s)) add(s, `${dir}/${rel}`, kind, owner);
  }
}
// the D1 seed
const seed = join(SITE, '.generated/seed.sql');
if (existsSync(seed)) {
  counts.seed = 1;
  for (const m of readFileSync(seed, 'utf8').matchAll(/'((?:[^']|'')*)'/g)) {
    const v = m[1]!.replace(/''/g, "'");
    if (readable(v)) add(v, '.generated/seed.sql', 'seed');
  }
}
const list = [...hits.values()].sort((a, b) => a.sentence.localeCompare(b.sentence, 'he'));
writeFileSync(OUT, JSON.stringify({ counts, hits: list.length, gate_caught: list.filter((h) => h.gate).length, list }, null, 1) + '\n');
console.log(JSON.stringify({ counts, hits: list.length, gate_caught: list.filter((h) => h.gate).length }));
