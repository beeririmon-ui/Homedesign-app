/**
 * Tiny router. Site: History API with prerendered pages. Artifact: in-memory (no URL changes, no hash state).
 */
import { signal } from '@preact/signals';
import { loadsAsDocument } from '@hd/shared/analytics';

export const MEMORY = __ARTIFACT__;
/** MOCK1: the wow-tour mock-up is in this build (web/vite.config.ts: every build but the public one; not in a unit test) */
const TOUR = typeof __TOUR__ !== 'undefined' && __TOUR__;
/** MOCK1: the Artifact preview opens at the tour's door (its first screen); the site at the address asked for */
export const path = signal<string>(typeof location !== 'undefined' && !MEMORY ? location.pathname + location.search : TOUR ? '/tour/' : '/');

function normalise(to: string): string {
  return to.startsWith('/') ? to : `/${to}`;
}

/**
 * S21, QA ת63: what a full load to a page of its own waits for (state/cart.ts `leaveFor`: a cart write still on its
 * way). It returns the address to load, or a promise of it. S23 (QA ת72): the address is never changed on the way.
 * main.tsx sets it; until then the address is loaded as it is.
 */
type BeforeDocument = (href: string) => string | Promise<string>;
let beforeDocument: BeforeDocument | null = null;
export function setBeforeDocumentLoad(fn: BeforeDocument | null): void {
  beforeDocument = fn;
}
const documentFor = (href: string): string | Promise<string> => (beforeDocument ? beforeDocument(href) : href);
function loadDocument(href: string, to: string | Promise<string>, replace = false, busy?: Element): void {
  const go = (u: string) => (replace ? location.replace(u) : location.assign(u));
  if (typeof to === 'string') return go(to);
  // the link says it is on its way while the add before it lands (a slow network: up to a few seconds)
  busy?.setAttribute('aria-busy', 'true');
  void to.then(go, () => go(href));
}

export function navigate(to: string, opts: { replace?: boolean } = {}): void {
  const next = normalise(to);
  // S19, QA ת55: the cart, the checkout and the order page always load as their own document (no beacon, their own CSP)
  if (!MEMORY && typeof location !== 'undefined' && loadsAsDocument(next)) {
    loadDocument(next, documentFor(next), opts.replace);
    return;
  }
  if (!MEMORY && typeof history !== 'undefined') {
    if (opts.replace) history.replaceState(null, '', next);
    else history.pushState(null, '', next);
  }
  path.value = next;
  if (typeof window !== 'undefined') window.scrollTo({ top: 0 });
}

export function initRouter(): void {
  if (MEMORY) return;
  addEventListener('popstate', () => {
    path.value = location.pathname + location.search;
  });
}

/**
 * Same-origin link clicks become client navigations (modifier keys and new tabs keep the browser default).
 * S19, QA ת55: except a link to a page without the analytics beacon (the cart, the checkout, the order page): the
 * browser follows it, and the page loads as a document of its own.
 */
export function onLinkClick(e: MouseEvent): void {
  if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  const a = (e.target as Element | null)?.closest?.('a');
  if (!a || a.target || a.hasAttribute('download') || a.getAttribute('rel') === 'external') return;
  const href = a.getAttribute('href');
  if (!href || !href.startsWith('/') || href.startsWith('//')) return;
  if (!MEMORY && loadsAsDocument(href)) {
    // S21, QA ת63: the browser follows the link, unless a cart write is on its way
    const to = documentFor(href);
    if (to === href) return;
    e.preventDefault();
    loadDocument(href, to, false, a);
    return;
  }
  e.preventDefault();
  navigate(href);
}

export type Route =
  | { name: 'home' }
  | { name: 'room'; room: string; slot?: string; option?: number; style?: string }
  | { name: 'product'; id: string }
  | { name: 'cart' }
  | { name: 'checkout'; failed: boolean }
  | { name: 'order'; id: string }
  | { name: 'mock-pay'; session: string }
  | { name: 'legal'; page: 'accessibility' | 'terms' | 'privacy' | 'returns' }
  /** MOCK1: the wow-tour mock-up, behind HD_PUBLIC=0 (a public build has no such route) */
  | { name: 'tour' }
  | { name: 'not-found' };

export function match(full: string): Route {
  const [p = '/', query = ''] = full.split('?');
  const q = new URLSearchParams(query);
  const seg = p.replace(/\/+$/, '').split('/').filter(Boolean).map(decodeURIComponent);
  if (seg.length === 0) return { name: 'home' };
  if (seg[0] === 'rooms' && seg[1]) {
    const opt = Number(q.get('option'));
    // S10: ?style=<id> names the house shown (DIR2); the Nordic house without it
    const style = q.get('style');
    return {
      name: 'room',
      room: seg[1],
      slot: q.get('slot') ?? undefined,
      option: Number.isInteger(opt) && opt > 0 ? opt : undefined,
      style: style && /^[a-z-]+$/.test(style) ? style : undefined,
    };
  }
  if (seg[0] === 'p' && seg[1]) return { name: 'product', id: seg[1] };
  if (TOUR && seg[0] === 'tour' && seg.length === 1) return { name: 'tour' };
  if (seg[0] === 'cart') return { name: 'cart' };
  if (seg[0] === 'checkout') return { name: 'checkout', failed: q.has('failed') || q.has('canceled') };
  if (seg[0] === 'order' && seg[1]) return { name: 'order', id: seg[1] };
  if (seg[0] === 'mock-pay' && seg[1]) return { name: 'mock-pay', session: seg[1] };
  if (seg.length === 1 && (['accessibility', 'terms', 'privacy', 'returns'] as const).includes(seg[0] as 'terms'))
    return { name: 'legal', page: seg[0] as 'accessibility' };
  return { name: 'not-found' };
}
