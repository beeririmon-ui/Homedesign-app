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

  it('formats prices exactly as the site does', () => {
    for (const a of [100, 4900, 7900, 19900, 129900, 1234567, 12345, 99]) expect(priceHe(a), String(a)).toBe(formatIls(a));
  });
});
