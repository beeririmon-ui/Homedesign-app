/**
 * MOCK8 (2026-11-26, briefs/site-mock8-integrate-2026-11-26.md): the house grade (FB16) and the walk by scroll impulses
 * (FB19), the pure parts:
 *
 *  1. web/src/tour/grade.ts against the fb16 tool's own apply_grade (assets/renders/tools/fb16/fb16.py, W0's grade):
 *     50 colours, each channel within 1 value (OpenCV's float Lab and its gamma table against the exact formulas);
 *  2. the slopes of the L curve that tools/make-tour-room.ts writes (the tool's pchip) give the knots back;
 *  3. tools/tour/arrival.json: one line picks the walk; K-A2 ends on a still (the push walks on), the whole walk on
 *     the room;
 *  4. the walk (web/src/tour/walk.ts): a push plays a stretch and stops; it never goes back; two or three small pushes
 *     reach the end, where it keeps a walking pace; a gesture of many wheel events is one push.
 */
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { curve, gradeRgb, type TourGrade } from '../src/tour/grade';
import { GESTURE, Gesture, WALK, WalkPlay } from '../src/tour/walk';

const read = <T>(rel: string): T => JSON.parse(readFileSync(new URL(rel, import.meta.url), 'utf8')) as T;
/** W0's grade (manifest-fb16.json), its slopes as tools/make-tour-room.ts computes them */
const W0: TourGrade = { kin: [0.0, 10.968, 87.598, 97.0, 100.0], kout: [0.0, 8.931, 75.0, 96.0, 100.0], m: [], da: 1.135, db: 2.647 };
function slopes(x: number[], y: number[]): number[] {
  const h = x.slice(1).map((v, i) => v - x[i]!);
  const d = h.map((hi, i) => (y[i + 1]! - y[i]!) / hi);
  const m = y.map(() => 0);
  m[0] = d[0]!;
  m[m.length - 1] = d[d.length - 1]!;
  for (let i = 1; i < x.length - 1; i++)
    if (d[i - 1]! * d[i]! > 0) {
      const w1 = 2 * h[i]! + h[i - 1]!;
      const w2 = h[i]! + 2 * h[i - 1]!;
      m[i] = (w1 + w2) / (w1 / d[i - 1]! + w2 / d[i]!);
    }
  return m;
}
W0.m = slopes(W0.kin, W0.kout);
/** apply_grade's own output for these colours (python3.12, fb16.py, W0) */
const IN = [
  [241, 160, 175],
  [229, 148, 198],
  [213, 57, 14],
  [76, 72, 223],
  [233, 1, 127],
  [210, 33, 204],
  [30, 119, 209],
  [77, 87, 71],
  [184, 65, 253],
  [113, 122, 129],
  [149, 141, 130],
  [254, 206, 202],
  [179, 159, 87],
  [253, 119, 55],
  [216, 41, 219],
  [156, 29, 11],
  [113, 9, 36],
  [131, 248, 119],
  [206, 234, 210],
  [161, 112, 131],
  [68, 127, 97],
  [63, 254, 3],
  [24, 49, 248],
  [177, 225, 51],
  [184, 94, 125],
  [0, 158, 212],
  [169, 39, 136],
  [68, 247, 225],
  [47, 130, 240],
  [216, 181, 163],
  [10, 189, 121],
  [23, 62, 138],
  [186, 129, 156],
  [223, 175, 92],
  [164, 153, 27],
  [15, 169, 99],
  [153, 82, 57],
  [38, 97, 208],
  [102, 97, 147],
  [250, 100, 151],
  [0, 0, 0],
  [255, 255, 255],
  [12, 10, 9],
  [128, 128, 128],
  [230, 220, 200],
  [60, 40, 30],
  [200, 180, 160],
  [5, 5, 5],
  [250, 245, 235],
  [90, 120, 150],
];
const OUT = [
  [189, 122, 130],
  [178, 110, 146],
  [160, 38, 1],
  [66, 51, 166],
  [175, 0, 89],
  [159, 15, 147],
  [40, 86, 151],
  [61, 65, 50],
  [141, 43, 183],
  [86, 88, 90],
  [113, 103, 91],
  [216, 171, 163],
  [136, 117, 58],
  [191, 86, 33],
  [164, 22, 158],
  [123, 18, 0],
  [93, 6, 28],
  [116, 210, 94],
  [184, 203, 178],
  [122, 80, 92],
  [54, 93, 66],
  [61, 214, 0],
  [40, 33, 189],
  [147, 183, 30],
  [139, 66, 87],
  [33, 116, 153],
  [131, 24, 99],
  [72, 209, 186],
  [50, 94, 173],
  [172, 140, 122],
  [28, 141, 85],
  [24, 48, 110],
  [141, 93, 110],
  [174, 134, 64],
  [123, 112, 6],
  [26, 124, 67],
  [117, 59, 36],
  [43, 70, 153],
  [80, 70, 106],
  [189, 71, 107],
  [0, 0, 0],
  [255, 255, 255],
  [10, 8, 7],
  [97, 93, 89],
  [198, 184, 163],
  [50, 33, 24],
  [158, 138, 118],
  [4, 4, 4],
  [248, 240, 228],
  [71, 87, 107],
];

describe('MOCK8: the house grade (FB16)', () => {
  it('the L curve passes through its knots and is monotone', () => {
    W0.kin.forEach((x, i) => expect(curve(W0, x)).toBeCloseTo(W0.kout[i]!, 6));
    let last = -1;
    for (let L = 0; L <= 100; L += 0.25) {
      const v = curve(W0, L);
      expect(v).toBeGreaterThanOrEqual(last - 1e-9);
      last = v;
    }
  });
  it('gradeRgb is the fb16 tool’s apply_grade, within one value a channel', () => {
    let off = 0;
    IN.forEach((c, i) => {
      const g = gradeRgb(c, W0);
      for (let k = 0; k < 3; k++) {
        const d = Math.abs(g[k]! - OUT[i]![k]!);
        expect(d, `${c.join(',')} → ${g.join(',')} (fb16: ${OUT[i]!.join(',')})`).toBeLessThanOrEqual(1);
        off += d;
      }
    });
    expect(off / (IN.length * 3)).toBeLessThan(0.3);
  });
});

describe('MOCK8: the arrival’s walk (FB19)', () => {
  type Cfg = { walk: string; walks: Record<string, { end: { kind: string } }>; impulse: number; snap: number };
  const cfg = read<Cfg>('../../tools/tour/arrival.json');
  it('one line picks the walk: K-A2 ends on a still, the whole walk (and the final one) on the room', () => {
    expect(Object.keys(cfg.walks)).toEqual(expect.arrayContaining(['ka2', 'fb19', 'final']));
    expect(cfg.walks[cfg.walk]).toBeTruthy();
    expect(cfg.walks.ka2!.end.kind).toBe('still');
    expect(cfg.walks.fb19!.end.kind).toBe('room');
    // the coordinator's update: the final walk (D0 → K-A2 → the walking turn → T-E0-W into M0-W fix1) is the one shown
    expect(cfg.walk).toBe('final');
    expect(cfg.walks.final!.end.kind).toBe('room');
  });
  /** plays the walk at 60 Hz until it rests (or reaches its end); returns where it is and how long it took */
  function play(w: WalkPlay, t0: number): { t: number; s: number; back: boolean } {
    let t = t0;
    let s = 0;
    let back = false;
    for (let i = 0; i < 60 * 20; i++) {
      const r = w.step(t, 1 / 60);
      if (r < 0) back = true;
      t = Math.min(w.p.duration, t + r / 60);
      s += 1 / 60;
      if (r === 0 || t >= w.p.duration) break;
    }
    return { t, s, back };
  }
  for (const d of [5.4, 8.8]) {
    it(`a walk of ${d} s: a small push plays a stretch and stops; two or three reach the end`, () => {
      const w = new WalkPlay({ duration: d, impulse: cfg.impulse, snap: cfg.snap });
      w.push(0, GESTURE.first);
      const a = play(w, 0);
      expect(a.back).toBe(false);
      expect(a.t).toBeGreaterThan(0.2 * d);
      expect(a.t).toBeLessThan(0.5 * d);
      expect(w.resting).toBe(true);
      // a wheel notch a push: the third reaches the end, at a walking pace
      w.push(a.t, GESTURE.first);
      const b = play(w, a.t);
      expect(b.t).toBeGreaterThan(a.t);
      expect(b.t).toBeLessThan(d);
      w.push(b.t, GESTURE.first);
      expect(w.through).toBe(true);
      const c = play(w, b.t);
      expect(c.t).toBe(d);
      expect(w.rate).toBeGreaterThanOrEqual(WALK.end * 0.9);
      // two full flicks (1.3 impulses each) reach it too
      const f = new WalkPlay({ duration: d, impulse: cfg.impulse, snap: cfg.snap });
      f.push(0, GESTURE.cap);
      f.push(play(f, 0).t, GESTURE.cap);
      expect(f.through).toBe(true);
    });
  }
  it('the rate never jumps: it rises and falls a little a frame, and the walk never goes back', () => {
    const w = new WalkPlay({ duration: 5.4, impulse: cfg.impulse, snap: cfg.snap });
    w.push(0, 1);
    let t = 0;
    let r0 = 0;
    for (let i = 0; i < 400; i++) {
      const r = w.step(t, 1 / 60);
      expect(Math.abs(r - r0)).toBeLessThanOrEqual(Math.max(WALK.acc, WALK.dec * 2) / 60 + 1e-9 + (r === 0 ? WALK.rest : 0));
      expect(r).toBeGreaterThanOrEqual(0);
      t += r / 60;
      r0 = r;
    }
  });
  it('a gesture of many wheel events is one push, at most 1.3 impulses; a pause starts another', () => {
    const g = new Gesture();
    let k = 0;
    let fresh = 0;
    for (let i = 0; i < 30; i++) {
      const e = g.wheel(40, i * 16);
      k += e.k;
      fresh += e.fresh ? 1 : 0;
    }
    expect(fresh).toBe(1);
    expect(k).toBeCloseTo(GESTURE.cap, 6);
    expect(g.wheel(-50, 1000).k).toBe(0);
    expect(g.wheel(100, 2000).fresh).toBe(true);
  });
});
