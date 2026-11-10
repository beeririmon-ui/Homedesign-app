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

export type ApiStoryCart = StoryCart & { load(): Promise<Cart | null> };

export function apiStoryCart(api = httpApi): ApiStoryCart {
  let snap: Cart | null = null;
  let id: string | null = read();
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
  const set = async (variantId: string, pack: Pack, qty: number): Promise<Cart> => {
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
    async load() {
      id = read();
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
