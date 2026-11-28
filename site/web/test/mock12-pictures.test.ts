/**
 * MOCK12 (2026-11-28, briefs/site-mock12-wheels-studio-2026-11-28.md), the pure parts:
 *
 *  1. what a product is shown by outside the room (tour/pictures.ts `outside`): its studio picture first, else its card,
 *     else (the room cuts the card) its name; the wheel never gets a cut card;
 *  2. every frame the build wrote: its wheels (several a frame, each with its options on the atlas or as patches), the
 *     options' studio pictures on the frame's studio sheets, and no option whose card the room cuts is shown by it;
 *  3. the girl's print is the one her manifest draws (G1, the bunny set: master-designer, 2026-11-28);
 *  4. .generated/studio-missing.json lists the products still without a studio picture, each once.
 */
import { existsSync, readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { outside, wheelCard } from '../src/tour/pictures';
import type { TourData, TourOption, TourSlot } from '../src/tour/data';

const gen = (f: string) => new URL(`../../.generated/${f}`, import.meta.url);
const read = <T>(f: string): T => JSON.parse(readFileSync(gen(f), 'utf8')) as T;
const FRAMES = ['living-room', 'dining', 'dining-d2', 'bath-b1', 'bath', 'master', 'master-mb1', 'boy', 'girl', 'work'];
const built = FRAMES.every((f) => existsSync(gen(`tour.${f}.warm-modern.json`)));

describe('MOCK12 (FB29): a product outside the room', () => {
  const card = { src: 'tour/x/cards.360', w: 10, h: 10, source: 'layer' as const };
  const studio = { src: 'tour/x/studio.512', w: 512, h: 512, source: 'studio' as const };
  const opt = (o: Partial<TourOption>): TourOption => ({
    position: 1,
    card,
    box: [0, 1, 0, 1],
    product_id: null,
    name_he: null,
    price_agorot: null,
    price_provisional: false,
    available: false,
    dims_he: null,
    set: false,
    ...o,
  });
  const slot = { id: 'vase', name_he: 'אגרטל', lazy: false } as unknown as TourSlot;
  it('is its studio picture first, then its card, then (the room cuts the card) its name', () => {
    expect(outside(slot, opt({ studio }))).toEqual({ kind: 'studio', card: studio });
    expect(outside(slot, opt({ studio, cut: 'occluded' }))).toEqual({ kind: 'studio', card: studio });
    expect(outside(slot, opt({}))).toEqual({ kind: 'card', card });
    expect(outside(slot, opt({ cut: 'occluded' }))).toEqual({ kind: 'name', text: 'אגרטל' });
    expect(outside(slot, opt({ cut: 'frame' }))).toEqual({ kind: 'name', text: 'אגרטל' });
  });
  it('the wheel never gets a cut card', () => {
    expect(wheelCard(slot, opt({ cut: 'occluded' }))).toBeNull();
    expect(wheelCard(slot, opt({ studio, cut: 'occluded' }))).toEqual(studio);
  });
});

describe.skipIf(!built)('MOCK12: the frames the build wrote', () => {
  const frames = Object.fromEntries(FRAMES.map((f) => [f, read<TourData>(`tour.${f}.warm-modern.json`)]));
  it('every frame lists its wheels; each has 2–12 options, on the atlas (3 at most) or as patches; `sample` is the first', () => {
    for (const [id, d] of Object.entries(frames)) {
      const wheels = d.wheels ?? [];
      expect(d.sample ?? undefined, id).toBe(wheels[0]);
      for (const w of wheels) {
        const s = d.slots.find((x) => x.id === w)!;
        expect(s.options.length, `${id} ${w}`).toBeGreaterThanOrEqual(2);
        expect(s.options.length).toBeLessThanOrEqual(12);
        if (s.lazy) expect(s.atlas_opts).toBeUndefined();
        else for (const places of Object.values(s.atlas_opts!)) expect(places).toHaveLength(s.options.length);
        for (const o of s.options) expect(o.variant, `${id} ${w} ${o.position}`).toBeTruthy();
      }
      // a slot with options is a wheel
      for (const s of d.slots) if (s.options.length > 1) expect(wheels, `${id} ${s.id}`).toContain(s.id);
    }
  });
  it('every studio picture is a place on its frame’s studio sheet; a wheel of the FB20 stills keeps them all', () => {
    for (const [id, d] of Object.entries(frames))
      for (const s of d.slots)
        for (const o of s.options)
          if (o.studio) {
            expect(o.studio.source).toBe('studio');
            expect(o.studio.src, id).toMatch(
              new RegExp(`^tour/${id === 'living-room' ? 'living-room/warm-modern/M0-W' : `${id}/warm-modern`}/studio(-\\d+)?\\.512$`),
            );
            expect(o.studio.sprite).toHaveLength(4);
          }
    for (const [id, w] of [
      ['master', 'throw'],
      ['bath', 'hand-towel'],
      ['boy', 'bedspread'],
      ['living-room', 'cushions'],
    ] as const)
      expect(frames[id]!.slots.find((s) => s.id === w)!.options.every((o) => o.studio)).toBe(true);
  });
  it('no product is shown outside the room by a card the room cuts', () => {
    let cut = 0;
    for (const d of Object.values(frames))
      for (const s of d.slots)
        for (const o of s.fixed ? [] : s.options)
          if (o.cut) {
            cut++;
            const p = outside(s, o);
            expect(p.kind === 'name' || p.kind === 'studio').toBe(true);
          }
    expect(cut, 'the house has products its rooms cut (the bedding under its pillows, the curtains at the frame)').toBeGreaterThan(5);
  });
  it('the girl’s print is the one her manifest draws (G1: the bunny set)', () => {
    const s = frames.girl!.slots.find((x) => x.id === 'framed-prints')!;
    expect(s.options[0]!.card_id).toBe('framed-prints-aliexpress-watercolour-bunny-nursery-prints');
  });
  it('studio-missing.json lists each product still without a studio picture once, with where it is seen', () => {
    const m = read<{ count: number; products: { variant: string; card_id: string | null; seen: { room: string; shown: string }[] }[] }>('studio-missing.json');
    expect(m.count).toBe(m.products.length);
    const keys = m.products.map((p) => `${p.card_id}|${p.variant}`);
    expect(new Set(keys).size).toBe(keys.length);
    const withStudio = new Set(
      Object.values(frames).flatMap((d) => d.slots.flatMap((s) => s.options.filter((o) => o.studio).map((o) => `${o.card_id ?? '-'}|${o.variant}`))),
    );
    for (const p of m.products) {
      expect(withStudio.has(`${p.card_id ?? '-'}|${p.variant}`), p.variant).toBe(false);
      expect(p.seen.length).toBeGreaterThan(0);
      for (const s of p.seen) expect(['card', 'name']).toContain(s.shown);
    }
  });
});
