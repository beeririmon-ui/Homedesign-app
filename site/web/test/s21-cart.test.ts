/**
 * S21, QA ת63: the cart state behind the full page loads of the cart and the checkout (S19, ת55).
 * - the saved cart is fetched from the start but shown only after the app is mounted (`cartMounted`): until then, and in
 *   the prerendered page, the status is 'loading' (the header, the cart and the checkout are busy, never "empty");
 * - a cart that is gone (404) is empty; a load that failed is 'failed', never empty, and the next add uses the saved id;
 * - storage refused: the id goes to the next page (S21: in the address's fragment, #c=; S23, ת72: in window.name);
 * - an add still on its way holds a move to the cart or the checkout (up to LEAVE_WAIT_MS); the writes go with keepalive;
 * - the router: a link to the cart is left to the browser unless the hook has something to wait for or carry.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Cart } from '@hd/shared';

type CartMod = typeof import('../src/state/cart');
const cartOf = (id: string, qty = 0): Cart =>
  ({
    id,
    lines: qty ? [{ variant_id: 'vase:white', pack: 'set', qty, product_id: 'vase', name_he: 'אגרטל' }] : [],
    count: qty,
    subtotal_agorot: qty * 10000,
  }) as unknown as Cart;

/** a controllable store API */
const fake = {
  getCart: vi.fn<(id: string) => Promise<Cart>>(),
  createCart: vi.fn<() => Promise<Cart>>(),
  setItem: vi.fn<(id: string, v: string, pack: string, qty: number) => Promise<Cart>>(),
};
vi.mock('../src/api', async () => ({ api: { kind: 'http', ...fake }, ApiError: (await import('../src/api/types')).ApiError }));

/** localStorage that works (a Map), or refuses as "block all site data" does */
function storage(works: boolean, init: Record<string, string> = {}) {
  const m = new Map(Object.entries(init));
  const deny = () => {
    throw new DOMException('The operation is insecure.', 'SecurityError');
  };
  vi.stubGlobal(
    'localStorage',
    works
      ? { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => void m.set(k, v), removeItem: (k: string) => void m.delete(k) }
      : { getItem: deny, setItem: deny, removeItem: deny },
  );
  return m;
}
/** S23: the tab's window.name (state/carrier.ts) */
function tab(name = '') {
  const w = { name };
  vi.stubGlobal('window', w);
  return w;
}
function address(hash = '') {
  const loc = { pathname: '/cart/', search: '', hash, assign: vi.fn(), replace: vi.fn() };
  const hist = { state: null, replaceState: vi.fn((_s: unknown, _t: string, u: string) => void (loc.hash = u.includes('#') ? u.slice(u.indexOf('#')) : '')) };
  vi.stubGlobal('location', loc);
  vi.stubGlobal('history', hist);
  return { loc, hist };
}
const deferred = <T>() => {
  let resolve!: (v: T) => void;
  const promise = new Promise<T>((r) => (resolve = r));
  return { promise, resolve };
};
const tick = () => new Promise((r) => setTimeout(r, 0));

let m: CartMod;
/** the error class of the module graph the cart state was loaded in (the modules are reset per test) */
let ApiError: typeof import('../src/api/types').ApiError;
beforeEach(async () => {
  (globalThis as { __ARTIFACT__?: boolean }).__ARTIFACT__ = false;
  vi.resetModules();
  for (const f of Object.values(fake)) f.mockReset();
  m = await import('../src/state/cart');
  ApiError = (await import('../src/api')).ApiError;
});
afterEach(() => {
  vi.unstubAllGlobals();
});

describe('ת63 (1): never "empty" or "(0)" while the saved cart loads', () => {
  it('the saved cart is fetched at once, and shown only after the app is mounted (hydration meets the loading state)', async () => {
    storage(true, { 'hd.cart': 'cart-abc123' });
    address();
    fake.getCart.mockResolvedValue(cartOf('cart-abc123', 2));
    const load = m.loadCart();
    expect(fake.getCart).toHaveBeenCalledWith('cart-abc123');
    await tick();
    // the answer is in, but the app has not hydrated: nothing changes yet
    expect([m.cartStatus.value, m.cart.value, m.cartCount.value]).toEqual(['loading', null, 0]);
    // the page and the start of the app share one request
    expect(m.loadCart()).toBe(load);
    m.cartMounted();
    await load;
    expect([m.cartStatus.value, m.cartCount.value]).toEqual(['ready', 2]);
  });

  it('no saved cart: known and empty as soon as the app is mounted, with no request', async () => {
    storage(true);
    address();
    m.cartMounted();
    await m.loadCart();
    expect(fake.getCart).not.toHaveBeenCalled();
    expect([m.cartStatus.value, m.cart.value]).toEqual(['ready', null]);
  });

  it('a cart the server no longer has (404) is empty, and forgotten', async () => {
    const st = storage(true, { 'hd.cart': 'cart-gone-1' });
    address();
    fake.getCart.mockRejectedValue(new ApiError(404, 'cart_not_found'));
    m.cartMounted();
    await m.loadCart();
    expect(m.cartStatus.value).toBe('ready');
    expect(st.has('hd.cart')).toBe(false);
  });

  it('a load that failed is "failed" with its words, never empty; the next add goes to the saved cart, not a new one', async () => {
    storage(true, { 'hd.cart': 'cart-keep-1' });
    address();
    fake.getCart.mockRejectedValueOnce(new ApiError(0, 'network', 'אין חיבור לשרת. בדקו את החיבור ונסו שוב.'));
    m.cartMounted();
    await m.loadCart();
    expect(m.cartStatus.value).toBe('failed');
    expect(m.cartError.value).toContain('אין חיבור');
    // S23 (ת73 (a)): the add loads the saved cart again first, and adds to its quantity
    fake.getCart.mockResolvedValueOnce(cartOf('cart-keep-1', 2));
    fake.setItem.mockResolvedValue(cartOf('cart-keep-1', 3));
    expect(await m.addToCart('vase:white', 'אגרטל')).toBe(true);
    expect(fake.createCart).not.toHaveBeenCalled();
    expect(fake.setItem.mock.calls[0]!.slice(0, 4)).toEqual(['cart-keep-1', 'vase:white', 'set', 3]);
    expect(m.cartStatus.value).toBe('ready');
  });

  it('an add pressed while the saved cart loads waits for it, and adds to its quantity (never replaces it)', async () => {
    storage(true, { 'hd.cart': 'cart-two-1' });
    address();
    const got = deferred<Cart>();
    fake.getCart.mockReturnValue(got.promise);
    fake.setItem.mockImplementation(async (id, _v, _p, qty) => cartOf(id, qty));
    void m.loadCart();
    m.cartMounted();
    const add = m.addToCart('vase:white', 'אגרטל');
    expect(m.cartWritesPending()).toBe(true);
    got.resolve(cartOf('cart-two-1', 2));
    expect(await add).toBe(true);
    expect(fake.setItem.mock.calls[0]).toEqual(['cart-two-1', 'vase:white', 'set', 3, undefined]);
  });
});

describe('ת63 (2): without storage, the cart id travels to the next page (S23: in window.name, no longer in #c=)', () => {
  it('the id made here goes to the next page in window.name, never in an address; with storage, not at all', async () => {
    storage(false);
    address();
    const win = tab();
    m.cartMounted();
    await m.loadCart();
    fake.createCart.mockResolvedValue(cartOf('cart-new-77'));
    fake.setItem.mockResolvedValue(cartOf('cart-new-77', 1));
    await m.addToCart('vase:white', 'אגרטל');
    expect(JSON.parse(win.name.slice(4))).toEqual({ c: 'cart-new-77' });
    expect(m.leaveFor('/cart/')).toBe('/cart/');
    expect(m.leaveFor('/checkout/?failed=1')).toBe('/checkout/?failed=1');
    // with storage: storage keeps it, and the tab carries nothing
    vi.resetModules();
    m = await import('../src/state/cart');
    storage(true);
    const w2 = tab();
    m.cartMounted();
    await m.loadCart();
    fake.createCart.mockResolvedValue(cartOf('cart-new-78'));
    fake.setItem.mockResolvedValue(cartOf('cart-new-78', 1));
    await m.addToCart('vase:white', 'אגרטל');
    expect(w2.name).toBe('');
  });

  it('the next page reads the id from window.name, and loads that cart (the address has nothing to remove)', async () => {
    storage(false);
    const { hist } = address();
    tab(`hd1:${JSON.stringify({ c: 'cart-name-42' })}`);
    fake.getCart.mockResolvedValue(cartOf('cart-name-42', 1));
    const load = m.loadCart();
    expect(hist.replaceState).not.toHaveBeenCalled();
    expect(fake.getCart).toHaveBeenCalledWith('cart-name-42');
    m.cartMounted();
    await load;
    expect(m.cartCount.value).toBe(1);
  });

  it('a fragment never replaces a cart this browser keeps, nor takes an id out of shape; it is removed all the same', async () => {
    storage(true, { 'hd.cart': 'cart-mine-01' });
    const a = address('#c=cart-theirs-9');
    tab();
    fake.getCart.mockResolvedValue(cartOf('cart-mine-01'));
    void m.loadCart();
    expect(fake.getCart).toHaveBeenCalledWith('cart-mine-01');
    expect(a.loc.hash).toBe('');
    vi.resetModules();
    m = await import('../src/state/cart');
    storage(false);
    const b = address('#c=<script>&x=1');
    void m.loadCart();
    expect(fake.getCart).toHaveBeenCalledTimes(1);
    // another part of the fragment stays
    expect(b.hist.replaceState).toHaveBeenCalledWith(null, '', '/cart/#x=1');
  });
});

describe('ת63 (3): an add still on its way is not lost', () => {
  it('a move to the cart waits for the add (then carries the id when there is no storage); with nothing on its way it does not wait', async () => {
    storage(false);
    address();
    m.cartMounted();
    await m.loadCart();
    expect(m.leaveFor('/cart/')).toBe('/cart/');
    fake.createCart.mockResolvedValue(cartOf('cart-slow-5'));
    const put = deferred<Cart>();
    fake.setItem.mockReturnValue(put.promise);
    const add = m.addToCart('vase:white', 'אגרטל');
    const to = m.leaveFor('/cart/');
    expect(to).toBeInstanceOf(Promise);
    let left: string | null = null;
    void (to as Promise<string>).then((u) => (left = u));
    await tick();
    expect(left).toBeNull();
    put.resolve(cartOf('cart-slow-5', 1));
    await add;
    // S23 (ת72): the address as it is; the id went in window.name
    expect(await to).toBe('/cart/');
  });

  it('it waits at most LEAVE_WAIT_MS', async () => {
    vi.useFakeTimers();
    try {
      storage(true);
      address();
      m.cartMounted();
      await m.loadCart();
      fake.createCart.mockResolvedValue(cartOf('cart-hang-1'));
      fake.setItem.mockReturnValue(new Promise(() => {}));
      void m.addToCart('vase:white', 'אגרטל');
      const to = m.leaveFor('/checkout/') as Promise<string>;
      await vi.advanceTimersByTimeAsync(m.LEAVE_WAIT_MS + 10);
      expect(await to).toBe('/checkout/');
    } finally {
      vi.useRealTimers();
    }
  });

  it('the cart’s writes go with keepalive (a page that unloads does not cut them off); its reads do not', async () => {
    vi.doUnmock('../src/api');
    const calls: RequestInit[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_u: string, init: RequestInit = {}) => {
        calls.push(init);
        return new Response(JSON.stringify(cartOf('cart-k-1')), { status: 200, headers: { 'content-type': 'application/json' } });
      }),
    );
    const { httpApi } = await import('../src/api/http');
    await httpApi.createCart();
    await httpApi.setItem('cart-k-1', 'vase:white', 'set', 1);
    await httpApi.getCart('cart-k-1');
    expect(calls.map((c) => [c.method ?? 'GET', !!c.keepalive])).toEqual([
      ['POST', true],
      ['PUT', true],
      ['GET', false],
    ]);
  });
});

describe('the router’s door to a page of its own (ת55, ת63)', () => {
  /** a left click on <a href> as the document's listener gets it */
  function click(router: typeof import('../src/router'), href: string) {
    const attrs = new Map<string, string>([['href', href]]);
    const a = {
      target: '',
      hasAttribute: () => false,
      getAttribute: (k: string) => attrs.get(k) ?? null,
      setAttribute: (k: string, v: string) => void attrs.set(k, v),
    };
    const out = { prevented: false, attrs };
    router.onLinkClick({
      defaultPrevented: false,
      button: 0,
      metaKey: false,
      ctrlKey: false,
      shiftKey: false,
      altKey: false,
      target: { closest: () => a },
      preventDefault: () => void (out.prevented = true),
    } as unknown as MouseEvent);
    return out;
  }

  it('nothing to wait for or carry: the browser follows the link; an id to carry: the address with it; a write on its way: busy, then the load', async () => {
    const router = await import('../src/router');
    const { loc } = address();
    router.setBeforeDocumentLoad((h) => h);
    expect(click(router, '/cart/').prevented).toBe(false);
    router.setBeforeDocumentLoad((h) => `${h}#c=cart-x-12345`);
    expect(click(router, '/checkout/').prevented).toBe(true);
    expect(loc.assign).toHaveBeenLastCalledWith('/checkout/#c=cart-x-12345');
    const later = deferred<string>();
    router.setBeforeDocumentLoad(() => later.promise);
    const c = click(router, '/cart/');
    expect(c.prevented).toBe(true);
    expect(c.attrs.get('aria-busy')).toBe('true');
    expect(loc.assign).toHaveBeenCalledTimes(1);
    later.resolve('/cart/');
    await tick();
    expect(loc.assign).toHaveBeenLastCalledWith('/cart/');
    // from code (navigate), the same hook
    router.setBeforeDocumentLoad((h) => `${h}#c=cart-y-12345`);
    router.navigate('/checkout/?failed=1', { replace: true });
    expect(loc.replace).toHaveBeenLastCalledWith('/checkout/?failed=1#c=cart-y-12345');
    router.setBeforeDocumentLoad(null);
  });
});
