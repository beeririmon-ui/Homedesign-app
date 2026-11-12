/**
 * S18: what tools/check-promises.ts reads in a build: what a person reads in a page, every string in a script, and the
 * chunks the pages load (tools/lib/promises.ts says what a promise is).
 *
 * S20, QA ת60, the blind spots:
 * - **Text split across elements:** a span, a link, a <b> joins the sentence around it, as the browser renders it (the
 *   text is read with inline elements glued, and once more with a space in their place).
 * - **Text split in code:** JSX children (`u("p",{children:["אישור ",u("b",{children:"יישלח"})," לאימייל"]})`), a
 *   template literal's parts around `${}`, and `"a" + "b"` are read joined, as well as one by one.
 * - **Attributes:** every attribute, quoted either way or not at all (value, aria-roledescription, data-…).
 * - **Scripts and styles in a page:** every JSON island (application/json, ld+json…), every inline script, every
 *   <style> and style attribute (CSS `content`).
 * - **Every file:** HTML, JS anywhere in the build (not only assets/), CSS, JSON, SVG, XML and other text (`fileTexts`).
 * - **The Worker:** api/src, the shared modules it imports (`workerSources`), and its bundle (api/dist), but the owner's.
 *
 * S22, QA ת71:
 * - **Joins in code:** `["אישור ההזמנה","יישלח","במייל"].join(" ")` with a fixed separator (a literal; none is ","; any
 *   other separator is read as a space) and `"האישור ".concat("יגיע ", …)` are read as the text they make.
 * - **Not covered, on purpose: binary files' metadata** (a WebP's or a JPEG's XMP and EXIF, a font's name table, a PDF's
 *   info). `fileTexts` skips binaries. The customer never reads it: no browser shows an image's or a font's metadata on
 *   the page, and the site never prints it. What a page shows of an image is its alt text and caption, which are scanned
 *   with the page. QA's X11 (a WebP with an XMP description) is kept as a known, accepted limit.
 */
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, extname, join, relative, resolve } from 'node:path';
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
  /<\/?(?:p|div|li|ul|ol|h[1-6]|br|hr|dt|dd|dl|section|article|aside|header|footer|nav|main|form|fieldset|legend|button|figure|figcaption|table|thead|tbody|tfoot|caption|tr|td|th|option|optgroup|select|textarea|title|blockquote|summary|details|dialog|menu|address|pre|noscript|template|head|body|html|meta|link|input|img|picture|source|video|audio|svg|iframe|canvas|output|progress|meter)\b[^>]*>/gi;
const JSON_TYPES = /^(?:application\/(?:[\w.+-]*\+)?json|importmap|speculationrules)$/i;
const JS_TYPES = /^(?:|module|text\/javascript|application\/javascript|text\/ecmascript)$/i;

/** every attribute of every tag: name and value, quoted either way or not at all */
function attributes(html: string): { name: string; value: string }[] {
  const out: { name: string; value: string }[] = [];
  for (const tag of html.matchAll(/<[a-zA-Z][\w:-]*((?:\s+[^\s"'>/=]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'=<>`]+))?)*)\s*\/?>/g))
    for (const a of tag[1]!.matchAll(/([^\s"'>/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g))
      out.push({ name: a[1]!.toLowerCase(), value: decode(a[2] ?? a[3] ?? a[4] ?? '') });
  return out;
}

/** every string in a JSON text (its values), or the text itself when it is not JSON */
export function jsonStrings(text: string): string[] {
  const out: string[] = [];
  try {
    JSON.parse(text, (_k, v: unknown) => (typeof v === 'string' && out.push(v), v));
  } catch {
    out.push(text);
  }
  return out;
}

/** every string in a stylesheet (what `content` draws, among the rest), CSS escapes read */
export function cssStrings(css: string): string[] {
  const out: string[] = [];
  for (const m of css.replace(/\/\*[\s\S]*?\*\//g, '').matchAll(/"((?:[^"\\]|\\[\s\S])*)"|'((?:[^'\\]|\\[\s\S])*)'/g))
    out.push(
      (m[1] ?? m[2] ?? '')
        .replace(/\\([0-9a-f]{1,6})\s?/gi, (_x, h: string) => String.fromCodePoint(parseInt(h, 16)))
        .replace(/\\\n/g, '')
        .replace(/\\(.)/g, '$1'),
    );
  return out;
}

/** what a person reads in a page: its text, block by block, every attribute, its JSON, its inline scripts and styles */
export function htmlTexts(html: string): string[] {
  const out: string[] = [];
  for (const m of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)) {
    const attrs = attributes(`<script${m[1]}>`);
    const type = attrs.find((a) => a.name === 'type')?.value.trim() ?? '';
    const body = m[2]!;
    if (!body.trim()) continue;
    if (JSON_TYPES.test(type)) out.push(...jsonStrings(body));
    else if (JS_TYPES.test(type)) out.push(...codeStrings(body, 'inline.js'));
    else out.push(body);
  }
  for (const m of html.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/gi)) out.push(...cssStrings(m[1]!));
  const body = html
    .replace(/<script\b[\s\S]*?<\/script>/gi, '\n')
    .replace(/<style\b[\s\S]*?<\/style>/gi, '\n')
    .replace(/<!--[\s\S]*?-->/g, '');
  for (const a of attributes(body)) {
    if (!a.value.trim()) continue;
    if (a.name === 'style') out.push(...cssStrings(`x{${a.value}}`));
    else out.push(a.value);
  }
  // the text: blocks apart; inline elements (span, a, b, strong…) glued as rendered, and once more with a space
  const blocks = body.replace(BLOCK, '\n');
  out.push(...decode(blocks.replace(/<[^>]+>/g, '')).split('\n'));
  out.push(...decode(blocks.replace(/<[^>]+>/g, ' ')).split('\n'));
  return [...new Set(out)].filter((t) => t.trim());
}

const isStr = (n: ts.Node): n is ts.StringLiteralLike => ts.isStringLiteralLike(n);

/** S22 (QA ת71): `[…].join(sep)` and `x.concat(…)` as the text they make; null for any other call */
function joined(n: ts.CallExpression): string | null {
  if (!ts.isPropertyAccessExpression(n.expression)) return null;
  const name = n.expression.name.text;
  const target = n.expression.expression;
  if (name === 'join' && ts.isArrayLiteralExpression(target)) {
    const a = n.arguments[0];
    const sep = a === undefined ? ',' : isStr(a) ? a.text : ' ';
    return target.elements.map(rendered).join(sep);
  }
  if (name === 'concat' && n.arguments.length) return rendered(target) + n.arguments.map(rendered).join('');
  return null;
}

/** the text an expression renders, when it is made of strings: literals, templates, "+", JSX children, join and
 * concat (S22); '' for the rest */
function rendered(n: ts.Node): string {
  if (isStr(n)) return n.text;
  if (ts.isTemplateExpression(n)) return n.head.text + n.templateSpans.map((s) => rendered(s.expression) + s.literal.text).join('');
  if (ts.isParenthesizedExpression(n)) return rendered(n.expression);
  if (ts.isBinaryExpression(n) && n.operatorToken.kind === ts.SyntaxKind.PlusToken) return rendered(n.left) + rendered(n.right);
  if (ts.isConditionalExpression(n)) return '';
  if (ts.isArrayLiteralExpression(n)) return n.elements.map(rendered).join('');
  if (ts.isCallExpression(n)) {
    const j = joined(n);
    if (j !== null) return j;
  }
  // a compiled JSX element: h("b", { children: … }) / jsx(…)
  if (ts.isCallExpression(n))
    for (const a of n.arguments)
      if (ts.isObjectLiteralExpression(a))
        for (const p of a.properties)
          if (ts.isPropertyAssignment(p) && (ts.isIdentifier(p.name) || ts.isStringLiteral(p.name)) && p.name.text === 'children')
            return rendered(p.initializer);
  if (ts.isJsxElement(n) || ts.isJsxFragment(n)) return n.children.map(rendered).join('');
  if (ts.isJsxText(n)) return n.text.replace(/\s+/g, ' ');
  if (ts.isJsxExpression(n)) return n.expression ? rendered(n.expression) : '';
  return '';
}

/**
 * Every string in a script (literals and the parts of template literals), as TypeScript reads it; and (S20) the text
 * that strings render together: an array of JSX children, a template literal with its parts joined, "a" + "b", a
 * JSX element's children; (S22) an array's `.join(sep)` and a string's `.concat(…)`. A string that is HTML is read as
 * a page; one that is JSON, as JSON.
 */
export function codeStrings(code: string, file: string): string[] {
  const kind = file.endsWith('.ts')
    ? ts.ScriptKind.TS
    : file.endsWith('.tsx')
      ? ts.ScriptKind.TSX
      : file.endsWith('.jsx')
        ? ts.ScriptKind.JSX
        : ts.ScriptKind.JS;
  const sf = ts.createSourceFile(file, code, ts.ScriptTarget.Latest, true, kind);
  const out: string[] = [];
  const push = (t: string) => {
    if (!t.trim()) return;
    out.push(t);
    if (/<[a-z][\w-]*[\s>/]/i.test(t)) out.push(...htmlTexts(t));
    const s = t.trim();
    if ((s[0] === '{' && s.endsWith('}')) || (s[0] === '[' && s.endsWith(']'))) out.push(...jsonStrings(s).filter((x) => x !== s));
  };
  const visit = (n: ts.Node): void => {
    if (ts.isStringLiteralLike(n) || ts.isTemplateHead(n) || ts.isTemplateMiddle(n) || ts.isTemplateTail(n) || ts.isJsxText(n)) push(n.text);
    else if (ts.isTemplateExpression(n) || ts.isJsxElement(n) || ts.isJsxFragment(n)) push(rendered(n));
    else if (ts.isBinaryExpression(n) && n.operatorToken.kind === ts.SyntaxKind.PlusToken && !ts.isBinaryExpression(n.parent)) push(rendered(n));
    else if (ts.isArrayLiteralExpression(n) && n.elements.length > 1) push(rendered(n));
    else if (ts.isCallExpression(n) && joined(n) !== null) push(rendered(n));
    n.forEachChild(visit);
  };
  visit(sf);
  return out;
}

/** a file's text the way its reader gets it: a page, a script, a stylesheet, JSON, or plain text; null for a binary */
const BINARY = /\.(?:woff2?|ttf|otf|eot|png|jpe?g|gif|webp|avif|ico|bmp|mp4|webm|mov|mp3|ogg|wav|pdf|zip|gz|br|wasm|bin)$/i;
export function fileTexts(path: string): string[] | null {
  if (BINARY.test(path)) return null;
  const text = readFileSync(path, 'utf8');
  const ext = extname(path).toLowerCase();
  if (ext === '.html' || ext === '.htm' || ext === '.svg' || ext === '.xml') return htmlTexts(text);
  if (ext === '.js' || ext === '.mjs' || ext === '.cjs') return codeStrings(text, path);
  if (ext === '.css') return cssStrings(text);
  if (ext === '.json' || ext === '.webmanifest') return jsonStrings(text);
  return text.split('\n');
}

/** a script's name in a text: "assets/x.js", "./x.js", "/x.js", "https://cdn…/assets/x.js" */
const SCRIPT_REF = /(?:^|["'`(\s/=])([\w.-]+\.m?js)(?=["'`)\s?#]|$)/g;

/**
 * Which scripts in the build the pages load (statically, lazily, by any URL), and which only the review pages load.
 * S20 (QA ת60): every script anywhere in the build is scanned but those only the review pages (dist/test) reach.
 */
export function scriptsOf(
  dist: string,
  customerPages: string[],
  reviewPages: string[],
): { loaded: Set<string>; reviewOnly: string[]; unreferenced: string[]; all: string[] } {
  const all = walk(dist, (r) => /\.m?js$/.test(r)).map((p) => relative(dist, p).split('\\').join('/'));
  const byName = new Map<string, string[]>();
  for (const f of all) byName.set(f.split('/').pop()!, [...(byName.get(f.split('/').pop()!) ?? []), f]);
  const refs = (text: string): string[] => [...text.matchAll(SCRIPT_REF)].flatMap((m) => byName.get(m[1]!) ?? []);
  const reach = (pages: string[]): Set<string> => {
    const seen = new Set<string>();
    const stack = pages.flatMap((p) => refs(readFileSync(p, 'utf8')));
    while (stack.length) {
      const f = stack.pop()!;
      if (seen.has(f)) continue;
      seen.add(f);
      stack.push(...refs(readFileSync(join(dist, f), 'utf8')).filter((x) => !seen.has(x)));
    }
    return seen;
  };
  const loaded = reach(customerPages);
  const review = reach(reviewPages);
  return {
    loaded,
    reviewOnly: all.filter((f) => review.has(f) && !loaded.has(f)),
    unreferenced: all.filter((f) => !review.has(f) && !loaded.has(f)),
    all,
  };
}

/** @deprecated S18's name: the scripts the pages load (see scriptsOf) */
export function loadedChunks(dist: string, pages: string[]): { loaded: Set<string>; all: string[] } {
  const { loaded, all } = scriptsOf(dist, pages, []);
  return { loaded, all };
}

/**
 * S20 (QA ת60): the Worker's customer strings: api/src (.ts, .tsx, .json) but the owner's, and every module of
 * shared/src those import (`@hd/shared`, `@hd/shared/<name>`, and theirs in turn): ORDER_STATUS_HE is served as `status_he`.
 */
export function workerSources(api: string, shared: string): string[] {
  const own = walk(api, (r) => /\.(?:tsx?|json)$/.test(r) && !OWNER_ONLY.includes(r));
  const out = new Set(own);
  const stack = own.filter((f) => /\.tsx?$/.test(f));
  const seen = new Set<string>();
  while (stack.length) {
    const f = stack.pop()!;
    if (seen.has(f)) continue;
    seen.add(f);
    const code = readFileSync(f, 'utf8');
    for (const m of code.matchAll(/(?:from|import)\s*\(?\s*['"]([^'"]+)['"]/g)) {
      const spec = m[1]!;
      let target: string | null = null;
      if (spec === '@hd/shared') target = join(shared, 'index.ts');
      else if (spec.startsWith('@hd/shared/')) target = join(shared, `${spec.slice(11)}.ts`);
      else if (spec.startsWith('.') && f.startsWith(shared)) target = resolve(dirname(f), spec.endsWith('.ts') ? spec : `${spec}.ts`);
      if (target && !existsSync(target) && existsSync(target.replace(/\.ts$/, '/index.ts'))) target = target.replace(/\.ts$/, '/index.ts');
      if (target && existsSync(target) && !out.has(target)) {
        out.add(target);
        stack.push(target);
      }
    }
  }
  return [...out];
}
