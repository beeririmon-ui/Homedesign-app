/**
 * Layer 2's detail page model (web/src/story/detail-model.ts): the picker's cascade over the house's SKUs, the address
 * that names an option, the picture a SKU shows (close-up, supplier photo, the frame's crop, nothing), and the reason
 * there is no add button.
 */
import { describe, expect, it } from 'vitest';
import { choose, creditOf, fromQuery, photoOf, storyNote, storySku, toQuery, whyOf, type DetailData, type DSku } from '../src/story/detail-model';

const img = (n: string) => ({ src: `/m/${n}.480.webp`, srcset: `/m/${n}.480.webp 480w`, w: 480, h: 480 });
const sku = (color: string, size: string, o: Partial<DSku> = {}): DSku => ({
  key: `${color}+${size}`,
  values: { color, size },
  label_he: `${color}, ${size}`,
  variant_id: `p:${color}+${size}`,
  price_agorot: size === '50x50' ? 5900 : 4900,
  price_he: size === '50x50' ? '₪ 59' : '₪ 49',
  available: true,
  sellable: true,
  size_he: size,
  days: [9, 23],
  image: null,
  image_of_option: true,
  closeup: null,
  ...o,
});
const base: DetailData = {
  product: 'p',
  name_he: 'ציפית כרית בוקלה, תה חלב',
  material_he: 'בוקלה',
  status: 'available',
  set_qty: 1,
  style_he: 'מודרני חם',
  axes: [
    {
      id: 'color',
      name_he: 'צבע',
      values: [
        { id: 'white', label_he: 'לבן', hex: '#fff' },
        { id: 'tea', label_he: 'תה חלב', hex: '#c9ae8f' },
      ],
    },
    {
      id: 'size',
      name_he: 'מידה',
      values: [
        { id: '50x50', label_he: '50×50', hex: null },
        { id: '30x50', label_he: '30×50', hex: null },
      ],
    },
  ],
  skus: [
    sku('white', '50x50', { image: 0 }),
    sku('white', '30x50'),
    sku('tea', '50x50', { image: 1 }),
    sku('tea', '30x50', { available: false, sellable: false }),
  ],
  images: [img('white'), img('tea')],
  story_key: 'tea+50x50',
  crop: img('crop'),
  crop_title_he: 'דירת אדריכלית',
  marks_he: { final_test: 'טיוטה / בדיקה' },
};

describe('the detail page model', () => {
  it('starts on the option the story shows, and the address names any other option', () => {
    expect(storySku(base).key).toBe('tea+50x50');
    expect(fromQuery(base, '').key).toBe('tea+50x50');
    expect(fromQuery(base, '?color=white&size=30x50').key).toBe('white+30x50');
    expect(fromQuery(base, '?color=nope&size=30x50').key).toBe('tea+50x50');
    expect(toQuery(base, storySku(base))).toBe('');
    const white = base.skus[1]!;
    expect(fromQuery(base, toQuery(base, white)).key).toBe(white.key);
  });

  it('chooses with the site picker rules: an option out of stock is never chosen, the next axis moves to one that is', () => {
    const story = storySku(base);
    expect(choose(base, story, 1, '30x50').key).toBe('tea+50x50'); // tea 30×50 is out of stock: the choice does not happen
    const white = choose(base, story, 0, 'white');
    expect(white.key).toBe('white+50x50');
    expect(choose(base, white, 1, '30x50').key).toBe('white+30x50');
    // from white 30×50 back to tea: 30×50 does not exist in stock for tea, so the size moves to the first that does
    expect(choose(base, base.skus[1]!, 0, 'tea').key).toBe('tea+50x50');
  });

  it('shows the supplier photo of the option, else the frame crop for the story option, else nothing', () => {
    expect(photoOf(base, storySku(base))).toMatchObject({ kind: 'supplier', image: img('tea') });
    const noPhoto = { ...base, skus: base.skus.map((k) => ({ ...k, image: null })) };
    expect(photoOf(noPhoto, storySku(noPhoto))).toMatchObject({ kind: 'frame', image: img('crop') });
    expect(photoOf(noPhoto, noPhoto.skus[0]!)).toMatchObject({ kind: 'none', image: null });
    expect(photoOf(base, base.skus[1]!).caption).toContain('צילום הספק עוד לא הורד');
    // the listing's main photo (the card names none for the option) does not claim to be the option
    const main = { ...base, skus: base.skus.map((k) => (k.key === 'tea+50x50' ? { ...k, image_of_option: false } : k)) };
    expect(photoOf(main, storySku(main)).caption).toBe('צילום הספק.');
  });

  it('says why there is no add button, and names the story option when the choice is another', () => {
    expect(whyOf(base, storySku(base))).toBe('');
    expect(whyOf(base, base.skus[3]!)).toBe('המלאי אינו זמין כעת.');
    expect(whyOf({ ...base, status: 'unpriced' }, storySku(base))).toContain('המחיר עוד לא נקבע');
    expect(storyNote(base, storySku(base))).toBeNull();
    expect(storyNote(base, base.skus[0]!)).toBe('בסיפור מוצגת האפשרות tea, 50x50.');
    expect(creditOf(base, base.skus[1]!)).toBe('בוקלה · 30x50 · ₪ 49');
    expect(creditOf({ ...base, status: 'unpriced' }, { ...storySku(base), price_he: null })).toBe('בוקלה · 50x50 · המחיר עוד לא נקבע');
  });

  it('a product without options has one SKU and no address', () => {
    const one: DetailData = { ...base, axes: [], skus: [{ ...sku('x', 'y'), key: 'default', values: {}, label_he: null }], story_key: 'default' };
    expect(fromQuery(one, '?color=white').key).toBe('default');
    expect(toQuery(one, one.skus[0]!)).toBe('');
    expect(storyNote(one, one.skus[0]!)).toBeNull();
  });
});
