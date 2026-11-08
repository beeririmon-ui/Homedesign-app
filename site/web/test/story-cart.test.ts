/**
 * The story layer's test cart (web/src/story/story-cart.ts): the store API's cart contract (createCart, getCart,
 * setItem) with the site mock's rules, one cart across the story pages, storage that can fail, and the price format held
 * equal to the site's.
 */
import { describe, expect, it } from 'vitest';
import { formatIls } from '@hd/shared/money';
import { MAX_QTY, StoryCartError, memoryStore, priceHe, storyCart, type KeyValue, type StoryVariant } from '../src/story/story-cart';

const V: StoryVariant[] = [
  { variant_id: 'bowl:default', product_id: 'bowl', name_he: 'קערה', option_he: null, price_agorot: 7900, set_qty: 1, available: true },
  { variant_id: 'candles:70x110mm', product_id: 'candles', name_he: 'פמוטים', option_he: null, price_agorot: 19900, set_qty: 2, available: true },
  { variant_id: 'rug:200x300+square', product_id: 'rug', name_he: 'שטיח', option_he: null, price_agorot: 129900, set_qty: 1, available: false },
];

describe('the story test cart', () => {
  it('adds a line per variant, sums the subtotal and the count, and caps a line at 20', async () => {
    const cart = storyCart(V, memoryStore());
    expect(cart.current()).toBeNull();
    await cart.add('bowl:default');
    await cart.add('bowl:default');
    const c = await cart.add('candles:70x110mm');
    expect(c.lines.map((l) => [l.variant_id, l.qty, l.line_total_agorot, l.pack, l.pack_qty])).toEqual([
      ['bowl:default', 2, 15800, 'set', 1],
      ['candles:70x110mm', 1, 19900, 'set', 2],
    ]);
    expect(c.subtotal_agorot).toBe(35700);
    expect(c.count).toBe(3);
    const big = await cart.add('bowl:default', 50);
    expect(big.lines.find((l) => l.variant_id === 'bowl:default')!.qty).toBe(MAX_QTY);
  });

  it('keeps the store API contract: unknown cart 404, not for sale 404, a wrong quantity 422, zero removes the line', async () => {
    const cart = storyCart(V, memoryStore());
    await expect(cart.getCart('nope')).rejects.toMatchObject({ status: 404, code: 'cart_not_found' });
    const { id } = await cart.createCart();
    await expect(cart.setItem(id, 'rug:200x300+square', 'set', 1)).rejects.toBeInstanceOf(StoryCartError);
    await expect(cart.setItem(id, 'rug:200x300+square', 'set', 1)).rejects.toMatchObject({ status: 404 });
    await expect(cart.setItem(id, 'bowl:default', 'set', 21)).rejects.toMatchObject({ status: 422 });
    await expect(cart.setItem(id, 'bowl:default', 'unit', 1)).rejects.toMatchObject({ status: 422 });
    await cart.setItem(id, 'bowl:default', 'set', 2);
    expect((await cart.setItem(id, 'bowl:default', 'set', 0)).lines).toEqual([]);
  });

  it('survives a page load (the same store), and clears', async () => {
    const store = memoryStore();
    await storyCart(V, store).add('bowl:default');
    const again = storyCart(V, store);
    expect(again.current()!.count).toBe(1);
    again.clear();
    expect(again.current()).toBeNull();
  });

  it('keeps a line across story pages: another page lists it by its snapshot, and the page that shows it has the last word', async () => {
    const store = memoryStore();
    await storyCart(V, store).add('bowl:default');
    // another page, without the bowl: the line stays, and its quantity can change there
    const other = storyCart([V[1]!], store);
    await other.add('candles:70x110mm');
    expect(other.current()!.lines.map((l) => [l.variant_id, l.qty])).toEqual([
      ['bowl:default', 1],
      ['candles:70x110mm', 1],
    ]);
    const { id } = other.current()!;
    expect((await other.setItem(id, 'bowl:default', 'set', 3)).subtotal_agorot).toBe(3 * 7900 + 19900);
    // a page where the bowl is no longer sold: it drops out there
    const sold = storyCart([{ ...V[0]!, available: false }, V[1]!], store);
    expect(sold.current()!.lines.map((l) => l.variant_id)).toEqual(['candles:70x110mm']);
    // a snapshot that is not a variant's shape (storage edited by hand) is not trusted
    store.set('hd.story.cart', JSON.stringify({ id, items: [{ variant_id: 'x', pack: 'set', qty: 1, v: { variant_id: 'x', price_agorot: 'free' } }] }));
    expect(storyCart([], store).current()!.lines).toEqual([]);
  });

  it('works when the storage throws or drops writes (a private window): the cart lives for this page', async () => {
    const broken: KeyValue = {
      get: () => {
        throw new Error('denied');
      },
      set: () => {
        throw new Error('denied');
      },
      remove: () => undefined,
    };
    const safe: KeyValue = {
      get: (k) => {
        try {
          return broken.get(k);
        } catch {
          return null;
        }
      },
      set: (k, v) => {
        try {
          broken.set(k, v);
        } catch {
          /* dropped */
        }
      },
      remove: () => undefined,
    };
    for (const store of [safe, broken]) {
      const cart = storyCart(V, store);
      await cart.add('bowl:default');
      const c = await cart.add('bowl:default');
      expect(c.count).toBe(2);
      expect(cart.current()!.subtotal_agorot).toBe(15800);
      cart.clear();
      expect(cart.current()).toBeNull();
    }
  });

  it('sells a single piece only where the supplier offers one (SET1), at its own price', async () => {
    const sets: StoryVariant[] = [{ ...V[1]!, unit_price_agorot: 10900 }, V[0]!];
    const cart = storyCart(sets, memoryStore());
    await cart.add('candles:70x110mm');
    const c = await cart.add('candles:70x110mm', 1, 'unit');
    expect(c.lines.map((l) => [l.pack, l.pack_qty, l.unit_price_agorot])).toEqual([
      ['set', 2, 19900],
      ['unit', 1, 10900],
    ]);
    expect(c.subtotal_agorot).toBe(30800);
    // the bowl is one piece: no single-piece line
    await expect(cart.add('bowl:default', 1, 'unit')).rejects.toMatchObject({ status: 422, code: 'pack_unavailable' });
  });

  it('changes a quantity, removes a line, and adds the whole look: what is not for sale is skipped and named', async () => {
    const cart = storyCart(V, memoryStore());
    const look = await cart.addLook(['bowl:default', 'rug:200x300+square', 'candles:70x110mm', 'nope']);
    expect(look.added).toEqual(['bowl:default', 'candles:70x110mm']);
    expect(look.skipped).toEqual(['rug:200x300+square', 'nope']);
    expect(look.cart!.count).toBe(2);
    expect((await cart.setQty('bowl:default', 'set', 3)).count).toBe(4);
    expect((await cart.setQty('bowl:default', 'set', 99)).lines[0]!.qty).toBe(MAX_QTY);
    cart.remove('bowl:default', 'set');
    expect(cart.current()!.lines.map((l) => l.variant_id)).toEqual(['candles:70x110mm']);
  });

  it('reads a line from storage, never trusts it: 1–20 whole units, else no line (QA on S3–S5, ת3)', async () => {
    const store = memoryStore();
    await storyCart(V, store).add('bowl:default');
    const saved = JSON.parse(store.get('hd.story.cart')!) as { id: string; items: Record<string, unknown>[] };
    const line = saved.items[0]!;
    saved.items = [
      { ...line, qty: -2 },
      { ...line, qty: 2.5 },
      { ...line, qty: '3' },
      { ...line, qty: 0 },
      { ...line, pack: 'crate' },
      { ...line, variant_id: 'candles:70x110mm', qty: 999 },
    ];
    store.set('hd.story.cart', JSON.stringify(saved));
    const c = storyCart(V, store).current()!;
    expect(c.lines.map((l) => [l.variant_id, l.qty])).toEqual([['candles:70x110mm', MAX_QTY]]);
    expect(c.subtotal_agorot).toBe(19900 * MAX_QTY);
  });

  it('holds a line whose product stopped being sold (PRE1): named, out of the sum, never charged', async () => {
    const store = memoryStore();
    await storyCart(V, store).add('bowl:default');
    await storyCart(V, store).add('candles:70x110mm');
    const later = storyCart([{ ...V[0]!, available: false }, V[1]!], store);
    expect(later.current()!.lines.map((l) => l.variant_id)).toEqual(['candles:70x110mm']);
    expect(later.current()!.subtotal_agorot).toBe(19900);
    expect(later.held()).toEqual([{ variant_id: 'bowl:default', pack: 'set', qty: 1, name_he: 'קערה', option_he: null }]);
    later.remove('bowl:default', 'set');
    expect(later.held()).toEqual([]);
  });

  it('the whole look twice adds nothing the second time (QA on S4)', async () => {
    const cart = storyCart(V, memoryStore());
    await cart.addLook(['bowl:default', 'candles:70x110mm']);
    const again = await cart.addLook(['bowl:default', 'candles:70x110mm']);
    expect(again.added).toEqual([]);
    expect(again.already).toEqual(['bowl:default', 'candles:70x110mm']);
    expect(cart.current()!.count).toBe(2);
  });

  it('a product the frame shows twice goes into the look twice (register v4, G-ED.6)', async () => {
    const cart = storyCart(V, memoryStore());
    const look = await cart.addLook(['bowl:default*2', 'candles:70x110mm']);
    expect(look.added).toEqual(['bowl:default', 'candles:70x110mm']);
    expect(look.units).toBe(3);
    expect(cart.current()!.lines.map((l) => [l.variant_id, l.qty])).toEqual([
      ['bowl:default', 2],
      ['candles:70x110mm', 1],
    ]);
    // a count it cannot read is one; the cap holds
    const other = storyCart(V, memoryStore());
    await other.addLook(['bowl:default*x', 'candles:70x110mm*999']);
    expect(other.current()!.lines.map((l) => l.qty)).toEqual([1, MAX_QTY]);
  });

  it('another tab that ordered and emptied the cart has the last word: the next add starts a new cart (QA on S4)', async () => {
    const store = memoryStore();
    const tabA = storyCart(V, store);
    const tabB = storyCart(V, store);
    await tabB.add('bowl:default');
    tabA.clear(); // tab A placed the order
    const c = await tabB.add('candles:70x110mm');
    expect(c.lines.map((l) => l.variant_id)).toEqual(['candles:70x110mm']);
  });

  it('strict (the checkout): a line the page does not list, or lists as not sold, is held and never charged (QA on S4)', async () => {
    const store = memoryStore();
    await storyCart(V, store).add('bowl:default');
    await storyCart(V, store).add('candles:70x110mm');
    // the checkout knows the candles only, by price and sale, with no names: the bowl (a snapshot) is held
    const table: StoryVariant[] = [{ ...V[1]!, name_he: '', product_id: '' }];
    const co = storyCart(table, store, 'hd.story.cart', { strict: true });
    expect(co.current()!.lines.map((l) => [l.variant_id, l.name_he])).toEqual([['candles:70x110mm', 'פמוטים']]);
    expect(co.current()!.subtotal_agorot).toBe(19900);
    expect(co.held().map((h) => h.variant_id)).toEqual(['bowl:default']);
  });

  it('formats prices exactly as the site does', () => {
    for (const a of [100, 4900, 7900, 19900, 129900, 1234567, 12345, 99]) expect(priceHe(a), String(a)).toBe(formatIls(a));
  });
});
