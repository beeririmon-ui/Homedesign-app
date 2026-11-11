/**
 * S15 (master-designer, docs/proposals/your-room-copy-2026-11-11.md §5): a page's meta description is cut where a
 * sentence ends, never in the middle of a word. The longest run of whole sentences that fits is kept; when even the
 * first sentence is longer than the limit, it is cut at the last space that fits, and an ellipsis says so.
 */
export const META_DESCRIPTION_MAX = 155;

export function metaDescription(text: string, max = META_DESCRIPTION_MAX): string {
  const t = text.replace(/\s+/g, ' ').trim();
  if (t.length <= max) return t;
  // a sentence ends at . ! or ? followed by a space (a number such as 1.5 or a size such as 40×60 is not an end)
  let end = -1;
  for (const m of t.matchAll(/[.!?](?= )/g)) {
    if (m.index + 1 > max) break;
    end = m.index + 1;
  }
  if (end > 0) return t.slice(0, end);
  // one long sentence: the last whole word that fits with the ellipsis
  const room = t.slice(0, max);
  const space = room.lastIndexOf(' ');
  const cut = (space > 0 ? room.slice(0, space) : room.slice(0, max - 1)).replace(/[\s,;:·–-]+$/, '');
  return `${cut}…`;
}
