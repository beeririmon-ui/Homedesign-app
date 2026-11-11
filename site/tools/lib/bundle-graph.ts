/**
 * S16, QA ת44: what the room's entry carries, by content. The web build (web/vite.config.ts, `bundleGraph`) writes
 * `.generated/bundle-graph.json`: every chunk of the client build with the modules whose code it carries (rendered,
 * not tree-shaken away), its static imports and its dynamic imports. The guard follows the entry's static imports and
 * fails when any of them carries a page that must be its own chunk, whatever the chunk is called: QA's mutation (the
 * order page imported statically, so its code sat in the entry under the entry's own name) is caught here.
 */
import { existsSync, readFileSync } from 'node:fs';
import { sitePath } from './paths';

export type BundleGraph = {
  chunks: Record<string, { isEntry: boolean; imports: string[]; dynamicImports: string[]; modules: string[] }>;
};

/** the pages off the room's first paint (web/src/pages/lazy.tsx) */
export const LAZY_PAGES = ['Order', 'Checkout', 'Cart', 'Product', 'Legal', 'MockPay'] as const;
const LAZY_MODULE = new RegExp(`(?:^|/)src/pages/(${LAZY_PAGES.join('|')})\\.tsx$`);

export const GRAPH_FILE = sitePath('.generated/bundle-graph.json');

export function readGraph(file = GRAPH_FILE): BundleGraph | null {
  return existsSync(file) ? (JSON.parse(readFileSync(file, 'utf8')) as BundleGraph) : null;
}

/** the chunks the browser loads with the entry: the given files and everything they import statically */
export function staticClosure(graph: BundleGraph, entryFiles: string[]): Set<string> {
  const seen = new Set<string>();
  const stack = entryFiles.filter((f) => graph.chunks[f]);
  while (stack.length) {
    const f = stack.pop()!;
    if (seen.has(f)) continue;
    seen.add(f);
    for (const i of graph.chunks[f]?.imports ?? []) if (!seen.has(i)) stack.push(i);
  }
  return seen;
}

/** every lazy page whose code is in the entry's closure, as "Page (in chunk)" */
export function lazyPagesInEntry(graph: BundleGraph, entryFiles: string[]): string[] {
  const out: string[] = [];
  for (const f of staticClosure(graph, entryFiles))
    for (const m of graph.chunks[f]!.modules) {
      const hit = LAZY_MODULE.exec(m);
      if (hit) out.push(`${hit[1]} (in ${f})`);
    }
  return out.sort();
}

/** each lazy page has its code somewhere in the build (a chunk of its own): a renamed or removed page is noticed */
export function lazyPagesMissing(graph: BundleGraph): string[] {
  const all = Object.values(graph.chunks).flatMap((c) => c.modules);
  return LAZY_PAGES.filter((p) => !all.some((m) => m.endsWith(`src/pages/${p}.tsx`)));
}
