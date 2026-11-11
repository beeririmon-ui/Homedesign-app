/**
 * S11, QA S6–S7 ת8 and ת11: how a line is named, and how a cart says it lost one. The same words on the server (the
 * order's snapshot, the invoice), in the shop's pages and in the story's cart.
 */

/** The line rule (manager's decision, ת8): the base name without a colour · the option's Hebrew labels. */
export const lineName = (base: string, label: string | null | undefined): string => (label ? `${base} · ${label}` : base);

/**
 * S15: a line's name split back into its base name and its labels, at the first " · " (an order keeps only the joined
 * name, api/src/routes/public.ts). "החדר שלך" names a piece by its base name, and says "the option" only when it has one.
 */
export function splitLineName(name: string): { base: string; label: string } {
  const i = name.indexOf(' · ');
  return i < 0 ? { base: name, label: '' } : { base: name.slice(0, i), label: name.slice(i + 3) };
}

/** ת11: lines that stopped being sold after they were added, removed and never charged ("פריט אחד כבר לא זמין והוסר"). */
export function removedHe(n: number): string {
  return n === 1 ? 'פריט אחד כבר לא זמין והוסר.' : `${n} פריטים כבר לא זמינים והוסרו.`;
}

/** ת11, the cart's quiet notice: removed, and not charged ("פריט אחד כבר לא זמין והוסר. הוא לא ייגבה.") */
export function removedNoteHe(n: number): string {
  return `${removedHe(n)} ${n === 1 ? 'הוא לא ייגבה.' : 'הם לא ייגבו.'}`;
}
