/**
 * Tiny router. Site: History API with prerendered pages. Artifact: in-memory (no URL changes, no hash state).
 */
import { signal } from '@preact/signals';

export const MEMORY = __ARTIFACT__;
export const path = signal<string>(typeof location !== 'undefined' && !MEMORY ? location.pathname + location.search : '/');

function normalise(to: string): string {
  return to.startsWith('/') ? to : `/${to}`;
}

export function navigate(to: string, opts: { replace?: boolean } = {}): void {
  const next = normalise(to);
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

/** Same-origin link clicks become client navigations (modifier keys and new tabs keep the browser default). */
export function onLinkClick(e: MouseEvent): void {
  if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  const a = (e.target as Element | null)?.closest?.('a');
  if (!a || a.target || a.hasAttribute('download') || a.getAttribute('rel') === 'external') return;
  const href = a.getAttribute('href');
  if (!href || !href.startsWith('/') || href.startsWith('//')) return;
  e.preventDefault();
  navigate(href);
}

export type Route =
  | { name: 'home' }
  | { name: 'room'; room: string; slot?: string; option?: number }
  | { name: 'product'; id: string }
  | { name: 'cart' }
  | { name: 'checkout'; failed: boolean }
  | { name: 'order'; id: string }
  | { name: 'mock-pay'; session: string }
  | { name: 'legal'; page: 'accessibility' | 'terms' | 'privacy' | 'returns' }
  | { name: 'not-found' };

export function match(full: string): Route {
  const [p = '/', query = ''] = full.split('?');
  const q = new URLSearchParams(query);
  const seg = p.replace(/\/+$/, '').split('/').filter(Boolean).map(decodeURIComponent);
  if (seg.length === 0) return { name: 'home' };
  if (seg[0] === 'rooms' && seg[1]) {
    const opt = Number(q.get('option'));
    return { name: 'room', room: seg[1], slot: q.get('slot') ?? undefined, option: Number.isInteger(opt) && opt > 0 ? opt : undefined };
  }
  if (seg[0] === 'p' && seg[1]) return { name: 'product', id: seg[1] };
  if (seg[0] === 'cart') return { name: 'cart' };
  if (seg[0] === 'checkout') return { name: 'checkout', failed: q.has('failed') || q.has('canceled') };
  if (seg[0] === 'order' && seg[1]) return { name: 'order', id: seg[1] };
  if (seg[0] === 'mock-pay' && seg[1]) return { name: 'mock-pay', session: seg[1] };
  if (seg.length === 1 && (['accessibility', 'terms', 'privacy', 'returns'] as const).includes(seg[0] as 'terms'))
    return { name: 'legal', page: seg[0] as 'accessibility' };
  return { name: 'not-found' };
}
