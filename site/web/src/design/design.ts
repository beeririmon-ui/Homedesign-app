/**
 * FB13 (2026-11-25): three design directions for the site and the tour, behind a flag, so the owner can choose
 * (docs/proposals/site-fb13-design-directions-2026-11-25.md):
 *   a  "גיליון": editorial — the tour as a magazine issue: a big serif, paper margins, numbered captions;
 *   b  "סורק": high-tech — a precise instrument: frosted glass, hairlines, reticles, data in a mono face;
 *   c  "הקרנה": the hybrid — a screening room: a dark stage round the picture, a serif title, mono data.
 *
 * `?design=a|b|c` picks one for this tab (kept in sessionStorage, so the cart and the product page wear it too);
 * `?design=0` goes back to the current look. Without the flag the page has no attribute and loads none of these
 * stylesheets: the default look is unchanged. A public build (HD_PUBLIC=1) has none of it (__TOUR__ folds it away).
 */
export type Design = 'a' | 'b' | 'c';
export const DESIGNS = ['a', 'b', 'c'] as const satisfies readonly Design[];
const KEY = 'hd-design';
const isDesign = (v: string | null): v is Design => DESIGNS.includes(v as Design);

function read(): Design | null {
  if (typeof __TOUR__ === 'undefined' || !__TOUR__ || typeof location === 'undefined') return null;
  const q = new URLSearchParams(location.search).get('design');
  try {
    if (q === '0') {
      sessionStorage.removeItem(KEY);
      return null;
    }
    if (isDesign(q)) {
      sessionStorage.setItem(KEY, q);
      return q;
    }
    const kept = sessionStorage.getItem(KEY);
    return isDesign(kept) ? kept : null;
  } catch {
    // no storage (a private window, blocked site data): the flag holds for this page only
    return isDesign(q) ? q : null;
  }
}

/** the direction this tab wears, or null (the current look). Read once, when the page starts. */
export const design: Design | null = read();

const sheets: Record<Design, () => Promise<unknown>> = {
  a: () => import('./a.css'),
  b: () => import('./b.css'),
  c: () => import('./c.css'),
};

/** main.tsx, once: the attribute every stylesheet of the direction is scoped by, and that direction's stylesheet */
export function applyDesign(): void {
  if (!design) return;
  document.documentElement.dataset.design = design;
  void sheets[design]();
}
