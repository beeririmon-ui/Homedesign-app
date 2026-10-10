/** Product gallery (FR-I): the render first with a visible "render" note, the supplier photo after it, carousel semantics. */
import { describe, it, expect } from 'vitest';
import { h } from 'preact';
import { renderToString } from 'preact-render-to-string';
import { ProductGallery, type GalleryImage } from '../src/components/ProductGallery';

const render: GalleryImage = {
  kind: 'render',
  src: '/media/rooms/living-room/nordic/M0/slots/vase/1.product.1920.webp',
  alt: 'הדמיה: אגרטל קרמיקה, לבן בחדר',
  width: 600,
  height: 600,
  label: 'הדמיה בחדר',
  caption: 'כך המוצר נראה בחדר (המוצר מרונדר). התמונה המקורית מהספק בתמונה הבאה.',
};
const supplier: GalleryImage = {
  kind: 'supplier',
  src: '/media/products/vase-a/supplier.800.webp',
  alt: 'תמונת הספק: אגרטל קרמיקה, לבן',
  width: 800,
  height: 800,
  label: 'תמונת הספק',
  caption: 'התמונה המקורית מהספק.',
};

describe('product gallery', () => {
  it('shows the render first, says it is a render, and the supplier photo after it', () => {
    const html = renderToString(h(ProductGallery, { images: [render, supplier], id: 'p-vase-a' }));
    const iRender = html.indexOf('data-kind="render"');
    const iSupplier = html.indexOf('data-kind="supplier"');
    expect(iRender).toBeGreaterThan(-1);
    expect(iSupplier).toBeGreaterThan(iRender);
    expect(html).toContain('>הדמיה</span>');
    expect(html).toContain('המוצר מרונדר');
    expect(html).toContain('alt="תמונת הספק: אגרטל קרמיקה, לבן"');
    expect(html).toContain('src="/media/products/vase-a/supplier.800.webp"');
    expect(html).toContain('width="800" height="800"');
    expect(html).toContain('התמונה המקורית מהספק');
  });

  it('is an accessible carousel: labelled slides, previous / next buttons, thumbnails and a live region', () => {
    const html = renderToString(h(ProductGallery, { images: [render, supplier], id: 'p-vase-a' }));
    expect(html).toContain('aria-roledescription="carousel"');
    expect(html).toContain('aria-label="תמונות המוצר"');
    expect(html).toContain('aria-roledescription="slide"');
    expect(html).toContain('aria-label="1 מתוך 2: הדמיה בחדר"');
    expect(html).toContain('aria-label="2 מתוך 2: תמונת הספק"');
    expect(html).toMatch(/<button[^>]*aria-label="התמונה הקודמת"[^>]*aria-disabled="true"/);
    expect(html).toMatch(/<button[^>]*aria-label="התמונה הבאה"/);
    expect(html).not.toMatch(/aria-label="התמונה הבאה"[^>]*aria-disabled/);
    expect(html).toMatch(/aria-label="תמונה 1: הדמיה בחדר"[^>]*aria-current="true"/);
    expect(html).toContain('aria-label="תמונה 2: תמונת הספק"');
    expect(html).toContain('aria-live="polite"');
    // the strip is a scrollable region: focusable and named
    expect(html).toMatch(/class="gallery-track"[^>]*tabindex="0"/);
    // thumbnails are decorative, alt="" (the button is labelled); the renderer writes an empty attribute as `alt`
    expect((html.match(/<img src="[^"]+" alt(?:=""|\s)/g) ?? []).length).toBe(2);
  });

  it('with the render alone there is nothing to navigate', () => {
    const html = renderToString(h(ProductGallery, { images: [render], id: 'p-vase-a' }));
    expect(html).not.toContain('gallery-nav');
    expect(html).not.toContain('tabindex');
    expect(html).toContain('aria-label="1 מתוך 1: הדמיה בחדר"');
  });
});
