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
 *
 * MOCK7 (2026-11-26, briefs/site-mock7-tour-transitions-2026-11-26.md, FB17): C is the preview's default look (the
 * recommendation; the owner can switch). `?design=a|b|c` still picks one, and `?design=0` the look before FB13 — both
 * kept for the tab. The public build is unchanged (no attribute, no stylesheet).
 */
export type Design = 'a' | 'b' | 'c';
export const DESIGNS = ['a', 'b', 'c'] as const satisfies readonly Design[];
const KEY = 'hd-design';
const isDesign = (v: string | null): v is Design => DESIGNS.includes(v as Design);
/** MOCK7: the preview's look without a flag */
export const DEFAULT_DESIGN: Design = 'c';

function read(): Design | null {
  if (typeof __TOUR__ === 'undefined' || !__TOUR__ || typeof location === 'undefined') return null;
  const q = new URLSearchParams(location.search).get('design');
  try {
    if (q === '0' || isDesign(q)) {
      sessionStorage.setItem(KEY, q);
      return q === '0' ? null : q;
    }
    const kept = sessionStorage.getItem(KEY);
    return kept === '0' ? null : isDesign(kept) ? kept : DEFAULT_DESIGN;
  } catch {
    // no storage (a private window, blocked site data): the flag holds for this page only
    return q === '0' ? null : isDesign(q) ? q : DEFAULT_DESIGN;
  }
}

/** the direction this tab wears, or null (the current look). Read once, when the page starts. */
export const design: Design | null = read();

const sheets: Record<Design, () => Promise<unknown>> = {
  a: () => import('./a.css'),
  b: () => import('./b.css'),
  c: () => import('./c.css'),
};

/**
 * main.tsx, once: the attribute every stylesheet of the direction is scoped by, and that direction's stylesheet.
 * MOCK10 (FB26): the page waits for it before its first render, so the first frame is already the direction's (never
 * the paper look for a moment, then the night).
 */
export function applyDesign(): Promise<unknown> {
  if (!design) return Promise.resolve();
  document.documentElement.dataset.design = design;
  return sheets[design]().catch(() => undefined);
}
