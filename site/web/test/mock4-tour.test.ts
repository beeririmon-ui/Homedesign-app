/**
 * MOCK4 (2026-11-18): the arithmetic of the arrival's labels (web/src/tour/arrival.ts) — the plan's projection through
 * the camera of a frame of the walk, the names on their doors at the rest on HC (ARR-M1), when each is on screen, and
 * the layout that keeps them apart. What the page does with them is held in the browser (e2e/mock4.spec.ts).
 */
import { beforeAll, describe, expect, it } from 'vitest';

type Mod = typeof import('../src/tour/arrival');
let m: Mod;
beforeAll(async () => {
  Object.assign(globalThis, { __ARTIFACT__: false, __MEDIA_BASE__: '/media/', __HD_PUBLIC__: false });
  m = await import('../src/tour/arrival');
});

describe('MOCK4: the names on the doors at the rest on HC', () => {
  it('the bath’s lintel at u 0.3944–0.4114, the bedroom’s centred at 0.496 (ARR-M1), the children’s from hc-lock', () => {
    const cam = m.camAt(m.arrival.hc_60)!;
    expect(cam).not.toBeNull();
    for (const l of m.arrival.labels) {
      const a = m.project(l.pts[0], cam)!;
      const b = m.project(l.pts[1], cam)!;
      const u = [a.u, b.u].sort((x, y) => x - y);
      if (l.u[0] !== l.u[1]) {
        expect(u[0]).toBeCloseTo(l.u[0], 3);
        expect(u[1]).toBeCloseTo(l.u[1], 3);
      } else expect((u[0]! + u[1]!) / 2).toBeCloseTo(l.u[0], 2);
      // the lintels are over the camera's height: in the upper part of the frame
      expect(Math.max(a.v, b.v)).toBeLessThan(0.5);
    }
    const bed = m.labelPose(m.arrival.labels.find((l) => l.id === 'O-corridor-master')!, cam)!;
    expect(bed.at.u).toBeCloseTo(0.496, 3);
    expect(m.arrival.labels.map((l) => l.name_he)).toEqual(['רחצה', 'חדר ילד', 'חדר ילדה', 'חדר שינה']);
  });

  it('a point behind the camera is not drawn', () => {
    expect(m.project([2.462, 7.0, 2.4], m.camAt(m.arrival.hc_60)!)).toBeNull();
  });

  it('they land one after another from 0.3 s before the rest, and are all on through it; they go 0.2 s into the turn', () => {
    const [r0, r1] = m.arrival.rest_60;
    for (let i = 0; i < m.arrival.labels.length; i++) {
      expect(m.labelOpacity(i, r0 - 19)).toBe(0);
      expect(m.labelOpacity(i, r0 + 30)).toBe(1);
      expect(m.labelOpacity(i, r1)).toBe(1);
      expect(m.labelOpacity(i, 424)).toBe(0);
    }
    // in the order of the route: each starts 0.12 s after the one before
    expect(m.labelOpacity(0, r0 - 10)).toBeGreaterThan(m.labelOpacity(3, r0 - 10));
  });

  it('the layout keeps every name clear of the others, inside the window, on a phone and a wide screen', () => {
    for (const [w, h, size] of [
      [1380, 776, { w: 92, h: 26 }],
      [390, 219, { w: 48, h: 17 }],
    ] as const) {
      const sizes = m.arrival.labels.map(() => size);
      const lift = m.layoutLabels(sizes, w, h);
      const cam = m.camAt(m.arrival.hc_60)!;
      const boxes = m.arrival.labels.map((l, i) => {
        const p = m.labelPose(l, cam)!;
        const x0 = p.at.u * w - size.w / 2;
        const y1 = p.at.v * h - 8 - lift[i]!;
        return [x0, y1 - size.h, x0 + size.w, y1] as const;
      });
      for (const b of boxes) expect(b[1]).toBeGreaterThanOrEqual(1.9);
      // on a wide screen no two names touch; on a phone at most a corner where the window's top edge stops a lift
      let overlaps = 0;
      for (let i = 0; i < boxes.length; i++)
        for (let j = i + 1; j < boxes.length; j++) {
          const a = boxes[i]!;
          const b = boxes[j]!;
          if (a[0] < b[2] && a[2] > b[0] && a[1] < b[3] && a[3] > b[1]) overlaps++;
        }
      expect(overlaps).toBe(0);
    }
  });

  it('a phone takes the 30 fps walk and the 1080 door; a wide screen the 60 fps walk and the 1920 door', () => {
    expect(m.walkFor(390).fps).toBe(30);
    expect(m.walkFor(1440).fps).toBe(60);
    expect(m.doorUrl(390)).toMatch(/d0\.1080\.webp$/);
    expect(m.doorUrl(1440)).toMatch(/d0\.1920\.webp$/);
    expect(m.frameAt(0)).toBe(1);
    expect(m.frameAt((702 - 1) / 60)).toBe(702);
  });
});
