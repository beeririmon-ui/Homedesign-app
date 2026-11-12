import { batch, signal, computed } from '@preact/signals';
import type { Cart, Pack } from '@hd/shared';
import { api, ApiError } from '../api';
import { announce } from './ui';
import { CART_ID, REREAD_MS, carriedCartId, carryCartId, markWrite, settleForeignWrites, writesNotLanded } from './carrier';

const KEY = 'hd.cart';
export const cart = signal<Cart | null>(null);
export const cartBusy = signal(false);
export const cartError = signal<string | null>(null);
export const cartCount = computed(() => cart.value?.count ?? 0);
/**
 * S21, QA ת63: whether this document knows its cart yet. Since S19 (ת55) the cart and the checkout are always a full
 * page load, so every entry starts without the cart and the saved one is fetched again.
 * - **'loading'** until then: the header's count, the cart and the checkout show a quiet loading state (`aria-busy`),
 *   never "סל (0)", "הסל ריק." or "הסל ריק, אין מה לשלם.". The prerendered pages are drawn in it too, and so is the
 *   first render that hydrates them (Preact keeps the prerendered attributes then): it changes only after `cartMounted`.
 * - **'ready'**: the cart is known: none was saved, the API sent it, or the API said it is gone (404, 409).
 * - **'failed'**: the saved cart could not be fetched (no network, a server error): its words, never "empty".
 */
export type CartStatus = 'loading' | 'ready' | 'failed';
export const cartStatus = signal<CartStatus>('loading');
/** S6, §7.2: the line just added ("variant:pack"), for 2.5 s: the button that added it says "נוסף לסל" */
export const justAdded = signal<string | null>(null);
let addedTimer: ReturnType<typeof setTimeout> | undefined;

/**
 * The cart id this document knows: the one in storage, the one the page before carried in window.name (S23, QA ת72 (c):
 * a browser that keeps no storage; S21 carried it in the address's #c=), or the one it made. Storage has the last word
 * when it holds one (another tab may have ordered).
 */
let memId: string | null = null;
function stored(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}
/** whether this browser keeps storage at all (a private window may read but refuse to write) */
function usable(): boolean {
  try {
    localStorage.setItem('hd.probe', '1');
    localStorage.removeItem('hd.probe');
    return true;
  } catch {
    return false;
  }
}
function savedId(): string | null {
  return stored() ?? memId ?? carriedCartId();
}
function saveId(id: string | null): void {
  memId = id;
  let kept = false;
  try {
    if (id) localStorage.setItem(KEY, id);
    else localStorage.removeItem(KEY);
    kept = true;
  } catch {
    /* storage unavailable: the id lives in this document, and goes to the next one in window.name */
  }
  // S23 (ת72 (c)): never in the address; and once storage keeps it, the tab carries it no more
  carryCartId(kept ? null : id);
}

/** the pages that may take a cart id from a link (ת72 (a)): the cart and the checkout */
const CARRIES_CART = /^\/(?:cart|checkout)(?:\/|$)/;

/**
 * S21 carried the cart id to the next page in the address's fragment ("#c=<id>"); since S23 (QA ת72 (c)) it goes in
 * window.name (state/carrier.ts), and the site writes no "#c=" anywhere. A "#c=" in an address is still read once and
 * removed from it (replaceState: no history entry, and a fragment never reaches a server or a referrer), and it is
 * taken only (QA ת72 (a)) on the cart or the checkout, only by a browser that keeps no storage, and only when this tab
 * knows no cart of its own: a link with someone else's id plants nothing where storage works, nor on any other page.
 */
export function adoptFragmentId(): void {
  if (typeof location === 'undefined' || !location.hash) return;
  const params = new URLSearchParams(location.hash.slice(1));
  const id = params.get('c');
  if (id === null) return;
  params.delete('c');
  const rest = params.toString();
  try {
    history.replaceState(history.state, '', `${location.pathname}${location.search}${rest ? `#${rest}` : ''}`);
  } catch {
    /* a sandboxed frame: the fragment stays, and is read again harmlessly */
  }
  if (CART_ID.test(id) && CARRIES_CART.test(location.pathname) && !usable() && !savedId()) saveId(id);
}

// ---------- S21, QA ת63 (3): writes still on their way ----------
const writes = new Set<Promise<unknown>>();
function track<T>(p: Promise<T>): Promise<T> {
  writes.add(p);
  const done = () => void writes.delete(p);
  p.then(done, done);
  return p;
}
export const cartWritesPending = (): boolean => writes.size > 0;
/** how long a move to the cart or the checkout waits for an add still on its way (a slow phone network) */
export const LEAVE_WAIT_MS = 4000;
/** resolves when no cart write is on its way, or after `ms` (a write may start another: the retry of a lost cart) */
export async function cartWritesSettled(ms = LEAVE_WAIT_MS): Promise<void> {
  const end = Date.now() + ms;
  while (writes.size && Date.now() < end) {
    await Promise.race([Promise.allSettled([...writes]), new Promise((r) => setTimeout(r, Math.max(0, end - Date.now())))]);
  }
}
/**
 * S21, QA ת63: the router's hook before a page of its own is loaded (router.ts `beforeDocumentLoad`). An add or a change
 * still on its way would be cut off by the load, or land after the next page read the cart: the move waits for it
 * (up to LEAVE_WAIT_MS; the writes also go with `keepalive`, api/http.ts, and leave their mark for the next page, ה29).
 * S23 (QA ת72 (b), (c)): the address is never changed (the cart id goes in window.name), so a link to the page itself
 * stays as it is too.
 */
export function leaveFor(href: string): string | Promise<string> {
  if (!writes.size) return href;
  return cartWritesSettled().then(() => href);
}
/** S23, ה29: this document's own marks of writes on their way (a write of this page is never waited for by its load) */
const ownMarks = new Set<string>();

// ---------- loading ----------
let mounted = false;
const onMounted: (() => void)[] = [];
/**
 * main.tsx calls this once the app has hydrated (or rendered). The saved cart is fetched from the start, but it is
 * shown only after: a render before hydration would differ from the prerendered page, and Preact would keep the
 * prerendered attributes (aria-busy, the count's label) over the new ones.
 */
export function cartMounted(): void {
  mounted = true;
  for (const f of onMounted.splice(0)) f();
}
const whenMounted = (): Promise<void> => (mounted ? Promise.resolve() : new Promise((r) => onMounted.push(r)));

let inflight: Promise<void> | null = null;
type Got = { c: Cart } | { e: unknown } | null;
const fetchCart = (id: string): Promise<Got> =>
  api.getCart(id).then(
    (c) => ({ c }),
    (e: unknown) => ({ e }),
  );
const pause = (ms: number) => new Promise((r) => setTimeout(r, ms));
/** the cart as the server has it (once at a time: the page and the start of the app share one request) */
export function loadCart(): Promise<void> {
  if (inflight) return inflight;
  adoptFragmentId();
  const id = savedId();
  const got: Promise<Got> = id ? fetchCart(id) : Promise.resolve(null);
  const p = (async () => {
    let r = await got;
    // S23, ה29: a write a page before this one left on its way (it took over the 4 s the move waits): the cart is read
    // again until it shows the write, at most PENDING_WAIT_MS after the write began; meanwhile nothing new is shown (the
    // first load stays in its loading state: never "empty", never "סל (0)")
    while (id && r && 'c' in r && writesNotLanded(r.c, ownMarks).length) {
      await pause(REREAD_MS);
      r = await fetchCart(id);
    }
    settleForeignWrites(ownMarks);
    await whenMounted();
    batch(() => {
      if (r && 'c' in r) {
        cart.value = r.c;
        cartError.value = null;
        cartStatus.value = 'ready';
      } else if (r) {
        const e = r.e;
        if (e instanceof ApiError && (e.status === 404 || e.status === 409)) {
          // the cart is gone (ordered, or expired): the empty cart is the truth now
          if (savedId() === id) saveId(null);
          if (cart.value?.id === id) cart.value = null;
          cartError.value = null;
          cartStatus.value = 'ready';
        } else {
          // S16, QA ת37: the server's own words (with its error code) when it sent them, else a plain line; never silence
          cartError.value = e instanceof ApiError && e.messageHe ? e.messageHe : 'לא הצלחנו לטעון את הסל. נסו לרענן את הדף.';
          // a cart already shown stays shown; a first load that failed says so, and never "empty"
          if (cartStatus.value !== 'ready') cartStatus.value = 'failed';
        }
      } else cartStatus.value = 'ready';
    });
  })();
  const shared = p.finally(() => {
    if (inflight === shared) inflight = null;
  });
  inflight = shared;
  return shared;
}

/**
 * S23, QA ת75: a page the browser restores from its back/forward cache shows the cart as it was when the page was left;
 * another page may have changed it since. It reads the cart again (main.tsx and the story call this on `pageshow`).
 */
export function cartPageShown(e: { persisted: boolean }): void {
  if (e.persisted) void loadCart();
}

/** the cart's id: the one shown, else the one saved (a load that failed still knows it), else a new cart */
async function ensureCart(): Promise<string> {
  if (inflight) await inflight;
  if (cart.value) return cart.value.id;
  const known = savedId();
  if (known) return known;
  const c = await api.createCart();
  saveId(c.id);
  cart.value = c;
  return c.id;
}

export function setQty(variantId: string, pack: Pack, qty: number, label?: string, house?: string): Promise<boolean> {
  // S23, ה29: the write leaves its mark for the next page until it has its answer
  const mark = markWrite(variantId, pack, qty);
  ownMarks.add(mark.key);
  return track(
    write(variantId, pack, qty, label, house).finally(() => {
      mark.done();
      ownMarks.delete(mark.key);
    }),
  );
}
async function write(variantId: string, pack: Pack, qty: number, label?: string, house?: string): Promise<boolean> {
  cartBusy.value = true;
  cartError.value = null;
  try {
    const id = await ensureCart();
    const c = await api.setItem(id, variantId, pack, qty, house);
    batch(() => {
      cart.value = c;
      cartStatus.value = 'ready';
    });
    // a new id, or storage that keeps it again (S23: then the tab carries it no more)
    if (memId !== c.id || stored() !== c.id) saveId(c.id);
    if (label) announce(qty > 0 ? label : `הוסר מהסל`);
    return true;
  } catch (e) {
    if (e instanceof ApiError && (e.status === 404 || e.status === 409) && e.code.startsWith('cart')) {
      saveId(null);
      cart.value = null;
      return write(variantId, pack, qty, label, house);
    }
    cartError.value = e instanceof ApiError ? (e.messageHe ?? 'לא הצלחנו לעדכן את הסל.') : 'לא הצלחנו לעדכן את הסל.';
    announce(cartError.value);
    return false;
  } finally {
    cartBusy.value = false;
  }
}

/**
 * Adds to the cart: `pack` is the set (default) or one piece (P1); each is its own line. `house`: the room engine's
 * house it is added in (S12, ת21), so the order's "החדר שלך" draws that house.
 */
export function addToCart(variantId: string, name: string, qty = 1, pack: Pack = 'set', packLabel?: string, house?: string): Promise<boolean> {
  // S21 (ת63): on its way from the press, so a move to the cart waits for it even while the saved cart still loads
  return track(
    (async () => {
      // a saved cart still loading is waited for, so its quantity is added to and never replaced
      if (inflight) await inflight;
      // S23, QA ת73 (a): after a load that failed the saved quantities are not known (an add would replace them): it loads
      // again first, and while it still fails the add is refused with the error
      if (cartStatus.value === 'failed') {
        await loadCart();
        if (cartStatus.value === 'failed') {
          announce(cartError.value ?? 'לא הצלחנו לעדכן את הסל.');
          return false;
        }
      }
      const current = cart.value?.lines.find((l) => l.variant_id === variantId && l.pack === pack)?.qty ?? 0;
      const ok = await setQty(variantId, pack, Math.min(20, current + qty), `נוסף לסל: ${name}${packLabel ? `, ${packLabel}` : ''}`, house);
      if (ok) {
        justAdded.value = `${variantId}:${pack}`;
        clearTimeout(addedTimer);
        addedTimer = setTimeout(() => (justAdded.value = null), 2500);
      }
      return ok;
    })(),
  );
}

export function forgetCart(): void {
  saveId(null);
  cart.value = null;
}

export function saveOrderToken(orderId: string, token: string): void {
  try {
    localStorage.setItem(`hd.order.${orderId}`, token);
  } catch {
    sessionTokens.set(orderId, token);
  }
}
const sessionTokens = new Map<string, string>();
export function orderToken(orderId: string): string | null {
  try {
    return localStorage.getItem(`hd.order.${orderId}`) ?? sessionTokens.get(orderId) ?? null;
  } catch {
    return sessionTokens.get(orderId) ?? null;
  }
}
