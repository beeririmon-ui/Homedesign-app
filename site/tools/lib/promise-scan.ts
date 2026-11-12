/**
 * S18: what tools/check-promises.ts reads in a build: what a person reads in a page, every string in a script, and the
 * chunks the pages load (tools/lib/promises.ts says what a promise is).
 */
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import ts from 'typescript';

/** the Worker's screens and messages for the owner, never the customer's (paths under api/src) */
export const OWNER_ONLY = ['routes/admin-ui.ts', 'routes/admin.ts', 'lib/admin-orders.ts', 'lib/notify/index.ts', 'lib/access.ts'];

export function walk(dir: string, keep: (rel: string) => boolean, root = dir): string[] {
  if (!existsSync(dir)) return [];
  const out: string[] = [];
  for (const e of readdirSync(dir)) {
    const p = join(dir, e);
    const rel = relative(root, p).split('\\').join('/');
    if (statSync(p).isDirectory()) out.push(...walk(p, keep, root));
    else if (keep(rel)) out.push(p);
  }
  return out;
}

const ENTITIES: Record<string, string> = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', '#39': "'" };
const decode = (s: string): string =>
  s.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+|#39);/gi, (m, e: string) =>
    e[0] === '#' ? String.fromCodePoint(e[1] === 'x' || e[1] === 'X' ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10)) : (ENTITIES[e.toLowerCase()] ?? m),
  );
const BLOCK =
  /<\/?(?:p|div|li|ul|ol|h[1-6]|br|hr|dt|dd|dl|section|article|aside|header|footer|nav|main|form|fieldset|legend|label|button|a|figure|figcaption|table|tr|td|th|option|select|textarea|title|blockquote|summary|details|span)\b[^>]*>/gi;

/** what a person reads in a page: its text, block by block, the attributes read aloud or shown, and its JSON-LD */
export function htmlTexts(html: string): string[] {
  const out: string[] = [];
  for (const m of html.matchAll(/<script\b[^>]*type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/gi)) {
    const strings: string[] = [];
    try {
      JSON.parse(m[1]!, (_k, v: unknown) => (typeof v === 'string' && strings.push(v), v));
    } catch {
      strings.push(m[1]!);
    }
    out.push(...strings);
  }
  const body = html
    .replace(/<script\b[\s\S]*?<\/script>/gi, '\n')
    .replace(/<style\b[\s\S]*?<\/style>/gi, '\n')
    .replace(/<!--[\s\S]*?-->/g, '');
  for (const m of body.matchAll(/\s(?:aria-label|aria-description|title|alt|placeholder|content)="([^"]*)"/gi)) out.push(decode(m[1]!));
  // a span or a link is a block here too: a sentence is never glued across two of them
  out.push(...decode(body.replace(BLOCK, '\n').replace(/<[^>]+>/g, '')).split('\n'));
  return out.filter((t) => t.trim());
}

/** every string in a script (literals and the parts of template literals), as TypeScript reads it */
export function codeStrings(code: string, file: string): string[] {
  const kind = file.endsWith('.ts') ? ts.ScriptKind.TS : file.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.JS;
  const sf = ts.createSourceFile(file, code, ts.ScriptTarget.Latest, false, kind);
  const out: string[] = [];
  const visit = (n: ts.Node): void => {
    if (ts.isStringLiteralLike(n) || ts.isTemplateHead(n) || ts.isTemplateMiddle(n) || ts.isTemplateTail(n) || ts.isJsxText(n)) out.push(n.text);
    n.forEachChild(visit);
  };
  visit(sf);
  return out;
}

/** the chunks a set of pages loads: their scripts, and every chunk those name (static imports, dynamic imports, preloads) */
export function loadedChunks(dist: string, pages: string[]): { loaded: Set<string>; all: string[] } {
  const all = walk(join(dist, 'assets'), (r) => r.endsWith('.js')).map((p) => relative(dist, p).split('\\').join('/'));
  const byName = new Map(all.map((f) => [f.split('/').pop()!, f]));
  const refs = (text: string): string[] =>
    [...text.matchAll(/["'`(](?:\.?\/)?(?:assets\/)?([\w.-]+\.js)["'`)]/g)].map((m) => byName.get(m[1]!)).filter((f): f is string => !!f);
  const loaded = new Set<string>();
  const stack = pages.flatMap((p) => refs(readFileSync(p, 'utf8')));
  while (stack.length) {
    const f = stack.pop()!;
    if (loaded.has(f)) continue;
    loaded.add(f);
    stack.push(...refs(readFileSync(join(dist, f), 'utf8')).filter((x) => !loaded.has(x)));
  }
  return { loaded, all };
}
