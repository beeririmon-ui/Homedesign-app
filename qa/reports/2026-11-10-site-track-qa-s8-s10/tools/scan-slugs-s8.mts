/**
 * qa-agent, 2026-11-10 (S8, the slug rule): every product card id through the build's productSlug / publicId (b0a71cd2):
 * unique? a supplier word? any word with a digit before the short id (the owner's rule: no size, no model code, no
 * number)? the short id itself is the only part allowed to carry digits. Then the addresses the site serves: every
 * /p/<slug>/ and /story/<room>/<style>/p/<slug>/ in dist, and every line of dist/_redirects (old → new, 301, the target a
 * page that exists). Also: the S7 slugs that carried a size, and what they answer now.
 *   cd <copy>/site && npx tsx <this> <data dir> <dist dir> <s7 scan json> <out.json>
 */
import { existsSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const shared = await import(join(process.cwd(), 'shared/src/product-url.ts'));
const [DATA, DIST, S7, OUT] = process.argv.slice(2) as [string, string, string, string];
const SUPPLIERS = /(^|-)(cj|ae|aliexpress|zendrop|cjdropshipping|temu|alibaba|amazon|etsy|spocket|dsers|1688)(-|$)/;
const ids = new Set<string>();
const walk = (d: string) => {
  for (const n of readdirSync(d)) {
    const p = join(d, n);
    if (statSync(p).isDirectory()) walk(p);
    else if (p.endsWith('.json')) {
      try {
        const j = JSON.parse(readFileSync(p, 'utf8'));
        if (typeof j.id === 'string') ids.add(j.id);
      } catch {}
    }
  }
};
walk(join(DATA, 'products'));
const by = new Map<string, string[]>();
const bad: { id: string; slug: string; why: string }[] = [];
for (const id of ids) {
  const s = shared.publicId(id) as string;
  by.set(s, [...(by.get(s) ?? []), id]);
  const sid = shared.shortIdOf(s) as string | null;
  if (!sid || sid !== shared.shortId(id)) bad.push({ id, slug: s, why: 'no short id at the end' });
  const words = s.slice(0, -6).split('-');
  if (SUPPLIERS.test(words.join('-'))) bad.push({ id, slug: s, why: 'supplier word' });
  for (const w of words) if (/\d/.test(w)) bad.push({ id, slug: s, why: `a word with a digit: ${w}` });
  if (words.length > 6) bad.push({ id, slug: s, why: 'more than 6 words' });
}
// the addresses in dist
const pages: string[] = [];
const walkDist = (d: string, rel = '') => {
  for (const n of readdirSync(d)) {
    const p = join(d, n);
    if (statSync(p).isDirectory()) walkDist(p, `${rel}/${n}`);
    else if (n === 'index.html' && /\/p\/[^/]+$/.test(rel)) pages.push(`${rel}/`);
  }
};
walkDist(DIST);
const slugOfPage = (u: string) => u.split('/').at(-2)!;
const pageBad = pages.filter((u) => slugOfPage(u).slice(0, -6).split('-').some((w) => /\d/.test(w)) || SUPPLIERS.test(slugOfPage(u)));
// _redirects
const lines = readFileSync(join(DIST, '_redirects'), 'utf8').split('\n').filter((l) => l.trim() && !l.startsWith('#'));
const redirects = lines.map((l) => {
  const [from, to, code] = l.trim().split(/\s+/);
  const target = to!.split('?')[0]!;
  const exists = existsSync(join(DIST, target, 'index.html')) || target === '/rooms/living-room/';
  return { from: from!, to: to!, code: Number(code), target_exists: exists, to_has_digit_word: /\/p\//.test(to!) ? slugOfPage(to!).slice(0, -6).split('-').some((w) => /\d/.test(w)) : false };
});
// the S7 slugs with a size (QA S6-S7, data/scan-slugs.json): what they are now
const s7 = existsSync(S7) ? (JSON.parse(readFileSync(S7, 'utf8')) as { bad: { id: string; slug: string; why: string }[] }).bad.filter((b) => b.why === 'a size') : [];
const s7now = s7.map((b) => ({ old: b.slug, now: shared.publicId(b.id), page_now: pages.some((u) => u.endsWith(`/p/${shared.publicId(b.id)}/`)), old_redirected: redirects.some((r) => r.from.endsWith(`/p/${b.slug}/`)) }));
const res = {
  cards: ids.size,
  slugs: by.size,
  collisions: [...by].filter(([, v]) => v.length > 1),
  bad,
  dist_product_pages: pages.length,
  dist_pages_bad: pageBad,
  redirects: { lines: redirects.length, by_code: redirects.reduce((m: Record<string, number>, r) => ((m[r.code] = (m[r.code] ?? 0) + 1), m), {}), target_missing: redirects.filter((r) => !r.target_exists), to_with_digit_word: redirects.filter((r) => r.to_has_digit_word), all: redirects },
  s7_sized_slugs: { count: s7.length, old_redirected: s7now.filter((x) => x.old_redirected).length, items: s7now },
};
writeFileSync(OUT, JSON.stringify(res, null, 1));
console.log(JSON.stringify({ cards: res.cards, slugs: res.slugs, collisions: res.collisions.length, bad: bad.length, bad_examples: bad.slice(0, 6), dist_product_pages: pages.length, dist_pages_bad: pageBad.length, redirects: { lines: redirects.length, by_code: res.redirects.by_code, target_missing: res.redirects.target_missing.length, to_with_digit_word: res.redirects.to_with_digit_word.length }, s7_sized: { count: s7.length, old_redirected: res.s7_sized_slugs.old_redirected, example: s7now.slice(0, 3) } }, null, 1));
