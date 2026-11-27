/**
 * MOCK9 (2026-11-27, FB19): the wordmark. There is no brand name yet (ART5): "הבית" is the placeholder, and the name is
 * swapped here, in one place — the header, the logo intro (design/intro.ts) and the tests read it from BRAND_HE.
 */
export const BRAND_HE = 'הבית';

export function Wordmark() {
  return <span class="wordmark">{BRAND_HE}</span>;
}
