/**
 * MOCK6 (2026-11-25, briefs/site-mock6-kids-rooms-2026-11-25.md):
 *  - the wheel of many options with a fixture of ten (web/src/components/scroll-wheel.ts): the counter, the keys, the
 *    card it rests on, the cards it draws, and the loader that asks for the option it rests on only;
 *  - the engine's background load never takes a many-option slot ahead (data.ts `behind`);
 *  - the kids' rooms as generated: the owner's counts (boy 13, girl 12; the bath 19 with B1's planter), the safety rule
 *    (the Roman blind and the pendant shown and not sold, the toys waiting for EN 71), no mark for the plan-B furniture,
 *    the kids shell's cameras (the girl's the boy's plus girl_offset_y), and the prints at ×1 only.
 * What the page does with them is held in the browser (e2e/mock6.spec.ts).
 */
import { beforeAll, describe, expect, it } from 'vitest';
import { MANY_FROM, RestLoader, cardLabelHe, counterHe, inReach, keyStep, nearest } from '../src/components/scroll-wheel';

const N = 10;

describe('MOCK6: the wheel of many options, a fixture of ten', () => {
  it('a slot of four or more options takes it; two or three keep the arc', () => {
    expect(MANY_FROM).toBe(4);
    expect(3 < MANY_FROM && N >= MANY_FROM).toBe(true);
  });

  it('the counter reads "3 / 10", and each card its place for a screen reader', () => {
    expect(counterHe(0, N)).toBe('1 / 10');
    expect(counterHe(2, N)).toBe('3 / 10');
    expect(counterHe(9, N)).toBe('10 / 10');
    expect(cardLabelHe(2, N, 'דוגמה 3')).toBe('3 מתוך 10: דוגמה 3');
  });

  it('the keys, right to left: ← and ↓ the next, → and ↑ the previous, Home, End, Page Down / Up by three; held at the ends', () => {
    expect(keyStep('ArrowLeft', 0, N)).toBe(1);
    expect(keyStep('ArrowDown', 4, N)).toBe(5);
    expect(keyStep('ArrowRight', 4, N)).toBe(3);
    expect(keyStep('ArrowUp', 0, N)).toBe(0);
    expect(keyStep('ArrowLeft', 9, N)).toBe(9);
    expect(keyStep('Home', 6, N)).toBe(0);
    expect(keyStep('End', 2, N)).toBe(9);
    expect(keyStep('PageDown', 8, N)).toBe(9);
    expect(keyStep('PageUp', 2, N)).toBe(0);
    expect(keyStep('Enter', 2, N)).toBeNull();
    expect(keyStep('a', 2, N)).toBeNull();
  });

  it('it rests on the card nearest the middle, whatever the direction of the page', () => {
    // ten cards of 100 px, 14 apart, laid right to left (the first on the right), the scroller's middle at 500
    const rtl = Array.from({ length: N }, (_, i) => 900 - i * 114);
    expect(nearest(rtl, 500)).toBe(4); // 444 is 56 away; 558 is 58
    expect(nearest(rtl, 900)).toBe(0);
    expect(nearest(rtl, -200)).toBe(9);
    const ltr = Array.from({ length: N }, (_, i) => 100 + i * 114);
    expect(nearest(ltr, 328)).toBe(2);
    // a tie goes to the lower index
    expect(nearest([0, 10], 5)).toBe(0);
  });

  it('it draws the cards near the one it rests on: five of ten, not ten', () => {
    expect([...inReach(0, N)].sort((a, b) => a - b)).toEqual([0, 1, 2]);
    expect([...inReach(5, N)].sort((a, b) => a - b)).toEqual([3, 4, 5, 6, 7]);
    expect([...inReach(9, N)].sort((a, b) => a - b)).toEqual([7, 8, 9]);
    for (let i = 0; i < N; i++) expect(inReach(i, N).size).toBeLessThanOrEqual(5);
  });

  it('the loader asks for the option it rests on only: the ones passed on the way are never asked for', async () => {
    const asked: number[] = [];
    const gates: (() => void)[] = [];
    const loader = new RestLoader(
      (pos) =>
        new Promise<void>((r) => {
          asked.push(pos);
          gates.push(r);
        }),
      1,
    );
    // resting where it is asks for nothing
    await loader.rest(1);
    expect(asked).toEqual([]);
    // a rest on 3; while its patch loads, the wheel passes 4, 5, 6 and rests on 7
    void loader.rest(3);
    expect(asked).toEqual([3]);
    for (const p of [4, 5, 6, 7]) void loader.rest(p);
    expect(asked).toEqual([3]);
    gates.shift()!();
    await new Promise((r) => setTimeout(r, 0));
    expect(asked).toEqual([3, 7]);
    gates.shift()!();
    await new Promise((r) => setTimeout(r, 0));
    expect(loader.shown).toBe(7);
    // back to 7 again: nothing; a swipe across the rest of the ten to 10: one patch
    await loader.rest(7);
    const done = loader.rest(10);
    gates.shift()!();
    await done;
    expect(asked).toEqual([3, 7, 10]);
    expect(asked.length).toBeLessThan(N);
  });
});

type Data = typeof import('../src/tour/data');
let d: Data;
beforeAll(async () => {
  Object.assign(globalThis, { __ARTIFACT__: false, __MEDIA_BASE__: '/media/', __HD_PUBLIC__: false });
  d = await import('../src/tour/data');
});

describe('MOCK6: the background load', () => {
  it('a many-option slot (a fixture of ten) is never loaded ahead; a wheel of three is, but the option shown', () => {
    const opt = (position: number) => ({ position }) as unknown as import('../src/tour/data').TourOption;
    const slots = [
      { id: 'art', lazy: true, options: Array.from({ length: N }, (_, i) => opt(i + 1)) },
      { id: 'throw', options: [opt(1), opt(2), opt(3)] },
      { id: 'lamp', options: [opt(1)] },
    ] as unknown as import('../src/tour/data').TourSlot[];
    expect(d.behind(slots, { art: 4, throw: 2, lamp: 1 })).toEqual([
      ['throw', 1],
      ['throw', 3],
    ]);
  });
});

describe('MOCK6: the kids’ rooms as built (tools/make-tour-room.ts)', () => {
  it('the rooms and their buttons: חדר הילד and חדר הילדה, a frame each', () => {
    expect(d.GROUP_IDS).toEqual(['living-room', 'master', 'bath', 'dining', 'work', 'boy', 'girl']);
    expect(d.GROUP_HE.boy).toBe('חדר הילד');
    expect(d.GROUP_HE.girl).toBe('חדר הילדה');
    expect(d.FRAMES.boy).toEqual(['boy']);
    expect(d.FRAMES.girl).toEqual(['girl']);
  });

  it('the owner’s counts: boy 13, girl 12, the bath 19 (B1’s planter); the other rooms as MOCK5', () => {
    expect(d.roomCount('boy').total).toBe(13);
    expect(d.roomCount('girl').total).toBe(12);
    expect(d.roomCount('bath').total).toBe(19);
    expect(d.roomCount('master').total).toBe(22);
    expect(d.roomCount('dining').total).toBe(23);
    expect(d.roomCount('work').total).toBe(18);
    expect(d.ROOMS['bath-b1'].slots.some((s) => s.id === 'ledge-planter')).toBe(true);
  });

  it('the safety rule: the blind and the pendant shown and not sold, the toys waiting for EN 71; never a price', () => {
    const want: Record<string, Record<string, ['blocked' | 'notify', string]>> = {
      boy: {
        'roman-blind': ['blocked', 'לא במכירה'],
        pendant: ['blocked', 'לא במכירה לחדר ילדים'],
        'toy-cars': ['notify', 'ממתין לתקן EN 71'],
        'soft-toy': ['notify', 'ממתין לתקן EN 71'],
      },
      girl: {
        'roman-blind': ['blocked', 'לא במכירה'],
        pendant: ['blocked', 'לא במכירה לחדר ילדים'],
        'soft-toy': ['notify', 'ממתין לתקן EN 71'],
      },
    };
    for (const room of ['boy', 'girl'] as const) {
      const r = d.ROOMS[room];
      const held = Object.fromEntries(r.slots.filter((s) => s.sale).map((s) => [s.id, [s.sale!.state, s.sale!.label_he]]));
      expect(held).toEqual(want[room]);
      expect(d.roomHeld(room)).toBe(Object.keys(want[room]!).length);
      for (const s of r.slots.filter((x) => x.sale)) {
        expect(s.sale!.why_he.length).toBeGreaterThan(10);
        for (const o of s.options) {
          expect(o.price_agorot).toBeNull();
          expect(o.available).toBe(false);
        }
        // the pendant keeps its mark (MOCK6's choice): the room's marks and its count agree
        expect(s.fixed).toBe(false);
      }
      // textiles are sold as usual: no hold on the bedding, the pillowcases, the throw or the cushions
      for (const id of ['bedding', 'pillowcase', 'bedspread', 'cushions']) expect(r.slots.find((s) => s.id === id)!.sale).toBeUndefined();
      // every other room has no hold
    }
    for (const id of d.ROOM_IDS.filter((x) => x !== 'boy' && x !== 'girl')) expect(d.ROOMS[id].slots.some((s) => s.sale)).toBe(false);
  });

  it('the walnut bed, desk and chair are the plate’s (plan B): no layer, no mark, not counted', () => {
    for (const room of ['boy', 'girl'] as const) {
      const ids = d.ROOMS[room].slots.map((s) => s.id);
      for (const id of ['bed', 'desk', 'desk-chair']) expect(ids).not.toContain(id);
      expect(d.ROOMS[room].slots.filter((s) => s.fixed)).toEqual([]);
      expect(d.ROOMS[room].for_sale).toBe(room === 'boy' ? 13 : 12);
    }
  });

  it('the kids shell’s cameras: K-boy, and K-girl the boy’s shifted by girl_offset_y (3.63); the slots’ depths shift with it', () => {
    type Cam = { loc: [number, number, number]; yaw_deg_left: number };
    const boy = d.ROOMS.boy as unknown as { camera: Cam; camera_from: string; slots: { id: string; depth_m: number }[] };
    const girl = d.ROOMS.girl as unknown as typeof boy;
    expect(boy.camera_from).toBe('style_shells_1_3_1.warm-modern.kids.cameras.K-boy');
    expect(girl.camera_from).toBe('style_shells_1_3_1.warm-modern.kids.cameras.K-girl');
    expect(boy.camera.loc).toEqual([1.1, 13, 1]);
    expect(girl.camera.loc[1] - boy.camera.loc[1]).toBeCloseTo(3.63, 9);
    expect(girl.camera.yaw_deg_left).toBe(boy.camera.yaw_deg_left);
    const bd = Object.fromEntries(boy.slots.map((s) => [s.id, s.depth_m]));
    for (const s of girl.slots) expect(s.depth_m).toBeCloseTo(bd[s.id]!, 3);
  });

  it('the throw is the wheel in each, V1–V3 on the frame’s own atlas pages; the prints are ×1 only, so no zoom', () => {
    for (const room of ['boy', 'girl'] as const) {
      const r = d.ROOMS[room];
      expect(r.sample).toBe('bedspread');
      const t = r.slots.find((s) => s.id === 'bedspread')!;
      expect(t.options).toHaveLength(3);
      expect(t.lazy).toBeUndefined();
      expect(t.atlas_opts?.['1920']).toHaveLength(3);
      // the three share the default's shadow
      expect(new Set(t.shadows)).toEqual(new Set([1]));
      expect(r.zoom).toBe(false);
      expect(r.avoid).toHaveLength(1);
      expect(r.slots.find((s) => s.id === 'framed-prints')!.closeup).toBe(false);
      // a frame's pages: one for the products, one for the shadows (the sample's own pages are gone)
      expect(r.atlas!['1920']!.product.map((p) => p.src)).toEqual([`tour/${room}/warm-modern/atlas.product.1`]);
    }
  });
});
