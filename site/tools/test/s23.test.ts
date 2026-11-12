/**
 * S23, QA S22 ת85: the price checks of tools/build-catalog.ts (tools/lib/price-checks.ts), on made-up cards: the SKU a
 * studio price was set for against the default SKU, and the size ladder. Warnings only: no price is changed.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { ladderInversions, sizeArea, skuAnchorIssue } from '../lib/price-checks';
import { sitePath } from '../lib/paths';

describe('S23 ת85: the SKU a studio price was set for', () => {
  const anchor = { sku: 'SKU-200x300', retail_ils: 1299, retail_src: 'initial-2026-10-11' };
  it('the default is the SKU of the price: nothing to say', () => {
    expect(skuAnchorIssue({ retail_ils: 1299, retail_src: 'initial-2026-10-11' }, 'SKU-200x300', anchor)).toBeNull();
    expect(skuAnchorIssue({ retail_ils: 269, retail_src: 'sku-move-2026-11-12', retail_sku: 'SKU-B' }, 'SKU-B', undefined)).toBeNull();
  });
  it('the default moved under an unchanged price: a warning naming both SKUs', () => {
    const w = skuAnchorIssue({ retail_ils: 1299, retail_src: 'initial-2026-10-11' }, 'SKU-230x330', anchor);
    expect(w?.set_for).toBe('SKU-200x300');
    expect(w?.what).toMatch(/set for SKU SKU-200x300; the default SKU is now SKU-230x330/);
  });
  it('the entry’s own retail_sku wins over the anchor list', () => {
    expect(skuAnchorIssue({ retail_ils: 1299, retail_src: 'initial-2026-10-11', retail_sku: 'SKU-230x330' }, 'SKU-230x330', anchor)).toBeNull();
    expect(skuAnchorIssue({ retail_ils: 1299, retail_src: 'x', retail_sku: 'SKU-A' }, 'SKU-B', undefined)?.set_for).toBe('SKU-A');
  });
  it('a price set again without saying its SKU: a warning (the anchor no longer speaks for it)', () => {
    expect(skuAnchorIssue({ retail_ils: 1499, retail_src: 'studio' }, 'SKU-200x300', anchor)?.what).toMatch(/set again since its anchor/);
    expect(skuAnchorIssue({ retail_ils: 99, retail_src: 'studio' }, 'SKU-1', undefined)?.what).toMatch(/no retail_sku, no anchor/);
  });
  it('the anchor list ships with the site, one per studio-priced card with options, and names a SKU each', () => {
    const doc = JSON.parse(readFileSync(sitePath('tools/price-anchors.json'), 'utf8')) as { anchors: Record<string, { sku: string; retail_ils: number }> };
    const rows = Object.values(doc.anchors);
    expect(rows.length).toBeGreaterThan(100);
    expect(rows.every((r) => typeof r.sku === 'string' && r.sku.length > 3 && r.retail_ils > 0)).toBe(true);
  });
});

describe('S23 ת85: the size ladder', () => {
  it('reads a size from the value or its label', () => {
    expect(sizeArea('200x300', '200×300 ס"מ')).toBe(60000);
    expect(sizeArea('150', 'קוטר 150 ס"מ')).toBeCloseTo(Math.PI * 75 ** 2);
    expect(sizeArea('round-180')).toBeCloseTo(Math.PI * 90 ** 2);
    expect(sizeArea('linen', 'פשתן')).toBeNull();
  });
  const axes = [
    { id: 'size', values: [{ id: '150x200' }, { id: '200x300' }, { id: '230x330' }] },
    { id: 'color', values: [{ id: 'natural' }, { id: 'grey' }] },
  ];
  const row = (size: string, color: string, ils: number) => ({ values: { size, color }, retail_agorot: ils * 100 });
  it('a smaller size above a larger one, the colour the same: one warning per axis, with its worst pair and the count', () => {
    const out = ladderInversions(axes, [
      row('150x200', 'natural', 4909),
      row('200x300', 'natural', 2959),
      row('230x330', 'natural', 1299),
      row('150x200', 'grey', 900),
      row('230x330', 'grey', 1100),
    ]);
    expect(out).toEqual([{ axis: 'size', smaller: '150x200', smaller_ils: 4909, larger: '230x330', larger_ils: 1299, pairs: 3 }]);
  });
  it('a ladder that rises (or equal prices, or two colours compared) says nothing', () => {
    expect(
      ladderInversions(axes, [
        row('150x200', 'natural', 900),
        row('200x300', 'natural', 900),
        row('230x330', 'natural', 1299),
        row('150x200', 'grey', 2000),
        row('230x330', 'natural', 1299),
      ]),
    ).toEqual([]);
    expect(
      ladderInversions(
        [{ id: 'color', values: [{ id: 'a' }, { id: 'b' }] }],
        [
          { values: { color: 'a' }, retail_agorot: 9 },
          { values: { color: 'b' }, retail_agorot: 1 },
        ],
      ),
    ).toEqual([]);
  });
});
