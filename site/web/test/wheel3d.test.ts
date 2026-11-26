/**
 * FB20 (2026-11-26, briefs/site-wheel-3d-2026-11-26.md): the 3D product wheel's rules (web/src/components/ring-wheel.ts)
 * and the option's two pictures (web/src/tour/data.ts `pictures`).
 */
import { describe, expect, it } from 'vitest';
import { DIM, REVEAL_MS, RING, RingPhysics, cardPose, ringDelta, ringGeom, ringIndex } from '../src/components/ring-wheel';
import type { TourOption, TourSlot } from '../src/tour/data';
import { pictures, wheelCard } from '../src/tour/pictures';

describe('FB20: the ring', () => {
  it('is seen from above at 30–45°, and the selection’s reveal is 600–900 ms with the room dimmed under the wheel', () => {
    expect(RING.tilt).toBeGreaterThanOrEqual(30);
    expect(RING.tilt).toBeLessThanOrEqual(45);
    expect(RING.tiltShort).toBeGreaterThanOrEqual(30);
    expect(REVEAL_MS).toBeGreaterThanOrEqual(600);
    expect(REVEAL_MS).toBeLessThanOrEqual(900);
    expect(DIM.ev).toBeLessThan(0);
  });

  it('works for 3 to 12 options: the whole ring fits its cell’s height, and the front three fit across', () => {
    for (const [w, h] of [
      [309, 259],
      [400, 295],
      [640, 190],
    ] as const)
      for (let n = 3; n <= 12; n++) {
        const g = ringGeom(n, w, h);
        expect(g.step * n).toBeCloseTo(360);
        expect(g.cw).toBeGreaterThanOrEqual(40);
        // the front card at the bottom of the cell, the back of the ring under its top
        const p = g.p;
        const zf = g.r * Math.cos((g.tilt * Math.PI) / 180);
        const yf = g.r * Math.sin((g.tilt * Math.PI) / 180);
        const front = g.cy + (yf * p) / (p - zf) + ((g.cw / 2) * p) / (p - zf);
        const back = g.cy - (yf * p) / (p + zf) - ((g.cw / 2) * p) / (p + zf);
        expect(front).toBeLessThanOrEqual(h + 0.5);
        expect(back).toBeGreaterThanOrEqual(-0.5);
      }
  });

  it('places a card in front larger, sharper and brighter than one behind; only the front half takes a tap', () => {
    const g = ringGeom(8, 400, 300);
    const f = cardPose(0, 0, g);
    const b = cardPose(4, 0, g);
    expect(f.front).toBeCloseTo(1);
    expect(b.front).toBeCloseTo(0);
    expect(f.opacity).toBeGreaterThan(b.opacity);
    expect(f.veil).toBe(0);
    expect(b.veil).toBeGreaterThan(0);
    expect(f.soft).toBe(0);
    expect(b.soft).toBe(1);
    expect(f.live).toBe(true);
    expect(b.live).toBe(false);
    // RTL: the next option sits to the left (a negative turn), the previous to the right
    expect(cardPose(1, 0, g).transform).toMatch(/^rotateY\(-45\.000deg\)/);
    expect(cardPose(7, 0, g).transform).toMatch(/^rotateY\(45\.000deg\)/);
  });

  it('closes on itself: distances take the short way round, and positions wrap', () => {
    expect(ringDelta(11, 0, 12)).toBe(-1);
    expect(ringDelta(1, 11, 12)).toBe(2);
    expect(ringIndex(-1, 5)).toBe(4);
    expect(ringIndex(12, 5)).toBe(2);
  });

  it('drags, carries on with the velocity and snaps to a whole card; a move to a card takes the short way', () => {
    const r = new RingPhysics(10, 100);
    r.startDrag(0);
    for (let t = 16; t <= 160; t += 16) r.drag(25, t);
    const at = r.release();
    expect(Number.isInteger(r.target)).toBe(true);
    expect(r.target!).toBeGreaterThan(r.pos);
    for (let i = 0; i < 400 && r.step(1 / 60); i++);
    expect(r.target).toBeNull();
    expect(r.index).toBe(at);
    expect(r.pos).toBe(at);
    // from the first card to the last: one step back, not nine forward
    r.setIndex(0);
    r.goTo(9);
    expect(r.target).toBe(-1);
    for (let i = 0; i < 400 && r.step(1 / 60); i++);
    expect(r.index).toBe(9);
  });
});

describe('FB20: the option’s two pictures', () => {
  const card = { src: 'tour/x/cards.webp', w: 10, h: 10, source: 'layer' as const };
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
  const slot = (lazy: boolean) => ({ id: 'throw', lazy }) as unknown as TourSlot;

  it('the wheel shows the studio picture where there is one, else today’s thumbnail', () => {
    const studio = { src: 'tour/studio/throw-1.webp', w: 480, h: 480, source: 'studio' as const };
    expect(pictures(slot(false), opt({ studio })).studio).toEqual(studio);
    expect(wheelCard(slot(false), opt({ studio }))).toEqual(studio);
    expect(pictures(slot(false), opt({})).studio).toBeNull();
    expect(wheelCard(slot(false), opt({}))).toEqual(card);
    // a card that already is our own studio picture (MOCK2) counts as one
    const own = { ...card, source: 'studio' as const };
    expect(pictures(slot(false), opt({ card: own })).studio).toEqual(own);
  });

  it('in the room: the option’s own layer, or its patch in a wheel of many', () => {
    expect(pictures(slot(false), opt({ position: 2 })).in_room).toEqual({ kind: 'layer', slot: 'throw', position: 2 });
    expect(pictures(slot(true), opt({ position: 7 })).in_room).toEqual({ kind: 'patch', slot: 'throw', position: 7 });
  });
});
