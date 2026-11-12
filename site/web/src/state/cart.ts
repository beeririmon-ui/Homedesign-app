import { batch, signal, computed } from '@preact/signals';
import type { Cart, Pack } from '@hd/shared';
import { api, ApiError } from '../api';
import { announce } from './ui';

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
 * The cart id this document knows: the one in storage, the one the address's fragment carried (#c=, S21: a browser
 * that keeps no storage), or the one it made. Storage has the last word when it holds one (another tab may have ordered).
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
  return stored() ?? memId;
}
function saveId(id: string | null): void {
  memId = id;
  try {
    if (id) localStorage.setItem(KEY, id);
    else localStorage.removeItem(KEY);
  } catch {
    /* storage unavailable: the id lives in this document, and goes to the next one in the address's fragment */
  }
}

/** a cart id as the API and the mock make them (base64url or hex) */
const CART_ID = /^[A-Za-z0-9_-]{8,80}$/;
/** the pages a cart id is carried to when storage keeps none: the cart and the checkout */
const CARRIES_CART = /^\/(?:cart|checkout)(?:\/|$)/;

/**
 * S21, QA ת63 (2): the cart id the page before carried in this address's fragment ("#c=<id>"), because this browser keeps
 * no storage. It is read once, then removed from the address (replaceState: no history entry, and a fragment never
 * reaches a server or a referrer). It is taken only when storage holds no cart of its own (a link with someone else's
 * id never replaces one).
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
  if (CART_ID.test(id) && !stored()) saveId(id);
}

/**
 * The address to load for a page of its own (S19, ת55: the cart, the checkout), with this document's cart id in its
 * fragment when this browser keeps no storage (S21, ת63 (2)); any other address as it is.
 */
export function withCartId(href: string): string {
  const id = cart.value?.id ?? memId;
  const [base = '', hash = ''] = href.split('#');
  if (!id || !CARRIES_CART.test(base.split('?')[0] ?? '') || usable()) return href;
  const params = new URLSearchParams(hash);
  params.set('c', id);
  return `${base}#${params.toString()}`;
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
 * (up to LEAVE_WAIT_MS; the writes also go with `keepalive`, api/http.ts). Then the address, with the cart id when
 * storage keeps none.
 */
export function leaveFor(href: string): string | Promise<string> {
  if (!writes.size) return withCartId(href);
  return cartWritesSettled().then(() => withCartId(href));
}

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
/** the cart as the server has it (once at a time: the page and the start of the app share one request) */
export function loadCart(): Promise<void> {
  if (inflight) return inflight;
  adoptFragmentId();
  const id = savedId();
  const got: Promise<{ c: Cart } | { e: unknown } | null> = id
    ? api.getCart(id).then(
        (c) => ({ c }),
        (e: unknown) => ({ e }),
      )
    : Promise.resolve(null);
  const p = (async () => {
    const r = await got;
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
  return track(write(variantId, pack, qty, label, house));
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
    if (memId !== c.id) saveId(c.id);
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
