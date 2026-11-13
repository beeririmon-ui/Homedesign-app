/**
 * S15, master-designer's copy for the set panel (docs/proposals/your-room-copy-2026-11-11.md §2): the words of a set's
 * panel, apart from its data so they can be checked on their own (web/test/s15-copy.test.ts).
 */

/** §2 row 4: the wheel's line above its heading, in a house whose options are sets ("3 סטים"), else "3 גרסאות" (§5) */
export const wheelCountHe = (n: number, sets: boolean): string => (n === 1 ? (sets ? 'סט אחד' : 'גרסה אחת') : `${n} ${sets ? 'סטים' : 'גרסאות'}`);

/** §2 row 6: the list of a set's pieces, as a screen reader names it */
export const setItemsLabelHe = (n: number): string => `בסט ${n} פריטים`;

/** §2 rows 10, 11: the pieces not sold now; the piece's own row already says "המלאי אינו זמין כעת" */
export function setNoteHe(missing: number): string {
  return missing === 1 ? 'פריט אחד מהסט אינו זמין כעת, ולכן הסט נכנס לסל בלעדיו.' : `${missing} פריטים מהסט אינם זמינים כעת, ולכן הסט נכנס לסל בלעדיהם.`;
}

/** §2 rows 12, 13: the set's button, whole or without the pieces not sold now (the price follows it) */
export const setButtonHe = (forSale: number, all: number): string => (forSale === all ? 'הסט כולו לסל' : `הסט לסל, ${forSale} מתוך ${all} פריטים`);

/** §2 row 7: a piece with no price is not sold ("בלי מחיר" reads as free) */
export const NOT_FOR_SALE_HE = 'עוד לא במכירה';
