/**
 * qa-agent, 2026-11-07 (S3-S5): the neutral product addresses, independently of the build.
 *  - every product card id in data/products (the ids the build may meet) through productSlug: unique? any supplier or
 *    marketplace name (also inside a word), any run of 4+ digits, any short id that is all digits?
 *  - QA's snapshot: _redirects (rows, duplicates, chains, each target = productSlug of its source), and every product
 *    link in the built HTML: neutral, and no old address left
 *   cd site && npx tsx ../qa/reports/2026-11-07-site-track-qa-s3-s5/tools/scan-urls.ts <dist> <out.json>
 */
import { readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { productSlug, shortIdOf } from '../../../../site/shared/src/product-url.ts';

const DIST = process.argv[2]!;
const OUT = process.argv[3]!;
const walk = (d: string, f: (p: string) => void) => {
  for (const n of readdirSync(d)) {
    const p = join(d, n);
    if (statSync(p).isDirectory()) walk(p, f);
    else f(p);
  }
};
const ids = new Set<string>();
walk('/home/user/homedesign-app/data/products', (p) => {
  if (!p.endsWith('.json')) return;
  try {
    const j = JSON.parse(readFileSync(p, 'utf8'));
    if (typeof j.id === 'string') ids.add(j.id);
  } catch {
    /* not a card */
  }
});
const SUPPLIER_RX = /(aliexpress|cjdropshipping|zendrop|temu|alibaba|amazon|etsy|spocket|dsers|(^|-)cj(-|$)|(^|-)ae(-|$))/;
const slugs = new Map<string, string[]>();
const bad: { id: string; slug: string; why: string }[] = [];
for (const id of ids) {
  const s = productSlug(id);
  slugs.set(s, [...(slugs.get(s) ?? []), id]);
  const words = s.split('-').slice(0, -1).join('-');
  if (SUPPLIER_RX.test(words)) bad.push({ id, slug: s, why: 'supplier name' });
  if (/\d{4,}/.test(words)) bad.push({ id, slug: s, why: '4+ digits in the words' });
  if (/^\d{5}$/.test(shortIdOf(s) ?? '')) bad.push({ id, slug: s, why: 'short id all digits' });
}
const collisions = [...slugs.entries()].filter(([, v]) => v.length > 1);
// _redirects
const rows = readFileSync(join(DIST, '_redirects'), 'utf8')
  .split('\n')
  .filter((l) => l.trim() && !l.startsWith('#'))
  .map((l) => l.trim().split(/\s+/));
const red = rows.map(([from, to, code]) => {
  const m = /^(\/story\/[^/]+\/[^/]+)?\/p\/([^/]+)\/$/.exec(from!);
  const want = m ? `${m[1] ?? ''}/p/${productSlug(m[2]!)}/` : null;
  return { from, to, code, target_is_slug_of_source: to === want, source_is_old_id: m ? ids.has(m[2]!) : false };
});
const froms = red.map((r) => r.from);
const tos = new Set(red.map((r) => r.to));
// every product link in the built HTML
const links: { file: string; href: string }[] = [];
walk(DIST, (p) => {
  if (!p.endsWith('.html')) return;
  const t = readFileSync(p, 'utf8');
  for (const m of t.matchAll(/href="([^"]*\/p\/[^"]+)"/g)) links.push({ file: p.replace(DIST, ''), href: m[1]! });
});
const oldLinks = links.filter((l) => {
  const seg = /\/p\/([^/?#]+)/.exec(l.href)?.[1];
  return seg ? ids.has(seg) : false;
});
const linkSupplier = links.filter((l) => SUPPLIER_RX.test(l.href.replace(/-[0-9a-z]{5}\/?(\?.*)?$/, '')) || /\d{4,}/.test(l.href.replace(/-[0-9a-z]{5}\/?(\?.*)?$/, '')));
// the page folders themselves
const pageDirs: string[] = [];
walk(DIST, (p) => {
  const m = /\/p\/([^/]+)\/index\.html$/.exec(p);
  if (m) pageDirs.push(p.replace(DIST, ''));
});
const dirBad = pageDirs.filter((p) => SUPPLIER_RX.test(p.replace(/-[0-9a-z]{5}\/index\.html$/, '')) || /\d{4,}/.test(p.replace(/-[0-9a-z]{5}\/index\.html$/, '')));
const res = {
  cards: ids.size,
  unique_slugs: slugs.size,
  collisions,
  bad_slugs: bad,
  redirects: {
    rows: red.length,
    shop: red.filter((r) => r.from!.startsWith('/p/')).length,
    story: red.filter((r) => r.from!.startsWith('/story/')).length,
    codes: [...new Set(red.map((r) => r.code))],
    duplicate_sources: froms.filter((f, i) => froms.indexOf(f) !== i),
    chains: red.filter((r) => froms.includes(r.to!)).map((r) => r.from),
    target_not_slug_of_source: red.filter((r) => !r.target_is_slug_of_source),
    source_not_a_card_id: red.filter((r) => !r.source_is_old_id).map((r) => r.from),
    distinct_targets: tos.size,
  },
  html_product_links: links.length,
  html_old_links: oldLinks.slice(0, 20),
  html_links_with_supplier_or_number: linkSupplier.slice(0, 20),
  product_page_dirs: pageDirs.length,
  product_page_dirs_bad: dirBad,
};
writeFileSync(OUT, JSON.stringify({ ...res, redirect_rows: red }, null, 1));
console.log(JSON.stringify(res, null, 1));
