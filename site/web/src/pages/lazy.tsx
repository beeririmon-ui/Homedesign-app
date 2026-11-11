/**
 * S13, the room's JS budget (S12 left it at 78.2/80 KB): the pages that are not on the room's first paint are chunks of
 * their own, loaded when their route is shown, or as soon as a link to them is pointed at or focused (main.tsx).
 *
 * - **Hydration is unchanged:** main.tsx loads the chunk of the page it is on before it hydrates, so the first client
 *   render is the prerendered markup, never a placeholder over it.
 * - **The prerender** (entry-server.tsx) registers every page up front: the server renders the full page, as before.
 * - **A client navigation** to a page not loaded yet shows the page's frame (`aria-busy`) for the moment the chunk takes.
 */
import { signal } from '@preact/signals';
import type { ComponentType, JSX } from 'preact';
import { useEffect } from 'preact/hooks';
import type { Route } from '../router';

export type LazyName = 'product' | 'cart' | 'checkout' | 'order' | 'mock-pay' | 'legal';

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- each page has its own props; the call sites are typed
type AnyPage = ComponentType<any>;
const ready = signal<Partial<Record<LazyName, AnyPage>>>({});
const loaders = new Map<LazyName, () => Promise<AnyPage>>();
const pending = new Map<LazyName, Promise<AnyPage | null>>();

/** Loads a page's chunk once (a failed load is retried on the next call). */
export function loadPage(name: LazyName): Promise<AnyPage | null> {
  const have = ready.value[name];
  if (have) return Promise.resolve(have);
  let p = pending.get(name);
  if (!p) {
    const load = loaders.get(name);
    if (!load) return Promise.resolve(null);
    p = load().then(
      (c) => ((ready.value = { ...ready.value, [name]: c }), c),
      () => (pending.delete(name), null),
    );
    pending.set(name, p);
  }
  return p;
}

/** A page component that renders the chunk's page once it is in, and the page's frame until then. */
export function lazyPage<P extends object>(name: LazyName, load: () => Promise<ComponentType<P>>): (props: P) => JSX.Element {
  loaders.set(name, load as () => Promise<AnyPage>);
  return function LazyPage(props: P) {
    const C = ready.value[name] as ComponentType<P> | undefined;
    useEffect(() => {
      if (!C) void loadPage(name);
    }, [C]);
    return C ? <C {...props} /> : <div class="wrap page" aria-busy="true" />;
  };
}

/** The server's render has every page at hand (entry-server.tsx). */
export function registerPages(pages: Partial<Record<LazyName, AnyPage>>): void {
  ready.value = { ...ready.value, ...pages };
}

/** The chunk a route's page needs; null for the pages in the entry (home, room, not found). */
export function lazyNameOf(route: Route): LazyName | null {
  switch (route.name) {
    case 'product':
    case 'cart':
    case 'checkout':
    case 'order':
    case 'mock-pay':
    case 'legal':
      return route.name;
    default:
      return null;
  }
}

/** Loads what a route's page needs (resolves at once when it is in the entry). */
export function preloadRoute(route: Route): Promise<unknown> {
  const name = lazyNameOf(route);
  return name ? loadPage(name) : Promise.resolve();
}
