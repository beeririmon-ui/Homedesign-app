/** Neutral product addresses (S5): the supplier and its product number never reach an address; the slug is stable. */
import { describe, expect, it } from 'vitest';
import { productPath, productSlug, shortId, shortIdOf, slugIndex } from '../src/product-url';

describe('product addresses', () => {
  it('drops the supplier and the long product number, keeps what the product is, ends in a stable short id', () => {
    const s = productSlug('vase-aliexpress-vintage-distressed-clay-vase-589009');
    expect(s).toMatch(/^vase-vintage-distressed-clay-vase-[0-9a-z]{5}$/);
    expect(productSlug('cushions-cj-boucle-teddy')).toMatch(/^cushions-boucle-teddy-[0-9a-z]{5}$/);
    expect(productSlug('planter-zendrop-seagrass-belly-basket-45')).toMatch(/^planter-seagrass-belly-basket-[0-9a-z]{5}$/);
    // S8: no size in a slug
    expect(productSlug('planter-zendrop-seagrass-belly-38x34')).not.toMatch(/38x34/);
    expect(productSlug('pendant-cj-silk-ribbed-pumpkin-40')).toMatch(/^pendant-silk-ribbed-pumpkin-[0-9a-z]{5}$/);
    // the same card, the same address, every time and in every runtime
    expect(productSlug('cushions-cj-boucle-teddy')).toBe(productSlug('cushions-cj-boucle-teddy'));
    expect(shortIdOf(s)).toBe(shortId('vase-aliexpress-vintage-distressed-clay-vase-589009'));
    expect(productPath('cushions-cj-boucle-teddy')).toBe(`/p/${productSlug('cushions-cj-boucle-teddy')}/`);
  });

  it('resolves the slug and the old address (the card id), and refuses an unknown one', () => {
    const ix = slugIndex(['cushions-cj-boucle-teddy', 'bowl-cj-matte-black-bowl-20']);
    expect(ix.resolve(productSlug('bowl-cj-matte-black-bowl-20'))).toEqual({ id: 'bowl-cj-matte-black-bowl-20', old: false });
    expect(ix.resolve('cushions-cj-boucle-teddy')).toEqual({ id: 'cushions-cj-boucle-teddy', old: true });
    expect(ix.resolve('nope')).toBeNull();
  });
});
