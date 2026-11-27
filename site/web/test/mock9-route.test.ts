/**
 * MOCK9 (2026-11-27, briefs/site-mock9-route-ui-2026-11-27.md; FB21): the guided route, the pure parts.
 *
 *  1. the stations are the owner's order, the same as the rooms' order (data.ts GROUP_IDS) and tools/tour/route.json;
 *  2. one leg per step; leg 1 (living → kitchen) is real, its ease frames as its manifest marks them; the others walk
 *     in code until their clips exist, and a real leg drops in with one line (MOCK11: legs 2, 4 and 5 are real too,
 *     web/test/mock11-route.test.ts; which legs are real is the config's);
 *  3. a trip: one station ahead at ×1, two ×2, three ×2.5, four and more ×3; the ease frames between the legs skipped
 *     (the ease-in of every leg but the first, the ease-out of every leg but the last); back is the light, ~450 ms;
 *  4. the stretch a hop plays: the whole leg, or without the frames a chain skips, on the frames' own times;
 *  5. the wordmark is one constant ("הבית" until the brand has a name).
 */
import { readFileSync } from 'node:fs';
import { beforeAll, describe, expect, it } from 'vitest';
import { BACK_MS, LEGS, ROUTE, legFile, nextOf, rateFor, span, trip } from '../src/tour/route';
import { BRAND_HE } from '../src/design/Wordmark';

const read = <T>(rel: string): T => JSON.parse(readFileSync(new URL(rel, import.meta.url), 'utf8')) as T;
const cfg = read<{ order: string[]; legs: Record<string, string | null> }>('../../tools/tour/route.json');
type Manifest = {
  chain: { ease_in_frames: Record<string, [number, number]>; ease_out_frames: Record<string, [number, number]> };
  variants: Record<string, { frames: number; fps: number }>;
};
const leg1 = read<Manifest>('../../../assets/video/transitions/warm-modern/route-fb21/leg1/final/manifest.json');

describe('MOCK9: the guided route', () => {
  let GROUP_IDS: readonly string[] = [];
  beforeAll(async () => {
    // the tour's data reads the build's flags (as web/test/mock6-tour.test.ts sets them)
    Object.assign(globalThis, { __ARTIFACT__: false, __MEDIA_BASE__: '/media/', __HD_PUBLIC__: false });
    GROUP_IDS = (await import('../src/tour/data')).GROUP_IDS;
  });
  it('the stations: living → kitchen → bath → bedroom → boy → girl → work, the rooms’ order and the config’s', () => {
    expect(ROUTE).toEqual(['living-room', 'dining', 'bath', 'master', 'boy', 'girl', 'work']);
    expect([...GROUP_IDS]).toEqual([...ROUTE]);
    expect(cfg.order).toEqual([...ROUTE]);
    expect(nextOf('living-room')).toBe('dining');
    expect(nextOf('work')).toBeNull();
  });

  it('one leg per step; leg 1 is the clip, with its manifest’s ease frames; a leg without one has none, one line each', () => {
    expect(LEGS.map((l) => `${l.from}>${l.to}`)).toEqual(ROUTE.slice(1).map((to, i) => `${ROUTE[i]}>${to}`));
    expect(Object.keys(cfg.legs)).toEqual(LEGS.map((l) => `${l.from}>${l.to}`));
    const l1 = LEGS[0]!;
    expect(l1.real).not.toBeNull();
    expect(l1.real!.desktop).toMatchObject({
      w: 1920,
      h: 1080,
      fps: 60,
      frames: leg1.variants['1920']!.frames,
      ease_in: leg1.chain.ease_in_frames['1920'],
      ease_out: leg1.chain.ease_out_frames['1920'],
    });
    expect(l1.real!.phone).toMatchObject({
      w: 1080,
      h: 608,
      fps: 30,
      frames: leg1.variants['1080']!.frames,
      ease_in: leg1.chain.ease_in_frames['1080'],
      ease_out: leg1.chain.ease_out_frames['1080'],
    });
    // the files the page plays stay light: a wide screen's under 6 MB (MOCK11: 8 MB for a long leg), a phone's under 2.5 MB
    expect(l1.real!.desktop.bytes).toBeLessThan(6 * 1048576);
    expect(l1.real!.phone.bytes).toBeLessThan(2.5 * 1048576);
    // MOCK11: the legs that are real are the config's lines, one each
    expect(LEGS.map((l) => l.real !== null)).toEqual(Object.values(cfg.legs).map(Boolean));
    // a phone (≤ 900 CSS px) plays the 30 fps file, a wide screen the 60 fps one; a leg in code has none
    expect(legFile(l1, 400)?.fps).toBe(30);
    expect(legFile(l1, 1280)?.fps).toBe(60);
    expect(legFile(LEGS.find((l) => !l.real)!, 1280)).toBeNull();
  });

  it('a trip: one station at the leg’s own pace; a jump chained ×2–×3, the ease frames between legs skipped; back is the light', () => {
    expect([1, 2, 3, 4, 6].map(rateFor)).toEqual([1, 2, 2.5, 3, 3]);
    expect(trip('dining', 'dining')).toEqual({ kind: 'stay' });
    const one = trip('living-room', 'dining');
    expect(one).toMatchObject({ kind: 'ahead', to: 'dining', stations: 1, rate: 1 });
    if (one.kind !== 'ahead') throw new Error('ahead');
    expect(one.hops.map((h) => [h.leg.id, h.skipIn, h.skipOut])).toEqual([['leg1', false, false]]);
    const two = trip('living-room', 'bath');
    if (two.kind !== 'ahead') throw new Error('ahead');
    expect(two.rate).toBe(2);
    expect(two.hops.map((h) => [h.leg.id, h.skipIn, h.skipOut])).toEqual([
      ['leg1', false, true],
      ['leg2', true, false],
    ]);
    const all = trip('living-room', 'work');
    if (all.kind !== 'ahead') throw new Error('ahead');
    expect(all.rate).toBe(3);
    expect(all.hops).toHaveLength(6);
    expect(all.hops.map((h) => h.skipIn)).toEqual([false, true, true, true, true, true]);
    expect(all.hops.map((h) => h.skipOut)).toEqual([true, true, true, true, true, false]);
    expect(trip('master', 'dining')).toEqual({ kind: 'back', to: 'dining', ms: BACK_MS });
    expect(BACK_MS).toBeGreaterThanOrEqual(400);
    expect(BACK_MS).toBeLessThanOrEqual(500);
  });

  it('the stretch a hop plays: the whole leg (frame 1 to the last), or without the ease frames a chain skips', () => {
    const v = LEGS[0]!.real!.desktop;
    expect(span(v, { skipIn: false, skipOut: false })).toEqual({ start: 0, end: (v.frames - 1) / v.fps });
    // the first frame after the ease-in, the last before the ease-out (frame i is on screen from (i − 1) / fps)
    expect(span(v, { skipIn: true, skipOut: true })).toEqual({ start: v.ease_in[1] / v.fps, end: (v.ease_out[0] - 2) / v.fps });
    const p = LEGS[0]!.real!.phone;
    expect(span(p, { skipIn: false, skipOut: true }).end).toBeCloseTo((p.ease_out[0] - 2) / 30, 6);
    // a chained hop is shorter than the whole leg, and at ×2 it takes less than half of its time
    const s = span(v, { skipIn: false, skipOut: true });
    expect((s.end - s.start) / rateFor(2)).toBeLessThan((v.frames - 1) / v.fps / 2);
  });

  it('the wordmark is one constant, the placeholder until the brand is named', () => {
    expect(BRAND_HE).toBe('הבית');
  });
});
