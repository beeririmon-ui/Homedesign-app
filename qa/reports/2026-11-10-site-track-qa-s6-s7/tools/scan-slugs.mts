/**
 * qa-agent, 2026-11-10 (S6-S7): every card id through publicId / productSlug of the build under test: unique? a
 * supplier word, a run of 4+ digits inside any word, a size (NNxNN, dNN, hNN, NNcm) left in the words?
 *   cd <site copy> && npx tsx <this> <data dir> <out.json>
 */
import { readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
const shared = await import(join(process.cwd(), 'shared/src/product-url.ts'));
const DATA = process.argv[2]!;
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
const slugOf = (shared.publicId ?? shared.productSlug) as (id: string) => string;
const by = new Map<string, string[]>();
const bad: { id: string; slug: string; why: string }[] = [];
for (const id of ids) {
  const s = slugOf(id);
  by.set(s, [...(by.get(s) ?? []), id]);
  const words = s.replace(/-[0-9a-z]{5}$/, '');
  if (/(^|-)(cj|ae|aliexpress|zendrop|cjdropshipping|temu|alibaba|amazon|etsy|spocket|dsers)(-|$)/.test(words)) bad.push({ id, slug: s, why: 'supplier word' });
  if (/\d{4,}/.test(words)) bad.push({ id, slug: s, why: '4+ digits in a word' });
  if (/(^|-)(\d+x\d+(x\d+)?|[dh]\d{2,3}|\d+(cm|mm))(-|$)/.test(words)) bad.push({ id, slug: s, why: 'a size' });
}
const res = { cards: ids.size, slugs: by.size, collisions: [...by].filter(([, v]) => v.length > 1), bad };
writeFileSync(process.argv[3]!, JSON.stringify(res, null, 1));
console.log(JSON.stringify({ cards: res.cards, slugs: res.slugs, collisions: res.collisions.length, bad_count: bad.length, by_reason: bad.reduce((m: Record<string, number>, b) => ((m[b.why] = (m[b.why] ?? 0) + 1), m), {}), examples: bad.slice(0, 8) }, null, 1));
