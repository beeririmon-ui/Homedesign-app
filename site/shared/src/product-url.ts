/**
 * Neutral product addresses (S5, 2026-11-07): one place maps a card id to the slug the customer sees, for the shop
 * (/p/<slug>/) and the story's detail pages (/story/<room>/<style>/p/<slug>/).
 *
 * A card id names the supplier and its product number ("vase-aliexpress-vintage-distressed-clay-vase-589009"). The
 * slug keeps the words that say what the product is, drops the supplier and the long number, and ends in a short id
 * made from the whole card id, so two cards never share an address and a card keeps its address while it lives:
 * "vase-vintage-distressed-clay-vase-2k7qf". Pure and synchronous: the browser, the Worker and the tools all use it.
 */

/** supplier and marketplace names that never reach an address */
const SUPPLIERS = new Set(['cj', 'cjdropshipping', 'aliexpress', 'ae', 'zendrop', 'temu', 'alibaba', 'amazon', 'etsy', 'spocket', 'dsers']);
/** at most this many words before the short id */
const MAX_WORDS = 6;

/** FNV-1a, 32 bits: small, stable, the same in every runtime */
function fnv1a(s: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

/** the short stable id of a card: 5 characters, base 36 */
export function shortId(cardId: string): string {
  return fnv1a(cardId).toString(36).padStart(7, '0').slice(-5);
}

/** the words of a card id that say what the product is: no supplier, no word with 4 digits or more (a product number,
 * or a model code such as "g4483a", QA on S3–S5) */
export function slugWords(cardId: string): string[] {
  return cardId
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((w) => w && !SUPPLIERS.has(w) && !/\d{4,}/.test(w))
    .slice(0, MAX_WORDS);
}

/** the neutral slug of a card id */
export function productSlug(cardId: string): string {
  const words = slugWords(cardId);
  return [...(words.length ? words : ['product']), shortId(cardId)].join('-');
}

/** the short id at the end of a slug, or null */
export function shortIdOf(slug: string): string | null {
  const m = /-([0-9a-z]{5})$/.exec(slug);
  return m ? m[1]! : null;
}

/** the shop's address of a product */
export const productPath = (cardId: string): string => `/p/${productSlug(cardId)}/`;

/**
 * A lookup from an address segment to a card id: the slug, or (an old address) the card id itself. Throws when two
 * cards would share a slug, so a build fails before an address does.
 */
export function slugIndex(cardIds: Iterable<string>): { resolve: (segment: string) => { id: string; old: boolean } | null; slugOf: (id: string) => string } {
  const bySlug = new Map<string, string>();
  const ids = new Set<string>();
  for (const id of cardIds) {
    ids.add(id);
    const slug = productSlug(id);
    const was = bySlug.get(slug);
    if (was && was !== id) throw new Error(`two products share the address ${slug}: ${was} and ${id}`);
    bySlug.set(slug, id);
  }
  return {
    resolve: (segment) => {
      const bySl = bySlug.get(segment);
      if (bySl) return { id: bySl, old: false };
      return ids.has(segment) ? { id: segment, old: true } : null;
    },
    slugOf: productSlug,
  };
}
