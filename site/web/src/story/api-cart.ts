/**
 * S7: the story's cart is the shop's cart. The same API (/api/cart, the Worker and D1), the same cart id in the browser
 * ('hd.cart', which the shop's pages read), so "המראה כולו לסל" in a story page, the cart, and the real /checkout/ are
 * one. The server holds the truth: it prices every line, refuses a variant that is not sold (PRE1) and a quantity
 * outside 1–20 (zod, server side); the browser keeps only the cart's id and the last view of it.
 */
import type { Cart, Pack } from '@hd/shared';
import { httpApi } from '../api/http';
import { ApiError } from '../api/types';
import { MAX_QTY, type StoryCart } from './story-cart';

export const CART_KEY = 'hd.cart';
const read = (): string | null => {
  try {
    return localStorage.getItem(CART_KEY);
  } catch {
    return null;
  }
};
const write = (id: string | null): void => {
  try {
    if (id) localStorage.setItem(CART_KEY, id);
    else localStorage.removeItem(CART_KEY);
  } catch {
    /* storage unavailable: the cart lives for this page only */
  }
};

/** S21 (ת63): whether this browser keeps storage at all (a private window may read but refuse to write) */
const usable = (): boolean => {
  try {
    localStorage.setItem('hd.probe', '1');
    localStorage.removeItem('hd.probe');
    return true;
  } catch {
    return false;
  }
};

export type ApiStoryCart = StoryCart & {
  load(): Promise<Cart | null>;
  /**
   * S21, QA ת63: the address of the shop's checkout to load from here: once the cart's writes on their way have landed
   * (up to `ms`), with the cart's id in the fragment (#c=, read and removed there) when this browser keeps no storage.
   * Without a write on its way and with storage, the address as it is (a string, not a promise: the link is followed).
   */
  leaveFor(href: string, ms?: number): string | Promise<string>;
};

export function apiStoryCart(api = httpApi): ApiStoryCart {
  let snap: Cart | null = null;
  let id: string | null = read();
  // S21 (ת63): the writes on their way (an add pressed just before "לתשלום")
  const writes = new Set<Promise<unknown>>();
  const track = <T>(p: Promise<T>): Promise<T> => {
    writes.add(p);
    const done = () => void writes.delete(p);
    p.then(done, done);
    return p;
  };
  const withId = (href: string): string => {
    const known = snap?.id ?? id;
    if (!known || usable()) return href;
    const [base = '', hash = ''] = href.split('#');
    const params = new URLSearchParams(hash);
    params.set('c', known);
    return `${base}#${params.toString()}`;
  };
  const ensure = async (): Promise<string> => {
    if (snap) return snap.id;
    if (id) return id;
    const c = await api.createCart();
    snap = c;
    id = c.id;
    write(c.id);
    return c.id;
  };
  /** a cart the server no longer has (ordered, or expired) starts again */
  const set = (variantId: string, pack: Pack, qty: number): Promise<Cart> => track(setNow(variantId, pack, qty));
  const setNow = async (variantId: string, pack: Pack, qty: number): Promise<Cart> => {
    const q = Math.max(0, Math.min(MAX_QTY, Math.trunc(qty)));
    try {
      snap = await api.setItem(await ensure(), variantId, pack, q);
    } catch (e) {
      if (e instanceof ApiError && (e.status === 404 || e.status === 409) && e.code.startsWith('cart')) {
        snap = null;
        id = null;
        write(null);
        snap = await api.setItem(await ensure(), variantId, pack, q);
      } else throw e;
    }
    return snap;
  };
  const self: ApiStoryCart = {
    kind: 'http',
    createCart: () => api.createCart(),
    getCart: (cartId) => api.getCart(cartId),
    setItem: (cartId, v, pack, qty) => api.setItem(cartId, v, pack, qty),
    leaveFor(href, ms = 4000) {
      if (!writes.size) return withId(href);
      const end = Date.now() + ms;
      return (async () => {
        while (writes.size && Date.now() < end)
          await Promise.race([Promise.allSettled([...writes]), new Promise((r) => setTimeout(r, Math.max(0, end - Date.now())))]);
        return withId(href);
      })();
    },
    async load() {
      // a browser without storage keeps the id this page made (S21); with storage, storage has the last word
      id = usable() ? read() : (snap?.id ?? id);
      if (!id) return (snap = null);
      try {
        snap = await api.getCart(id);
      } catch (e) {
        if (e instanceof ApiError && (e.status === 404 || e.status === 409)) {
          id = null;
          write(null);
        }
        snap = null;
      }
      return snap;
    },
    async add(variantId, qty = 1, pack = 'set') {
      const now = snap?.lines.find((l) => l.variant_id === variantId && l.pack === pack)?.qty ?? 0;
      return set(variantId, pack, now + qty);
    },
    async addLook(entries) {
      const added: string[] = [];
      const skipped: string[] = [];
      const already: string[] = [];
      let units = 0;
      const inCart = new Set((snap?.lines ?? []).filter((l) => l.pack === 'set').map((l) => l.variant_id));
      for (const entry of entries) {
        const [v = '', n] = entry.split('*');
        const qty = n && /^\d+$/.test(n) ? Math.max(1, Math.min(MAX_QTY, Number(n))) : 1;
        // a product already in the cart stays as it is (QA on S4: the look twice adds nothing)
        if (inCart.has(v)) already.push(v);
        else
          try {
            await set(v, 'set', qty);
            added.push(v);
            units += qty;
          } catch {
            skipped.push(v);
          }
      }
      return { cart: snap, added, skipped, already, units };
    },
    setQty: (variantId, pack, qty) => set(variantId, pack, qty),
    current: () => snap,
    // the server prices what it sells and drops what it does not: nothing is held in the browser
    held: () => [],
    remove(variantId, pack) {
      void set(variantId, pack, 0);
    },
    clear() {
      snap = null;
      id = null;
      write(null);
    },
  };
  return self;
}
