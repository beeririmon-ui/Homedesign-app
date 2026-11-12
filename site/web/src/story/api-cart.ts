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
import { carriedCartId, carryCartId, markWrite, REREAD_MS, settleForeignWrites, writesNotLanded } from '../state/carrier';

export const CART_KEY = 'hd.cart';
const read = (): string | null => {
  try {
    return localStorage.getItem(CART_KEY);
  } catch {
    return null;
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
const write = (id: string | null): void => {
  let kept = false;
  try {
    if (id) localStorage.setItem(CART_KEY, id);
    else localStorage.removeItem(CART_KEY);
    kept = true;
  } catch {
    /* storage unavailable: the id lives in this page, and goes to the next one in window.name */
  }
  // S23 (QA ת72 (c)): never in the address
  carryCartId(kept ? null : id);
};

/** S23 (QA ת74): what the page knows of the saved cart: still loading, known, or not loaded (a server error, no network) */
export type StoryCartStatus = 'loading' | 'ready' | 'failed';
/** S23 (QA ת73): a write refused because the saved cart could not be loaded (its quantities are not known) */
export class CartNotLoaded extends Error {
  constructor(public messageHe: string) {
    super('cart_not_loaded');
  }
}

export type ApiStoryCart = StoryCart & {
  /**
   * The saved cart, read again (the first time, after another tab changed it, back from the back/forward cache, "לנסות
   * שוב"). S23 (QA ת74): a cart that is gone (404, 409) is empty; a load that failed keeps what the page showed, if
   * anything, and says so (`status()` 'failed', `error()`), never "empty".
   */
  load(): Promise<StoryCartStatus>;
  status(): StoryCartStatus;
  /** the words of the last load that failed (the server's, with its error code, else a plain line), or null */
  error(): string | null;
  /**
   * S21, QA ת63: the address of the shop's checkout to load from here, once the cart's writes on their way have landed
   * (up to `ms`; one still on its way leaves its mark for the next page, ה29). Without a write on its way, the address
   * as it is (a string, not a promise: the link is followed). S23 (QA ת72): the address is never changed.
   */
  leaveFor(href: string, ms?: number): string | Promise<string>;
};

export function apiStoryCart(api = httpApi): ApiStoryCart {
  let snap: Cart | null = null;
  // S23 (ת72): window.name is read only without storage (as the shop's state/cart.ts)
  let id: string | null = read() ?? (usable() ? null : carriedCartId());
  let state: StoryCartStatus = 'loading';
  let err: string | null = null;
  // S23 (QA ת73 (b)): the load on its way; a write waits for it, so it adds to the saved quantities and never replaces them
  let loading: Promise<StoryCartStatus> | null = null;
  // S21 (ת63): the writes on their way (an add pressed just before "לתשלום"); S23 (ה29): and their marks
  const writes = new Set<Promise<unknown>>();
  const own = new Set<string>();
  const track = <T>(p: Promise<T>): Promise<T> => {
    writes.add(p);
    const done = () => void writes.delete(p);
    p.then(done, done);
    return p;
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
  const set = (variantId: string, pack: Pack, qty: number): Promise<Cart> => {
    const q = Math.max(0, Math.min(MAX_QTY, Math.trunc(qty)));
    const mark = markWrite(variantId, pack, q);
    own.add(mark.key);
    return track(
      setNow(variantId, pack, q).finally(() => {
        mark.done();
        own.delete(mark.key);
      }),
    );
  };
  const setNow = async (variantId: string, pack: Pack, q: number): Promise<Cart> => {
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
    // a write that landed makes the cart known (it is what the server holds now)
    state = 'ready';
    err = null;
    return snap;
  };
  const loadNow = async (): Promise<StoryCartStatus> => {
    // a browser without storage keeps the id this page knows, or the one the page before carried (S23: window.name);
    // with storage, storage has the last word
    id = usable() ? read() : (snap?.id ?? id ?? carriedCartId());
    if (!id) {
      snap = null;
      err = null;
      return (state = 'ready');
    }
    const cartId = id;
    const get = (): Promise<{ c: Cart } | { e: unknown }> =>
      api.getCart(cartId).then(
        (c) => ({ c }),
        (e: unknown) => ({ e }),
      );
    let r = await get();
    // S23, ה29: a write a page before this one left on its way: read again until it shows (at most PENDING_WAIT_MS)
    while ('c' in r && writesNotLanded(r.c, own).length) {
      await new Promise((ok) => setTimeout(ok, REREAD_MS));
      r = await get();
    }
    settleForeignWrites(own);
    if ('c' in r) {
      snap = r.c;
      err = null;
      return (state = 'ready');
    }
    const e = r.e;
    if (e instanceof ApiError && (e.status === 404 || e.status === 409)) {
      id = null;
      write(null);
      snap = null;
      err = null;
      return (state = 'ready');
    }
    // S23 (QA ת74): a failure is not an empty cart: what was shown stays, and the page says it could not load
    err = e instanceof ApiError && e.messageHe ? e.messageHe : 'לא הצלחנו לטעון את הסל. נסו לרענן את הדף.';
    if (state !== 'ready') state = 'failed';
    return state;
  };
  const load = (): Promise<StoryCartStatus> => {
    if (loading) return loading;
    const p = loadNow().finally(() => {
      if (loading === p) loading = null;
    });
    loading = p;
    return p;
  };
  /**
   * S23 (QA ת73): before a write that adds to what the cart holds, the saved cart must be known: a load on its way is
   * waited for (b), and after a load that failed it loads again first (a); while it still fails, the write is refused.
   */
  const known = async (): Promise<void> => {
    if (loading) await loading;
    if (state === 'failed') await load();
    if (state === 'failed') throw new CartNotLoaded(err ?? 'לא הצלחנו לטעון את הסל. נסו לרענן את הדף.');
  };
  const self: ApiStoryCart = {
    kind: 'http',
    createCart: () => api.createCart(),
    getCart: (cartId) => api.getCart(cartId),
    setItem: (cartId, v, pack, qty) => api.setItem(cartId, v, pack, qty),
    leaveFor(href, ms = 4000) {
      if (!writes.size) return href;
      const end = Date.now() + ms;
      return (async () => {
        while (writes.size && Date.now() < end)
          await Promise.race([Promise.allSettled([...writes]), new Promise((r) => setTimeout(r, Math.max(0, end - Date.now())))]);
        return href;
      })();
    },
    load,
    status: () => state,
    error: () => (state === 'failed' ? err : null),
    async add(variantId, qty = 1, pack = 'set') {
      // the press is a write on its way from here (a move to the checkout waits for it while the saved cart loads)
      return track(
        (async () => {
          await known();
          const now = snap?.lines.find((l) => l.variant_id === variantId && l.pack === pack)?.qty ?? 0;
          return set(variantId, pack, now + qty);
        })(),
      );
    },
    async addLook(entries) {
      return track(
        (async () => {
          await known();
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
        })(),
      );
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
