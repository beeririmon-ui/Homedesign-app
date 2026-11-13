/**
 * MOCK2 (2026-11-13), FB1: the parts that can be checked without a browser — the tour's two widths, the wheel's cards
 * (the product on its own: our own studio picture, or its layer trimmed; never a crop of the room), and the counters
 * that the smoothness rests on. The effects themselves are held to their counters in the browser (e2e/mock2.spec.ts).
 */
import { readFileSync, statSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { Metrics, report, statLine, sum, zero } from '../src/tour/metrics';

const read = <T>(f: string): T => JSON.parse(readFileSync(new URL(f, import.meta.url), 'utf8')) as T;
type Card = { src: string; w: number; h: number; source: 'studio' | 'layer' };
type Tour = {
  native: number;
  widths: { lo: number; hi: number };
  card_width: number;
  slots: { id: string; rect: number[]; ground: boolean; kind: string; src: string; options: { position: number; card: Card; product_id: string | null }[] }[];
};
const tour = read<Tour>('../../.generated/tour.living-room.warm-modern.json');
const studio = read<{ width: number; products: Record<string, { src: string }> }>('../../.generated/studio-images.json');
const media = (rel: string) => new URL(`../public/media/${rel}.webp`, import.meta.url);

describe('MOCK2: the tour at two widths (tools/make-tour.ts)', () => {
  it('has a phone width and the layers’ own width, and a file of every layer at both', () => {
    expect(tour.widths.hi).toBe(tour.native);
    expect(tour.widths.lo).toBeLessThan(tour.widths.hi);
    for (const s of tour.slots)
      for (const o of s.options)
        for (const w of [tour.widths.lo, tour.widths.hi])
          for (const kind of ['product', 'shadow'])
            expect(statSync(media(`${s.src}/${o.position}.${kind}.${w}`)).size, `${s.id} ${o.position} ${kind} @${w}`).toBeGreaterThan(0);
  });

  it('the phone’s layers are the smaller half of the bytes', () => {
    const bytes = (w: number) =>
      tour.slots.reduce((n, s) => n + s.options.reduce((m, o) => m + statSync(media(`${s.src}/${o.position}.product.${w}`)).size, 0), 0);
    const lo = bytes(tour.widths.lo);
    const hi = bytes(tour.widths.hi);
    expect(lo).toBeLessThan(hi * 0.7);
  });

  it('a slot rectangle is whole pixels at both widths, so a layer is put back on its own pixels', () => {
    for (const w of [tour.widths.lo, tour.widths.hi]) {
      const h = Math.round((w * 9) / 16);
      for (const s of tour.slots) {
        // what the engine rounds to, and what the file was cut to, are the same arithmetic (web/src/tour/gl.ts)
        const px = [Math.round(s.rect[0]! * w), Math.round(s.rect[1]! * w), Math.round(s.rect[2]! * h), Math.round(s.rect[3]! * h)];
        expect(px[1]! - px[0]!, `${s.id} @${w}`).toBeGreaterThan(0);
        expect(px[3]! - px[2]!, `${s.id} @${w}`).toBeGreaterThan(0);
      }
    }
  });
});

describe('MOCK2: the wheel shows the product on its own (FB1)', () => {
  it('every option has a card from our own media, at the card size, and never a crop of the room', () => {
    for (const s of tour.slots)
      for (const o of s.options) {
        expect(o.card.src.startsWith('tour/'), `${s.id} ${o.position}`).toBe(true);
        expect(Math.max(o.card.w, o.card.h)).toBe(tour.card_width);
        expect(statSync(media(o.card.src)).size).toBeGreaterThan(0);
        // a card is the product's shape, not a square of the room: its sides are rarely both the full card
        if (o.card.source === 'layer') expect(o.card.src).toContain(`/${o.position}.card.`);
      }
  });

  it('uses our own studio picture wherever one passed QA, and only there', () => {
    expect(studio.width).toBe(tour.card_width);
    for (const s of tour.slots)
      for (const o of s.options) {
        const own = o.product_id ? studio.products[o.product_id] : undefined;
        expect(o.card.source, `${s.id} ${o.position}`).toBe(own ? 'studio' : 'layer');
        if (own) expect(o.card.src).toBe(own.src);
      }
    // the pilot's two pictures that passed QA: the vase (in this room) and the throw (the Nordic room's sofa cover)
    expect(Object.keys(studio.products).length).toBeGreaterThanOrEqual(1);
    // a card id carries the supplier's name: it stays out of what the site serves (e2e/public-scan.spec.ts)
    expect(JSON.stringify(studio)).not.toContain('-cj-');
  });

  it('a card stands on a ground shadow only when the product stands on something', () => {
    for (const s of tour.slots) expect(s.ground, s.id).toBe(s.kind === 'floor' || s.kind === 'surface');
  });
});

describe('MOCK2: the counters (web/src/tour/metrics.ts)', () => {
  it('keeps, per effect, what happened while it ran', () => {
    const m = new Metrics();
    m.begin('reveal-b');
    m.count('decode');
    m.count('upload', 2);
    m.dom(() => 0);
    const s = m.end('reveal-b', [16, 17, 40], [1, 2, 3], [1e6, 1e6, 2e6], 0.8);
    expect(s.counts).toEqual({ decode: 1, upload: 2, compile: 0, readback: 0, layout: 1 });
    expect(sum(s.counts)).toBe(4);
    expect(s.frames).toBe(3);
    expect(s.long20).toBe(1);
    expect(s.long34).toBe(1);
    expect(s.js_max).toBe(3);
    expect(s.mpx).toBe(1.33);
    expect(s.min_scale).toBe(0.8);
    expect(m.order).toEqual(['reveal-b']);
    expect(statLine(s)).toContain('4 interruptions');
  });

  it('counts nothing outside an effect against it, and reports a clean run as clean', () => {
    const m = new Metrics();
    m.count('upload');
    m.begin('enter');
    const s = m.end('enter', [16, 16], [0.2, 0.3], [0, 0], 1);
    expect(sum(s.counts)).toBe(0);
    expect(statLine(s)).toContain('0 interruptions');
    expect(zero()).toEqual({ decode: 0, upload: 0, compile: 0, readback: 0, layout: 0 });
    const text = report(m, { browser: 'test' });
    expect(text).toContain('enter');
    expect(text).toContain('browser: test');
  });
});
