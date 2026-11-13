/**
 * MOCK1: the tour's data and the pure parts of its engine. The effects themselves are held to their seams in the
 * browser (e2e/mock1.spec.ts); here: the designer's curves, the tour's room as tools/make-tour.ts wrote it, and the
 * wheel's words for one option.
 */
import { readFileSync } from 'node:fs';
import { beforeAll, describe, expect, it } from 'vitest';
import { wheelCountHe } from '../src/set-copy';

type Slot = {
  id: string;
  rect: number[];
  depth_m: number;
  order_a: number;
  anchors: number[][];
  options: { position: number; box: number[]; product_id: string | null; name_he: string | null; set: boolean }[];
};
type Tour = { native: number; cover: number; camera: { frame: number[] }; slots: Slot[] };
const tour = JSON.parse(readFileSync(new URL('../../.generated/tour.living-room.warm-modern.json', import.meta.url), 'utf8')) as Tour;

describe('MOCK1: the tour room (tools/make-tour.ts)', () => {
  it('holds the phase 2 layers: 13 slots, the 12 default products and their 10 variants, and the three cushion sets', () => {
    expect(tour.slots).toHaveLength(13);
    const products = tour.slots.filter((s) => s.id !== 'cushions');
    expect(products.reduce((n, s) => n + s.options.length - 1, 0)).toBe(10);
    expect(tour.slots.find((s) => s.id === 'cushions')!.options.map((o) => o.set)).toEqual([true, true, true]);
    // the bowl's third option and the iron candle holders stay out (the brief)
    expect(tour.slots.find((s) => s.id === 'bowl')!.options).toHaveLength(2);
    expect(tour.slots.find((s) => s.id === 'candle-holders')!.options).toHaveLength(2);
  });

  it('puts every layer back on its own pixels: a slot rectangle is whole pixels of the canvas, and holds every option', () => {
    const h = Math.round((tour.native * 9) / 16);
    for (const s of tour.slots) {
      for (const [v, size] of [
        [s.rect[0]!, tour.native],
        [s.rect[1]!, tour.native],
        [s.rect[2]!, h],
        [s.rect[3]!, h],
      ] as const)
        expect(Math.abs(v * size - Math.round(v * size)), `${s.id} ${v}`).toBeLessThan(1e-6);
      for (const o of s.options) {
        expect(o.box[0]! >= s.rect[0]! && o.box[1]! <= s.rect[1]! && o.box[2]! >= s.rect[2]! && o.box[3]! <= s.rect[3]!, `${s.id} ${o.position}`).toBe(true);
      }
      for (const [u, v] of s.anchors) expect(u! >= 0 && u! <= 1 && v! >= 0 && v! <= 1, `${s.id} anchor`).toBe(true);
    }
  });

  it("gives every product its own code in the display's mask (its depth, 40 to the metre) and its own turn in the burst", () => {
    const codes = tour.slots.map((s) => Math.round(s.depth_m * 40));
    expect(new Set(codes).size).toBe(tour.slots.length);
    expect(codes.every((c) => c > 0 && c < 256)).toBe(true);
    expect([...tour.slots.map((s) => s.order_a)].sort((a, b) => a - b)).toEqual(tour.slots.map((_, i) => i + 1));
  });

  it('names a product only from the shop: a card the shop does not sell yet has no name and no price here', () => {
    for (const s of tour.slots) for (const o of s.options) if (!o.product_id && !o.set) expect(o.name_he, `${s.id} ${o.position}`).toBeNull();
    expect(tour.cover).toBeGreaterThan(0.1);
    expect(tour.cover).toBeLessThan(0.6);
  });
});

describe("MOCK1: the designer's curves and the wheel's words", () => {
  let bezier: (typeof import('../src/tour/engine'))['bezier'];
  beforeAll(async () => {
    Object.assign(globalThis, { __ARTIFACT__: false, __MEDIA_BASE__: '/media/', __HD_PUBLIC__: false });
    ({ bezier } = await import('../src/tour/engine'));
  });

  it('a curve is exactly 0 at 0 and 1 at 1 (an effect starts on the frame before it and ends on the frame after it)', () => {
    for (const c of [bezier(0.65, 0, 0.35, 1), bezier(0.16, 1, 0.3, 1), bezier(0.7, 0, 0.84, 0)]) {
      expect(c(0)).toBe(0);
      expect(c(1)).toBe(1);
      let last = 0;
      for (let i = 1; i <= 100; i++) {
        const y = c(i / 100);
        expect(y).toBeGreaterThanOrEqual(last - 1e-9);
        expect(y).toBeLessThanOrEqual(1 + 1e-9);
        last = y;
      }
    }
  });

  it('matches the CSS curve it names', () => {
    // cubic-bezier(0.65, 0, 0.35, 1) is symmetric about (0.5, 0.5)
    const c = bezier(0.65, 0, 0.35, 1);
    expect(c(0.5)).toBeCloseTo(0.5, 5);
    expect(c(0.25) + c(0.75)).toBeCloseTo(1, 5);
  });

  it('one option on the wheel is "גרסה אחת", not "1 גרסאות"', () => {
    expect(wheelCountHe(1, false)).toBe('גרסה אחת');
    expect(wheelCountHe(1, true)).toBe('סט אחד');
    expect(wheelCountHe(3, false)).toBe('3 גרסאות');
    expect(wheelCountHe(3, true)).toBe('3 סטים');
  });
});
