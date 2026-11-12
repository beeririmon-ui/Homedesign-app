/**
 * S23, QA S21: the cart state of the shop (state/cart.ts) and of the story (story/api-cart.ts), and what a tab carries
 * to its next page (state/carrier.ts).
 * - ת72: the cart id of a browser without storage goes in window.name, never in an address (c); no link gets it, the
 *   page's own address included (b); a "#c=" is taken only on the cart or the checkout, only without storage, and only
 *   when the tab knows no cart of its own, and it is removed from the address on every page (a);
 * - ת73: a write that adds waits for the saved cart (the story, b), and after a load that failed it loads again first,
 *   refused while it still fails (the shop, a; the story too);
 * - ת74: the story's load that failed is 'failed' with its words, never an empty cart; 404 and 409 are;
 * - ת75: a page shown again from the back/forward cache reads the cart again;
 * - ה29: a write on its way leaves a mark in window.name; the next page reads the cart again until it shows the write
 *   (never "empty" meanwhile), at most PENDING_WAIT_MS after the write began.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Cart } from '@hd/shared';

type CartMod = typeof import('../src/state/cart');
type CarrierMod = typeof import('../src/state/carrier');
const cartOf = (id: string, qty = 0, variant = 'vase:white'): Cart =>
  ({
    id,
    lines: qty ? [{ variant_id: variant, pack: 'set', qty, product_id: variant.split(':')[0], name_he: 'אגרטל' }] : [],
    count: qty,
    subtotal_agorot: qty * 10000,
  }) as unknown as Cart;

const fake = {
  getCart: vi.fn<(id: string) => Promise<Cart>>(),
  createCart: vi.fn<() => Promise<Cart>>(),
  setItem: vi.fn<(id: string, v: string, pack: string, qty: number) => Promise<Cart>>(),
};
vi.mock('../src/api', async () => ({ api: { kind: 'http', ...fake }, ApiError: (await import('../src/api/types')).ApiError }));
const announced: string[] = [];
vi.mock('../src/state/ui', () => ({ announce: (t: string) => void announced.push(t) }));

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
function address(pathname = '/cart/', hash = '') {
  const loc = { pathname, search: '', hash, href: `http://127.0.0.1${pathname}${hash}`, assign: vi.fn(), replace: vi.fn() };
  const hist = { state: null, replaceState: vi.fn((_s: unknown, _t: string, u: string) => void (loc.hash = u.includes('#') ? u.slice(u.indexOf('#')) : '')) };
  vi.stubGlobal('location', loc);
  vi.stubGlobal('history', hist);
  return { loc, hist };
}
function tab(name = '') {
  const w = { name };
  vi.stubGlobal('window', w);
  return w;
}
const carried = (w: { name: string }) =>
  w.name.startsWith('hd1:') ? (JSON.parse(w.name.slice(4)) as { c?: string; w?: { v: string; q: number; t: number }[] }) : null;
const deferred = <T>() => {
  let resolve!: (v: T) => void;
  let reject!: (e: unknown) => void;
  const promise = new Promise<T>((r, j) => ((resolve = r), (reject = j)));
  return { promise, resolve, reject };
};
const tick = () => new Promise((r) => setTimeout(r, 0));

let m: CartMod;
let carrier: CarrierMod;
let ApiError: typeof import('../src/api/types').ApiError;
beforeEach(async () => {
  (globalThis as { __ARTIFACT__?: boolean }).__ARTIFACT__ = false;
  vi.resetModules();
  for (const f of Object.values(fake)) f.mockReset();
  announced.length = 0;
  m = await import('../src/state/cart');
  carrier = await import('../src/state/carrier');
  ApiError = (await import('../src/api')).ApiError;
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('ת72 (a): a "#c=" in an address plants nothing', () => {
  it('storage works and holds no cart: no page takes it (the room, the product, the cart, the checkout); it is removed', async () => {
    for (const p of ['/rooms/living-room/', '/p/vase-x/', '/cart/', '/checkout/']) {
      vi.resetModules();
      m = await import('../src/state/cart');
      const st = storage(true);
      const { loc } = address(p, '#c=cart-theirs-77');
      const w = tab();
      m.cartMounted();
      await m.loadCart();
      expect(fake.getCart, p).not.toHaveBeenCalled();
      expect([st.has('hd.cart'), loc.hash, w.name], p).toEqual([false, '', '']);
      expect(m.cart.value, p).toBeNull();
    }
  });
  it('no storage: only the cart and the checkout take it, and only when the tab knows no cart of its own', async () => {
    for (const p of ['/rooms/living-room/', '/p/vase-x/', '/story/living-room/boho/']) {
      vi.resetModules();
      m = await import('../src/state/cart');
      storage(false);
      const { loc } = address(p, '#c=cart-theirs-77');
      tab();
      m.cartMounted();
      await m.loadCart();
      expect(fake.getCart, p).not.toHaveBeenCalled();
      expect(loc.hash, p).toBe('');
    }
    // the tab's own cart wins over the link's
    vi.resetModules();
    m = await import('../src/state/cart');
    storage(false);
    address('/cart/', '#c=cart-theirs-77');
    tab(`hd1:${JSON.stringify({ c: 'cart-mine-0001' })}`);
    fake.getCart.mockResolvedValue(cartOf('cart-mine-0001', 1));
    m.cartMounted();
    await m.loadCart();
    expect(fake.getCart.mock.calls.map((c) => c[0])).toEqual(['cart-mine-0001']);
    // the brief's one case: the cart, no storage, no cart of its own
    vi.resetModules();
    m = await import('../src/state/cart');
    storage(false);
    const { loc } = address('/cart/', '#c=cart-theirs-77');
    tab();
    fake.getCart.mockResolvedValue(cartOf('cart-theirs-77', 3));
    m.cartMounted();
    await m.loadCart();
    expect(fake.getCart).toHaveBeenLastCalledWith('cart-theirs-77');
    expect(loc.hash).toBe('');
  });
});

describe('ת72 (b), (c): the id never enters an address', () => {
  it('no link gets the id, the page’s own address included; it goes in window.name, and leaves it once storage keeps it', async () => {
    storage(false);
    address('/cart/');
    const w = tab();
    m.cartMounted();
    await m.loadCart();
    fake.createCart.mockResolvedValue(cartOf('cart-new-0077'));
    fake.setItem.mockResolvedValue(cartOf('cart-new-0077', 1));
    await m.addToCart('vase:white', 'אגרטל');
    for (const h of ['/cart/', '/checkout/', '/cart/#top', '/p/vase-x/']) expect(m.leaveFor(h)).toBe(h);
    expect(carried(w)).toEqual({ c: 'cart-new-0077' });
    // storage comes back (the customer allowed it): the next save keeps it there, and the tab carries it no more
    storage(true);
    fake.setItem.mockResolvedValue(cartOf('cart-new-0077', 2));
    await m.addToCart('vase:white', 'אגרטל');
    expect(w.name).toBe('');
  });
  it('a window name that is not ours is never overwritten (a window opened with a target name)', () => {
    const w = tab('preview-window');
    carrier.carryCartId('cart-new-0077');
    carrier.markWrite('vase:white', 'set', 1);
    expect(w.name).toBe('preview-window');
    expect(carrier.carriedCartId()).toBeNull();
  });
  it('what is read back is trusted only in its shape', () => {
    tab(
      `hd1:${JSON.stringify({
        c: '<img src=x>',
        w: [
          { v: 'x', p: 'set', q: 99, t: Date.now(), k: 'a' },
          { v: 'y', p: 'set', q: 2, t: Date.now(), k: 'b' },
        ],
      })}`,
    );
    expect(carrier.carriedCartId()).toBeNull();
    expect(carrier.writesNotLanded(null, new Set()).map((x) => x.v)).toEqual(['y']);
    tab('hd1:{not json');
    expect(carrier.carriedCartId()).toBeNull();
  });
});

describe('ת73 (a): the shop, an add after a load that failed', () => {
  it('loads again first; while it still fails the add is refused with the error, and nothing is written', async () => {
    storage(true, { 'hd.cart': 'cart-keep-0002' });
    address('/p/vase-x/');
    tab();
    fake.getCart.mockRejectedValue(new ApiError(500, 'http_500', 'השרת עמוס כרגע. נסו שוב בעוד רגע.'));
    m.cartMounted();
    await m.loadCart();
    expect(m.cartStatus.value).toBe('failed');
    expect(await m.addToCart('vase:white', 'אגרטל')).toBe(false);
    expect(fake.getCart).toHaveBeenCalledTimes(2);
    expect(fake.setItem).not.toHaveBeenCalled();
    expect(fake.createCart).not.toHaveBeenCalled();
    expect(announced.at(-1)).toContain('השרת עמוס');
    expect(m.cartStatus.value).toBe('failed');
  });
  it('the load succeeds on the second try: the add adds to the saved ×2 (×3 on the server, never ×1)', async () => {
    storage(true, { 'hd.cart': 'cart-keep-0002' });
    address('/p/vase-x/');
    tab();
    fake.getCart.mockRejectedValueOnce(new ApiError(503, 'unavailable')).mockResolvedValueOnce(cartOf('cart-keep-0002', 2));
    fake.setItem.mockImplementation(async (id, _v, _p, qty) => cartOf(id, qty));
    m.cartMounted();
    await m.loadCart();
    expect(await m.addToCart('vase:white', 'אגרטל')).toBe(true);
    expect(fake.setItem.mock.calls[0]!.slice(0, 4)).toEqual(['cart-keep-0002', 'vase:white', 'set', 3]);
  });
});

describe('ת75: back from the back/forward cache', () => {
  it('a page shown again from the cache reads the cart again; a fresh page does not read twice', async () => {
    storage(true, { 'hd.cart': 'cart-bf-00001' });
    address('/p/vase-x/');
    tab();
    fake.getCart.mockResolvedValueOnce(cartOf('cart-bf-00001', 1)).mockResolvedValueOnce(cartOf('cart-bf-00001', 2));
    m.cartMounted();
    await m.loadCart();
    expect(m.cartCount.value).toBe(1);
    m.cartPageShown({ persisted: false });
    await tick();
    expect(fake.getCart).toHaveBeenCalledTimes(1);
    m.cartPageShown({ persisted: true });
    await m.loadCart();
    expect(m.cartCount.value).toBe(2);
  });
});

describe('ה29: a write still on its way when the page was left', () => {
  it('the write leaves its mark while it is on its way, and takes it away once it has its answer', async () => {
    storage(true, { 'hd.cart': 'cart-mk-00001' });
    address('/p/vase-x/');
    const w = tab();
    m.cartMounted();
    fake.getCart.mockResolvedValue(cartOf('cart-mk-00001'));
    await m.loadCart();
    const put = deferred<Cart>();
    fake.setItem.mockReturnValue(put.promise);
    const add = m.addToCart('vase:white', 'אגרטל');
    await tick();
    await tick();
    expect(carried(w)?.w?.map((x) => [x.v, x.q])).toEqual([['vase:white', 1]]);
    put.resolve(cartOf('cart-mk-00001', 1));
    await add;
    expect(w.name).toBe('');
  });
  it('the next page reads the cart again until the write shows, and stays loading meanwhile (never "empty", never "(0)")', async () => {
    vi.useFakeTimers();
    storage(true, { 'hd.cart': 'cart-mk-00002' });
    address('/cart/');
    tab(`hd1:${JSON.stringify({ w: [{ v: 'vase:white', p: 'set', q: 1, t: Date.now() - 4300, k: 'prev1' }] })}`);
    // the PUT lands on the server between the second and the third read
    fake.getCart.mockResolvedValueOnce(cartOf('cart-mk-00002')).mockResolvedValueOnce(cartOf('cart-mk-00002')).mockResolvedValue(cartOf('cart-mk-00002', 1));
    m.cartMounted();
    const load = m.loadCart();
    await vi.advanceTimersByTimeAsync(10);
    expect([m.cartStatus.value, m.cartCount.value]).toEqual(['loading', 0]);
    await vi.advanceTimersByTimeAsync(800);
    expect(m.cartStatus.value).toBe('loading');
    await vi.advanceTimersByTimeAsync(800);
    await load;
    expect([m.cartStatus.value, m.cartCount.value]).toEqual(['ready', 1]);
    expect(fake.getCart).toHaveBeenCalledTimes(3);
    expect((window as unknown as { name: string }).name).toBe('');
  });
  it('a write that never shows: the cart as it is once PENDING_WAIT_MS have passed since the write began', async () => {
    vi.useFakeTimers();
    storage(true, { 'hd.cart': 'cart-mk-00003' });
    address('/cart/');
    tab(`hd1:${JSON.stringify({ w: [{ v: 'vase:white', p: 'set', q: 1, t: Date.now() - 5000, k: 'prev2' }] })}`);
    fake.getCart.mockResolvedValue(cartOf('cart-mk-00003'));
    m.cartMounted();
    const load = m.loadCart();
    await vi.advanceTimersByTimeAsync(carrier.PENDING_WAIT_MS - 5000 - 800);
    expect(m.cartStatus.value).toBe('loading');
    await vi.advanceTimersByTimeAsync(2000);
    await load;
    expect([m.cartStatus.value, m.cartCount.value]).toEqual(['ready', 0]);
  });
  it('no cart id to read (the cart was never made): nothing to wait for', async () => {
    storage(true);
    address('/cart/');
    tab(`hd1:${JSON.stringify({ w: [{ v: 'vase:white', p: 'set', q: 1, t: Date.now(), k: 'prev3' }] })}`);
    m.cartMounted();
    await m.loadCart();
    expect(m.cartStatus.value).toBe('ready');
    expect(fake.getCart).not.toHaveBeenCalled();
  });
});

describe('the story’s cart (story/api-cart.ts): ת73 (b), ת74, ה29', () => {
  type StoryMod = typeof import('../src/story/api-cart');
  let s: StoryMod;
  // the story imports the error class itself (api/types), not through the mocked api module
  let ApiError: typeof import('../src/api/types').ApiError;
  beforeEach(async () => {
    s = await import('../src/story/api-cart');
    ApiError = (await import('../src/api/types')).ApiError;
  });
  const api = () => ({ kind: 'http' as const, createCart: fake.createCart, getCart: fake.getCart, setItem: fake.setItem });

  it('ת73 (b): "המראה כולו לסל" pressed before the saved cart loaded waits for it: ×3 stays ×3, and "already in the cart" is seen', async () => {
    storage(true, { 'hd.cart': 'cart-st-00001' });
    tab();
    const got = deferred<Cart>();
    fake.getCart.mockReturnValue(got.promise);
    fake.setItem.mockImplementation(async (id, v, _p, qty) => cartOf(id, qty, v));
    const c = s.apiStoryCart(api() as never);
    void c.load();
    const look = c.addLook(['basket:a*1', 'lamp:b']);
    const one = c.add('basket:a');
    await tick();
    expect(fake.setItem).not.toHaveBeenCalled();
    got.resolve(cartOf('cart-st-00001', 3, 'basket:a'));
    const r = await look;
    expect(r.already).toEqual(['basket:a']);
    expect(r.added).toEqual(['lamp:b']);
    await one;
    expect(fake.setItem.mock.calls.map((x) => [x[1], x[3]])).toEqual([
      ['lamp:b', 1],
      ['basket:a', 4],
    ]);
  });
  it('ת74: a load that failed is "failed" with the server’s words (never an empty cart); a 404 is an empty cart', async () => {
    storage(true, { 'hd.cart': 'cart-st-00002' });
    tab();
    fake.getCart.mockRejectedValueOnce(new ApiError(503, 'unavailable', 'השרת עמוס כרגע. קוד השגיאה: E-TEST2345'));
    const c = s.apiStoryCart(api() as never);
    expect(c.status()).toBe('loading');
    expect(await c.load()).toBe('failed');
    expect([c.current(), c.error()]).toEqual([null, 'השרת עמוס כרגע. קוד השגיאה: E-TEST2345']);
    fake.getCart.mockRejectedValueOnce(new TypeError('Failed to fetch'));
    expect(await c.load()).toBe('failed');
    expect(c.error()).toBe('לא הצלחנו לטעון את הסל. נסו לרענן את הדף.');
    // "לנסות שוב" once the API answers
    fake.getCart.mockResolvedValueOnce(cartOf('cart-st-00002', 6));
    expect(await c.load()).toBe('ready');
    expect([c.current()?.count, c.error()]).toEqual([6, null]);
    // a cart shown stays shown when a later read fails
    fake.getCart.mockRejectedValueOnce(new ApiError(500, 'http_500'));
    expect(await c.load()).toBe('ready');
    expect(c.current()?.count).toBe(6);
    // gone: empty is the truth
    fake.getCart.mockRejectedValueOnce(new ApiError(404, 'cart_not_found'));
    expect(await c.load()).toBe('ready');
    expect(c.current()).toBeNull();
  });
  it('ת73 (a) in the story: after a load that failed, a write loads again; still failing, it is refused and nothing is written', async () => {
    storage(true, { 'hd.cart': 'cart-st-00003' });
    tab();
    fake.getCart.mockRejectedValue(new ApiError(500, 'http_500'));
    const c = s.apiStoryCart(api() as never);
    await c.load();
    await expect(c.add('basket:a')).rejects.toBeInstanceOf(s.CartNotLoaded);
    await expect(c.addLook(['basket:a'])).rejects.toBeInstanceOf(s.CartNotLoaded);
    expect(fake.setItem).not.toHaveBeenCalled();
    expect(fake.createCart).not.toHaveBeenCalled();
    fake.getCart.mockReset();
    fake.getCart.mockResolvedValue(cartOf('cart-st-00003', 2, 'basket:a'));
    fake.setItem.mockImplementation(async (id, v, _p, qty) => cartOf(id, qty, v));
    expect((await c.add('basket:a')).lines[0]!.qty).toBe(3);
  });
  it('ת72 (c): without storage the story reads the id the page before carried, and its own goes in window.name', async () => {
    storage(false);
    const w = tab(`hd1:${JSON.stringify({ c: 'cart-st-00004' })}`);
    fake.getCart.mockResolvedValue(cartOf('cart-st-00004', 2));
    const c = s.apiStoryCart(api() as never);
    expect(await c.load()).toBe('ready');
    expect(fake.getCart).toHaveBeenCalledWith('cart-st-00004');
    expect(c.leaveFor('/checkout/')).toBe('/checkout/');
    w.name = '';
    fake.createCart.mockResolvedValue(cartOf('cart-st-00005'));
    fake.setItem.mockResolvedValue(cartOf('cart-st-00005', 1));
    const c2 = s.apiStoryCart(api() as never);
    await c2.load();
    await c2.add('basket:a');
    expect(carried(w)).toEqual({ c: 'cart-st-00005' });
  });
  it('ה29: the story’s writes leave their mark, and its load waits for another page’s', async () => {
    vi.useFakeTimers();
    storage(true, { 'hd.cart': 'cart-st-00006' });
    const w = tab(`hd1:${JSON.stringify({ w: [{ v: 'basket:a', p: 'set', q: 2, t: Date.now() - 4500, k: 'prev9' }] })}`);
    fake.getCart.mockResolvedValueOnce(cartOf('cart-st-00006', 1, 'basket:a')).mockResolvedValue(cartOf('cart-st-00006', 2, 'basket:a'));
    const c = s.apiStoryCart(api() as never);
    const load = c.load();
    await vi.advanceTimersByTimeAsync(10);
    expect(c.status()).toBe('loading');
    await vi.advanceTimersByTimeAsync(800);
    expect(await load).toBe('ready');
    expect(c.current()?.count).toBe(2);
    expect(w.name).toBe('');
    const put = deferred<Cart>();
    fake.setItem.mockReturnValue(put.promise);
    const add = c.add('basket:a');
    await vi.advanceTimersByTimeAsync(0);
    expect(carried(w)?.w?.map((x) => [x.v, x.q])).toEqual([['basket:a', 3]]);
    put.resolve(cartOf('cart-st-00006', 3, 'basket:a'));
    await add;
    expect(w.name).toBe('');
  });
});
