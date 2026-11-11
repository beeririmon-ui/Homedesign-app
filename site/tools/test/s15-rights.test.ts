/**
 * S15, public honesty (master-designer §5; brief briefs/site-s15-copy-seo-2026-11-11.md task 4):
 *  - the owner's launch item "supplier image rights": the public build ships no supplier picture whose rights are not
 *    confirmed; its manifest lists none, and the build check fails on a file of one or on a page that names one;
 *  - "הדפס במרקם" only when the card says the print is embossed or textured; a guess the card hedges is no material.
 */
import { describe, expect, it } from 'vitest';
import type { SupplierImageManifest } from '@hd/shared';
import { manifestFiles, publicManifest, rightsIssues, shipsPublicly, withheld, type Rights } from '../lib/image-rights';
import { materialHe, materialsHe } from '../lib/hebrew';

const photo = (id: string, usage_rights: Rights) => ({ src: `products/${id}/photo.800`, width: 800, height: 800, usage_rights });
const M: SupplierImageManifest = {
  generated_at: '2026-11-11T00:00:00Z',
  width: 800,
  products: { 'vase-a': photo('vase-a', 'confirmed'), 'rug-b': photo('rug-b', 'unclear'), 'lamp-c': photo('lamp-c', 'none') },
  options: {
    'vase-a': { files: [{ name: 'opt-0123456789', width: 800, height: 800, artifact: true }], sku: [0] },
    'rug-b': {
      files: [
        { name: 'opt-aaaaaaaaaa', width: 800, height: 800, artifact: true },
        { name: 'opt-bbbbbbbbbb', width: 800, height: 800, artifact: false },
      ],
      sku: [0, 1],
    },
  },
  missing: [],
};
const RIGHTS: Record<string, Rights> = { 'vase-a': 'confirmed', 'rug-b': 'unclear', 'lamp-c': 'none' };

describe('supplier image rights: the public build', () => {
  it('only confirmed rights ship; unclear and none do not', () => {
    expect(shipsPublicly('confirmed')).toBe(true);
    expect(shipsPublicly('unclear')).toBe(false);
    expect(shipsPublicly('none')).toBe(false);
    expect(shipsPublicly(undefined)).toBe(false);
  });

  it('the public manifest lists only the confirmed product’s photo and its option pictures', () => {
    const p = publicManifest(M);
    expect(Object.keys(p.products)).toEqual(['vase-a']);
    expect(Object.keys(p.options ?? {})).toEqual(['vase-a']);
    expect(manifestFiles(p)).toEqual(['products/vase-a/photo.800.webp', 'products/vase-a/opt-0123456789.800.webp']);
    // the full manifest is not changed (behind the flag nothing changes)
    expect(Object.keys(M.products)).toHaveLength(3);
  });

  it('what a public build withholds: the products, the photos and the option pictures, by rights', () => {
    expect(withheld(M)).toEqual({ products: ['lamp-c', 'rug-b'], photos: 2, optionFiles: 2, byRights: { unclear: 1, none: 1 } });
  });

  it('the build check: a file of a withheld product, a page naming one, or a public manifest listing one fail', () => {
    const files = ['index.html', 'assets/index-abc.js', 'media/products/vase-a/photo.800.webp', 'media/products/rug-b/opt-aaaaaaaaaa.800.webp'];
    const text: Record<string, string> = {
      'index.html': '<img src="/media/products/vase-a/photo.800.webp"><img src="/media/products/lamp-c/photo.800.webp">',
      'assets/index-abc.js': 'const a="products/rug-b/opt-bbbbbbbbbb.800.webp"',
    };
    const issues = rightsIssues(
      files,
      (f) => text[f] ?? '',
      (id) => RIGHTS[id],
      M,
    );
    expect(issues.map((i) => i.where).sort()).toEqual(
      [
        'assets/index-abc.js',
        'index.html',
        'media/products/rug-b/opt-aaaaaaaaaa.800.webp',
        'supplier-images.public.json',
        'supplier-images.public.json',
      ].sort(),
    );
    // the public manifest and only confirmed files and names: no issue
    const clean = rightsIssues(
      ['index.html', 'media/products/vase-a/photo.800.webp'],
      () => '<img src="/media/products/vase-a/opt-0123456789.800.webp">',
      (id) => RIGHTS[id],
      publicManifest(M),
    );
    expect(clean).toEqual([]);
    // a folder of a product the shop does not know is not shipped either
    expect(
      rightsIssues(
        ['media/products/old-id/photo.800.webp'],
        () => '',
        (id) => RIGHTS[id],
      ),
    ).toHaveLength(1);
  });
});

describe('materials: "הדפס במרקם" only when the card says it (§5)', () => {
  it('a print the card calls embossed or textured', () => {
    // the Morandi triptych's card
    expect(materialHe("printed embossed film / 'texture painting' panel (supplier: 'Painting material: embossed film')")).toBe('הדפס במרקם');
  });
  it('a flat print is "הדפס", a canvas the card does not call a print is "קנבס"', () => {
    expect(materialHe('canvas print (HD inkjet)')).toBe('הדפס');
    expect(materialHe('printed canvas')).toBe('הדפס');
    expect(materialHe('Painting material: canvas')).toBe('קנבס');
    expect(materialHe('canvas, hand-painted acrylic/oil texture (per listing)')).toBe('קנבס');
    expect(materialHe('cotton canvas print')).toBe('כותנה');
  });
  it('a texture alone is no print: wood stays wood, a glaze is nothing the list names', () => {
    expect(materialHe('texture of material: woodiness')).toBe('עץ');
    expect(materialHe('matte sand-texture glaze')).toBeNull();
  });
  it('a guess the card hedges is not a claim: the magazine holder is metal, not "הדפס במרקם"', () => {
    expect(materialHe('cane/rattan-look perforated sling (material not stated - possibly PVC/printed)')).toBeNull();
    expect(materialsHe(['black iron frame', 'cane/rattan-look perforated sling (material not stated - possibly PVC/printed)'])).toEqual(['מתכת']);
  });
});
