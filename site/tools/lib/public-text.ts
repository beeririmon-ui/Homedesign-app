/**
 * S14, QA ת33: what the customer reads about a product is the shop's Hebrew, never the studio's notes.
 *
 * - **Never public:** the card's `notes` (sourcing's working notes) are not read by the public description at all; the
 *   card's `texture` is a public sentence only when it reads as one: Hebrew, no Latin, and no sourcing remark (what the
 *   photos show, another version in the listing, a doubt). Otherwise the description is built from the card's data alone
 *   (materials, dimensions), or is the slot's name.
 * - **The build check:** a public name, description or product note with Latin letters fails the build. The only Latin
 *   allowed is a unit after a number (3000K, 90-260V, 5W, 220mm) and a standard's mark (CE, UL, IP44), as in ת12.
 */

/** Latin letters left once a unit after a number and a standard's mark are taken out. */
export function hasLatinText(s: string): boolean {
  const rest = s
    .replace(/\d+(?:[.,]\d+)?(?:\s*[-–~]\s*\d+(?:[.,]\d+)?)?\s*(?:K|V|W|Hz|mAh|mm|cm|lm)\b/g, '')
    .replace(/\b(?:CE|UL|ETL|FCC|RoHS|IP\d{2})\b/g, '');
  return /[A-Za-z]/.test(rest);
}

const HEBREW = /[\u0590-\u05FF]/;
/** a sourcing remark, not a description: what the photos show, the listing, a doubt, a recommendation */
const REMARK = /בתמונות|ליסטינג|ספק|לא ודאי|לא ברור|לבדוק|מומלץ|\?/;

/** The card's texture as a public sentence, or null when it is not one (ת33). */
export function publicTexture(texture: string | null | undefined): string | null {
  const t = texture?.trim();
  if (!t || !HEBREW.test(t) || hasLatinText(t) || REMARK.test(t)) return null;
  return t.replace(/[.\s]+$/, '');
}

/**
 * The product's public description, from the card's data only: its texture when that is a public sentence, its
 * materials (already in Hebrew) and its dimensions as the supplier states them. Never the card's notes.
 */
export function publicDescription(card: { texture?: string | null }, materialsHe: string[], dims: number[], fallback: string): string {
  const texture = publicTexture(card.texture);
  const text = [
    texture ? `${texture}.` : null,
    materialsHe.length ? `חומרים: ${materialsHe.join(', ')}.` : null,
    dims.length ? `מידות: ${dims.join(' × ')} ס"מ (לפי הספק, לא אומת).` : null,
  ]
    .filter(Boolean)
    .join(' ');
  return text || fallback;
}

type PublicTextProduct = { id: string; name_he: string; description_he: string; notes_he?: string[]; materials_he?: string[] };
export type TextIssue = { product: string; where: string; text: string };

/** Every public name, description and product note with Latin in it: the build check of ת33. */
export function latinPublicText(products: PublicTextProduct[]): TextIssue[] {
  const out: TextIssue[] = [];
  for (const p of products) {
    if (hasLatinText(p.name_he)) out.push({ product: p.id, where: 'name', text: p.name_he });
    if (hasLatinText(p.description_he)) out.push({ product: p.id, where: 'description', text: p.description_he });
    for (const n of p.notes_he ?? []) if (hasLatinText(n)) out.push({ product: p.id, where: 'note', text: n });
  }
  return out;
}

/**
 * S17, QA ה5: a field whose value is unknown is not shown. Every public name, description, material and note that
 * says a value is unknown ("לא צוין", "לא ידוע"…): the build check.
 */
const SAYS_UNKNOWN = /לא\s+(?:צוין|מצוין|צויין|ידוע|ידועה|הוגדר)|אינו\s+ידוע|\bunknown\b|\bnot stated\b|\bunspecified\b/i;
export function unknownPublicText(products: PublicTextProduct[]): TextIssue[] {
  const out: TextIssue[] = [];
  for (const p of products) {
    if (SAYS_UNKNOWN.test(p.name_he)) out.push({ product: p.id, where: 'name', text: p.name_he });
    if (SAYS_UNKNOWN.test(p.description_he)) out.push({ product: p.id, where: 'description', text: p.description_he });
    for (const m of p.materials_he ?? []) if (SAYS_UNKNOWN.test(m)) out.push({ product: p.id, where: 'material', text: m });
    for (const n of p.notes_he ?? []) if (SAYS_UNKNOWN.test(n)) out.push({ product: p.id, where: 'note', text: n });
  }
  return out;
}
