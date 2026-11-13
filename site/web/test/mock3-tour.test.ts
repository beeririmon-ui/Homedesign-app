/**
 * MOCK3 (2026-11-13), FB2 and FB3: the arithmetic of "the whole frame first" (web/src/tour/layout.ts) — which layout a
 * screen gets, the window's size in each (the designer's own examples), the door's portal inside the window, the tap
 * rules on the window, the zoom's limits and the wheel's arc — and the counters when two effects overlap. What the page
 * does with them is held in the browser (e2e/mock3.spec.ts).
 */
import { describe, expect, it } from 'vitest';
import { camForBox } from '../src/engine/camera';
import { ARC, BAND, TAP, ZOOM, closeReserve, doorRect, layoutOf, overArc, padded, pinchZoom, rubber, tapRule, wheelArc, windowBox } from '../src/tour/layout';
import { Metrics, sum } from '../src/tour/metrics';

describe('MOCK3: three layouts, by the screen', () => {
  it('a phone upright, a phone on its side, a wide screen, a tablet either way', () => {
    expect(layoutOf(390, 844)).toBe('portrait');
    expect(layoutOf(360, 640)).toBe('portrait');
    expect(layoutOf(844, 390)).toBe('rails');
    expect(layoutOf(932, 430)).toBe('rails');
    expect(layoutOf(1440, 900)).toBe('desk');
    expect(layoutOf(768, 1024)).toBe('portrait');
    expect(layoutOf(1024, 768)).toBe('desk');
  });
});

describe('MOCK3: the 16:9 window', () => {
  const ratio = (b: { w: number; h: number }) => b.w / b.h;
  it('upright: the full width, and the rest shared 1 : 1.618 over the bands’ minimums (the designer’s two examples)', () => {
    // a stage of 390 × 690: the band over the window 140, the band under it 330
    const a = windowBox('portrait', 390, 690);
    expect(a.w).toBe(390);
    expect(Math.round(a.h)).toBe(219);
    expect(Math.round(a.top)).toBe(140);
    expect(Math.round(690 - a.top - a.h)).toBe(330);
    // 360 × 580: 104 and 273 (the designer rounds down; a pixel either way)
    const b = windowBox('portrait', 360, 580);
    expect(Math.round(b.h)).toBe(203);
    expect(Math.abs(b.top - 104)).toBeLessThan(1.5);
    expect(Math.abs(580 - b.top - b.h - 273)).toBeLessThan(1.5);
    for (const w of [360, 390, 412, 430]) expect(ratio(windowBox('portrait', w, 700))).toBeCloseTo(16 / 9, 6);
  });
  it('a short screen keeps the bands’ minimums: the window is never squeezed', () => {
    const b = windowBox('portrait', 360, 480);
    expect(b.top).toBe(BAND.top);
    expect(ratio(b)).toBeCloseTo(16 / 9, 6);
  });
  it('on its side: the full height between two rails of 88 (668 × 376 at 844 × 390, 756 × 425 at 932 × 430)', () => {
    const a = windowBox('rails', 844, 390);
    expect([Math.round(a.w), Math.round(a.h)]).toEqual([668, 376]);
    const b = windowBox('rails', 932, 430);
    expect([Math.round(b.w), Math.round(b.h)]).toEqual([756, 425]);
    // a notch on one side narrows the window, and it is still 16:9
    expect(ratio(windowBox('rails', 844, 390, { l: 47, r: 0, b: 21 }))).toBeCloseTo(16 / 9, 6);
    expect(windowBox('rails', 844, 390, { l: 47, r: 0, b: 21 }).w).toBeLessThan(a.w);
  });
  it('a wide screen: contain inside (width − 48) × (height − 64): 1380 × 776 at 1440 × 900 under a header of 60', () => {
    const a = windowBox('desk', 1440, 840);
    expect([Math.round(a.w), Math.round(a.h)]).toEqual([1380, 776]);
    expect(ratio(a)).toBeCloseTo(16 / 9, 6);
    // a narrow, tall window is limited by its width
    expect(Math.round(windowBox('desk', 1000, 900).w)).toBe(952);
  });
});

describe('MOCK3: the door inside the window', () => {
  it('84% of the window’s height, 0.62 as wide as it is tall, centred at a third of the width', () => {
    for (const [w, h] of [
      [390, 219],
      [668, 376],
      [1380, 776],
    ] as const) {
      const d = doorRect(w, h);
      expect(d.hh * 2).toBeCloseTo(h * 0.84, 6);
      expect(d.hw / d.hh).toBeCloseTo(0.62, 6);
      expect(d.cx).toBeCloseTo(w * 0.33, 6);
      // the whole portal is inside the window, with wall round it
      expect(d.cx - d.hw).toBeGreaterThan(0);
      expect(d.cy - d.hh).toBeGreaterThan(0);
      expect(d.cy + d.hh).toBeLessThan(h);
      expect(d.r).toBeLessThanOrEqual(44);
    }
  });
  it('"מילוי וגרירה" keeps the earlier portal', () => {
    const d = doorRect(390, 784, false);
    expect(d.cx).toBe(195);
    expect(d.hh * 2).toBeCloseTo(784 * 0.54, 6);
  });
});

describe('MOCK3: a tap on the window', () => {
  const lone = [{ id: 'rug', x: 100, y: 100 }];
  it('a mark on its own has a target of 56: within 28 it opens, further it is nothing', () => {
    expect(tapRule(100, 100, lone)).toEqual({ open: 'rug' });
    expect(tapRule(100 + TAP.near, 100, lone)).toEqual({ open: 'rug' });
    expect(tapRule(100 + TAP.near + 1, 100, lone)).toBeNull();
    expect(tapRule(10, 10, [])).toBeNull();
  });
  it('two marks: the nearer one opens when the other is 10 further or out of reach', () => {
    const two = [
      { id: 'vase', x: 100, y: 100 },
      { id: 'bowl', x: 130, y: 100 },
    ];
    // 4 from the vase, 26 from the bowl
    expect(tapRule(104, 100, two)).toEqual({ open: 'vase' });
    // 10 from the vase, 20 from the bowl: exactly 10 apart is enough
    expect(tapRule(110, 100, two)).toEqual({ open: 'vase' });
    // the bowl out of reach: the vase opens however close the two distances are
    expect(
      tapRule(90, 100, [
        { id: 'vase', x: 100, y: 100 },
        { id: 'bowl', x: 60, y: 100 },
      ]),
    ).toEqual({ open: 'vase' });
  });
  it('two marks within reach and too close to tell apart: zoom to the point', () => {
    const two = [
      { id: 'vase', x: 100, y: 100 },
      { id: 'bowl', x: 126, y: 100 },
    ];
    expect(tapRule(113, 100, two)).toEqual({ zoom: true, nearest: 'vase' });
    expect(tapRule(116, 100, two)).toEqual({ zoom: true, nearest: 'bowl' });
  });
});

describe('MOCK3: zoom', () => {
  it('×1 to ×2.5; a pinch stretches the picture up to ×2.75 in all and no further', () => {
    expect(pinchZoom(1)).toEqual({ z: 1, stretch: 1 });
    expect(pinchZoom(2.2)).toEqual({ z: 2.2, stretch: 1 });
    expect(pinchZoom(ZOOM.max)).toEqual({ z: ZOOM.max, stretch: 1 });
    for (const raw of [2.6, 3, 5, 50]) {
      const p = pinchZoom(raw);
      expect(p.z).toBe(ZOOM.max);
      expect(p.stretch).toBeGreaterThan(1);
      expect(p.z * p.stretch).toBeLessThanOrEqual(ZOOM.rubber + 1e-9);
    }
    // more pinch, more stretch (it is a spring, not a wall)
    expect(pinchZoom(3).stretch).toBeGreaterThan(pinchZoom(2.6).stretch);
    // under ×1 the camera stays on the whole frame; the picture gives a little
    const u = pinchZoom(0.5);
    expect(u.z).toBe(1);
    expect(u.stretch).toBeLessThan(1);
    expect(u.stretch).toBeGreaterThan(0.93);
  });
  it('a drag past the edge moves the picture 24 px at the most', () => {
    expect(rubber(0)).toBe(0);
    expect(rubber(30)).toBeGreaterThan(0);
    expect(rubber(-30)).toBe(-rubber(30));
    expect(rubber(30)).toBeLessThan(30);
    expect(Math.abs(rubber(5000))).toBeLessThanOrEqual(ZOOM.over);
  });
});

describe('MOCK3: the wheel’s arc', () => {
  it('upright: a centre card of clamp(96, 28vw, 128): 101 at 360, 109 at 390, 120 at 430', () => {
    expect(wheelArc('portrait', { w: 360, h: 202 }, 640).cw).toBe(101);
    expect(wheelArc('portrait', { w: 390, h: 219 }, 844).cw).toBe(109);
    expect(wheelArc('portrait', { w: 430, h: 242 }, 932).cw).toBe(120);
    expect(wheelArc('portrait', { w: 320, h: 180 }, 568).cw).toBe(96);
    expect(wheelArc('portrait', { w: 768, h: 432 }, 1024).cw).toBe(128);
  });
  it('the neighbours at 0.72, and two of them fit on each side of the centre card', () => {
    for (const w of [360, 390, 412, 430]) {
      const a = wheelArc('portrait', { w, h: (w * 9) / 16 }, 800);
      expect(a.shrink).toBe(0.72);
      const rad = (a.step * Math.PI) / 180;
      // the first neighbour clears the centre card, and the second ends inside the screen
      const first = a.radius * Math.sin(rad) - (a.cw * a.shrink * Math.cos(rad)) / 2;
      expect(first).toBeGreaterThanOrEqual(a.cw / 2);
      const second = a.radius * Math.sin(2 * rad) + (a.cw * a.shrink ** 2 * Math.cos(2 * rad)) / 2;
      expect(second).toBeLessThanOrEqual(w / 2);
    }
  });
  it('on its side a card of 88; a wide screen as before (measured from the same numbers)', () => {
    expect(wheelArc('rails', { w: 668, h: 376 }, 390).cw).toBe(88);
    const d = wheelArc('desk', { w: 1380, h: 776 }, 900);
    expect(d).toEqual({ cw: 148 * 0.78, step: 34, radius: 148 * 0.78 * 1.9, shrink: 1 });
    // "מילוי וגרירה" on a phone is the earlier wheel
    expect(wheelArc('portrait', { w: 390, h: 784 }, 844, true).shrink).toBe(1);
  });
  it('the close-up keeps nothing free upright, the arc on its side, the wheel on a wide screen', () => {
    expect(closeReserve('portrait', 219)).toBe(0);
    expect(closeReserve('rails', 376)).toBe(0.38);
    expect(closeReserve('desk', 776)).toBe(0.52);
    expect(closeReserve('portrait', 784, true)).toBe(0.52);
  });
});

describe('MOCK3: on its side the product ends 16 px over the arc, wherever the frame allows', () => {
  const vp = { w: 668, h: 376 };
  const A = 16 / 9;
  const limit = vp.h - ARC.h - ARC.clear;
  const bottom = (cam: { cv: number; z: number }, v: number) => vp.h / 2 + (v - cam.cv) * vp.h * cam.z;
  const framed = (b: [number, number, number, number]) => camForBox(padded(b), vp, A, closeReserve('rails', vp.h));
  it('a product in the middle of the frame is already clear: the camera is left as it is', () => {
    const b: [number, number, number, number] = [0.45, 0.55, 0.3, 0.45];
    const cam = framed(b);
    expect(bottom(cam, b[3])).toBeLessThanOrEqual(limit);
    expect(overArc(cam, b, vp, A)).toBe(cam);
  });
  it('a tall product low in the frame is lifted by zooming in, and still fits over the arc', () => {
    const b: [number, number, number, number] = [0.34, 0.43, 0.48, 0.78];
    const cam = framed(b);
    expect(bottom(cam, b[3])).toBeGreaterThan(limit);
    const up = overArc(cam, b, vp, A);
    expect(up.z).toBeGreaterThan(cam.z);
    expect(bottom(up, b[3])).toBeCloseTo(limit, 3);
    expect(bottom(up, b[2])).toBeGreaterThanOrEqual(0);
  });
  it('a product that reaches the frame’s bottom cannot be lifted: the camera never shows what is under the frame', () => {
    const rug: [number, number, number, number] = [0.2, 1, 0.74, 1];
    const cam = framed(rug);
    expect(overArc(cam, rug, vp, A)).toBe(cam);
  });
});

describe('MOCK3: two effects that overlap are each held to their own counters', () => {
  it('the wheel rises while the camera lands: a decode after the camera landed is the wheel’s alone', () => {
    const m = new Metrics();
    m.begin('zoom-in');
    m.begin('wheel-in');
    const cam = m.end('zoom-in', [16, 16], [1, 1], [0, 0], 1);
    m.count('decode');
    const wheel = m.end('wheel-in', [16, 16], [0, 0], [0, 0], 1);
    expect(sum(cam.counts)).toBe(0);
    expect(wheel.counts.decode).toBe(1);
    expect(m.order).toEqual(['zoom-in', 'wheel-in']);
  });
});
