/**
 * MOCK1: the tour's effects (docs/proposals/wow-tour-experience-2026-11-12.md), each one `run` of the engine: a function
 * of its own time that is the frame before it at 0 and the frame after it at 1. Durations and curves are the designer's
 * (section 7). With reduced motion every one of them is a short dissolve: no plane, no rings, nothing moves.
 *
 *  - the door: the portal grows until the wall is gone (a code stand-in for T-E0; temporary)
 *  - the reveal, "what is for sale here": A the burst, B the depth scan, C the dimmed room
 *  - the swap on the wheel: S1 the scan wipe, S2 from the outline, S3 lift and place
 *  - the style change: Y1 strip and dress, Y2 the material wave
 */
import { EASE, clamp01, type Pose, type TourEngine } from './engine';
import { FX, MASK_PER_M } from './gl';
import { NORDIC, WM, tour, type HouseId, type TourSlot } from './data';

export type Reveal = 'a' | 'b' | 'c';
export type Swap = 's1' | 's2' | 's3';
export type Style = 'y1' | 'y2';
/** what an effect asks of the page: the marks over the room are DOM, moved by CSS */
export type Ui = {
  ring(slot: TourSlot, kind: 'burst' | 'small' | 'touch'): void;
  /** a product's label (name · price) opens, or folds back to its dot; null: all of them */
  label(slot: TourSlot | null, on: boolean): void;
  /** the dots over the products */
  spots(on: boolean): void;
  /** the counter: n of 13 while the room fills, or the closing line ("13 פריטים · 26% מהחדר"); null: gone */
  count(n: number | null, final?: boolean): void;
  dims(on: boolean): void;
};

const FADE = 300;
const once = () => {
  const fired = new Set<string>();
  return (key: string, when: boolean, fn: () => void) => {
    if (!when || fired.has(key)) return;
    fired.add(key);
    fn();
  };
};
const bump = (x: number): number => (x <= 0 || x >= 1 ? 0 : Math.sin(Math.PI * x));
const everything = (e: TourEngine) => () => tour.slots.forEach((s) => e.settle(s.id, true));
const nothing = (e: TourEngine) => () => tour.slots.forEach((s) => e.settle(s.id, false));
/** the plane's travel: from in front of the nearest product to behind the room's far corner (m along the camera's axis) */
const NEAR = 2.0;
const FAR = 5.9;

// ---------- the door ----------
/** The portal grows from its place on the wall until the wall is off the screen; the camera ends on the room's rest. */
export function enter(e: TourEngine): Promise<void> {
  const [cx, cy, hw, hh] = e.d.door;
  const m = e.d.doorR + 48;
  const HW = Math.max(cx, e.vp.w - cx) + m;
  const HH = Math.max(cy, e.vp.h - cy) + m;
  e.stop('door-push');
  const from = { ...e.cam };
  return e.run(
    'enter',
    e.reduce ? FADE : 1200,
    (t) => {
      if (e.reduce) {
        e.d.doorAmt = 1 - t;
        return;
      }
      const k = EASE.camera(t);
      e.d.door = [cx, cy, hw + (HW - hw) * k, hh + (HH - hh) * k];
      // a narrow screen: the camera turns from the window to the room's rest as the wall opens (T-E0's pan, in code)
      e.cam = { cu: from.cu + (e.rest.cu - from.cu) * k, cv: e.rest.cv, z: from.z + (e.rest.z - from.z) * k };
    },
    () => {
      e.d.doorAmt = 0;
      e.cam = { ...e.rest };
    },
  );
}
/** Back to the door: the wall closes round the portal again (the way in, reversed) */
export function leave(e: TourEngine, d: { cx: number; cy: number; hw: number; hh: number; r: number }): Promise<void> {
  const m = d.r + 48;
  const HW = Math.max(d.cx, e.vp.w - d.cx) + m;
  const HH = Math.max(d.cy, e.vp.h - d.cy) + m;
  const to = e.atDoor();
  e.d.doorR = d.r;
  return e.run('leave', e.reduce ? FADE : 1000, (t) => {
    if (e.reduce) {
      e.d.door = [d.cx, d.cy, d.hw, d.hh];
      e.d.doorAmt = t;
      return;
    }
    const k = EASE.camera(t);
    e.d.doorAmt = 1;
    e.d.door = [d.cx, d.cy, HW + (d.hw - HW) * k, HH + (d.hh - HH) * k];
    e.cam = { ...e.rest, cu: e.rest.cu + (to.cu - e.rest.cu) * k };
  });
}
/** the designer's beat 1: a slow push of 2% in 10 s while the visitor stands at the door */
export function doorPush(e: TourEngine): void {
  if (e.reduce || e.sync) return;
  const at = e.atDoor();
  void e.run('door-push', 10_000, (t) => (e.cam = { ...at, z: at.z * (1 + 0.02 * EASE.out(t)) }));
}

// ---------- the reveal ----------
export async function reveal(e: TourEngine, ui: Ui, kind: Reveal, short = false): Promise<void> {
  await e.products();
  if (e.reduce) {
    await e.between('reveal-fade', FADE, everything(e));
    e.mask();
    ui.count(tour.slots.length, true);
    return;
  }
  if (kind === 'c') return revealDim(e, ui);
  e.mask(true);
  await (kind === 'a' ? revealBurst(e, ui) : revealScan(e, ui, short ? 1000 : 1600, short ? 400 : 600));
  e.mask();
}

/** A, the owner's idea: every product bursts in from its own point, the heaviest first, and the light comes up with them */
function revealBurst(e: TourEngine, ui: Ui): Promise<void> {
  const order = [...tour.slots].sort((a, b) => a.order_a - b.order_a);
  const n = order.length;
  const STAG = 120;
  const IN = 350;
  const end = (n - 1) * STAG + IN;
  const FLASH = 220;
  const total = end + 80 + FLASH + 60;
  const fire = once();
  const was = new Map<string, number>();
  return e.run('reveal-a', total, (t) => {
    const ms = t * total;
    let sum = 0;
    order.forEach((s, i) => {
      const p = EASE.out(clamp01((ms - i * STAG) / IN));
      // the shadow lands 80 ms after its product
      const q = clamp01((ms - i * STAG - 80) / 250);
      sum += p;
      fire(`ring ${s.id}`, ms >= i * STAG && t > 0, () => {
        ui.ring(s, 'burst');
        ui.label(s, true);
      });
      if (was.get(s.id) === p + 2 * q) return;
      was.set(s.id, p + 2 * q);
      if (p >= 1 && q >= 1) e.settle(s.id, true);
      else if (p > 0) e.pose(s.id, [{ a: p, s: q, lod: 2.6 * (1 - p) }]);
    });
    // the room a little dim (-0.5 EV) while it is empty; the exact grade is back when the last product is in
    e.d.ev = -0.5 * Math.min(1, ms / 160) * (1 - sum / n);
    // "how much they fill": every product's silhouette as one tint, for a moment
    e.d.tint = 0.24 * bump((ms - end - 80) / FLASH);
    fire('count', ms >= end + 80, () => ui.count(n, true));
  });
}

/** B, the recommended one: a plane of light goes into the room's depth, and each product takes form as it passes */
function revealScan(e: TourEngine, ui: Ui, scan: number, settle: number): Promise<void> {
  const total = scan + settle;
  const IN = 320;
  const at = (s: TourSlot) => ((s.depth_m - NEAR) / (FAR - NEAR)) * scan;
  const fire = once();
  const was = new Map<string, number>();
  let seen = 0;
  return e.run(
    'reveal-b',
    total,
    (t) => {
      const ms = t * total;
      e.d.fx = FX.scan;
      e.d.t = NEAR + (FAR - NEAR) * Math.min(1, ms / scan);
      e.d.amt = Math.min(1, ms / 160) * (1 - clamp01((ms - scan) / 260));
      for (const s of tour.slots) {
        const p = EASE.out(clamp01((ms - at(s)) / IN));
        const q = clamp01((ms - at(s) - 60) / 220);
        fire(`ring ${s.id}`, ms >= at(s) && t > 0, () => {
          ui.ring(s, 'small');
          ui.label(s, true);
          ui.count(++seen);
        });
        if (was.get(s.id) === p + 2 * q) continue;
        was.set(s.id, p + 2 * q);
        if (p >= 1 && q >= 1) e.settle(s.id, true);
        else if (p > 0) e.pose(s.id, [{ a: p, s: q }]);
      }
      fire('dims', ms >= scan * 0.55, () => ui.dims(true));
      fire('count', ms >= scan + 200, () => ui.count(tour.slots.length, true));
    },
    () => {
      e.d.fx = FX.none;
      e.d.amt = 0;
    },
  );
}

/** C: the room is whole from the first frame; everything that is not a product dims for a moment */
async function revealDim(e: TourEngine, ui: Ui): Promise<void> {
  if (e.visible.size < tour.slots.length) await e.between('reveal-c-in', FADE, everything(e));
  e.mask();
  const IN = 500;
  const HOLD = 1200;
  const t1 = 400 + IN;
  const t2 = t1 + HOLD;
  const total = t2 + IN;
  const fire = once();
  await e.run(
    'reveal-c',
    total,
    (t) => {
      const ms = t * total;
      e.d.fx = FX.dim;
      e.d.amt = ms < t2 ? EASE.out(clamp01((ms - 400) / IN)) : 1 - EASE.camera(clamp01((ms - t2) / IN));
      e.d.outline = 0.9 * e.d.amt;
      tour.slots.forEach((s, i) => fire(`label ${s.id}`, ms >= t1 - 200 + i * 70 && t > 0, () => ui.label(s, true)));
      fire('count', ms >= t1 && t > 0, () => ui.count(tour.slots.length, true));
    },
    () => {
      e.d.fx = FX.none;
      e.d.amt = 0;
      e.d.outline = 0;
    },
  );
}

/** The products are gathered: the plane comes back from the wall, and each one goes as it passes (0.6 s) */
export async function collect(e: TourEngine, ui: Ui): Promise<void> {
  ui.spots(false);
  ui.label(null, false);
  ui.count(null);
  ui.dims(false);
  if (e.reduce) return e.house === WM ? e.between('collect-fade', FADE, nothing(e)) : undefined;
  const total = 600;
  const OUT = 150;
  const at = (s: TourSlot) => ((FAR - s.depth_m) / (FAR - NEAR)) * (total - OUT);
  const was = new Map<string, number>();
  const wm = e.house === WM;
  if (wm) e.mask();
  await e.run(
    'collect',
    total,
    (t) => {
      const ms = t * total;
      e.d.fx = FX.scan;
      e.d.t = FAR - (FAR - NEAR) * t;
      e.d.amt = 0.7 * bump(t);
      if (!wm) return;
      for (const s of tour.slots) {
        if (!e.visible.has(s.id) && !was.has(s.id)) continue;
        const p = 1 - clamp01((ms - at(s)) / OUT);
        if (was.get(s.id) === p) continue;
        was.set(s.id, p);
        if (p <= 0) e.settle(s.id, false);
        else if (p < 1) e.pose(s.id, [{ a: p }]);
      }
    },
    () => {
      e.d.fx = FX.none;
      e.d.amt = 0;
    },
  );
  if (wm) e.mask();
}

// ---------- the swap on the wheel ----------
/** the slots S3 fits: an object standing on a surface (the designer: not the art, the curtains or the pendant) */
export const LIFTS = new Set(['vase', 'bowl', 'candle-holders', 'planter', 'basket']);

export async function swap(e: TourEngine, ui: Ui, s: TourSlot, to: number, dir: 1 | -1, kind: Swap): Promise<void> {
  const from = e.selection[s.id]!;
  if (from === to) return;
  await e.option(s.id, to);
  const choose = () => {
    e.selection = { ...e.selection, [s.id]: to };
    e.settle(s.id, true);
  };
  if (e.reduce) {
    await e.between('swap-fade', 150, choose);
    return e.mask();
  }
  const a = s.options[from - 1]!.box;
  const b = s.options[to - 1]!.box;
  const DUR = 450;
  const done = () => {
    choose();
    e.d.line = [0, 0, 0, 0];
    e.d.pulse = [0, 0];
  };
  if (kind === 's3' && LIFTS.has(s.id)) {
    // lift and place: the old one rises and goes, the new one comes down to its exact place, its shadow sharpens
    const up = -5 / e.gl.height;
    const fire = once();
    await e.run(
      'swap-s3',
      DUR,
      (t) => {
        const o = EASE.in(clamp01(t / 0.45));
        const k = clamp01((t - 0.4) / 0.6);
        const n = EASE.out(k);
        const poses: Pose[] = [];
        if (o < 1) poses.push({ pos: from, a: 1 - o, dy: up * o, slod: 1.5 * o });
        if (k > 0) poses.push({ pos: to, a: clamp01(n * 1.3), dy: up * (1 - n), s: n, slod: 2 * (1 - n) });
        e.pose(s.id, poses);
        fire('touch', t >= 0.94, () => ui.ring(s, 'touch'));
      },
      done,
    );
  } else if (kind === 's2') {
    // from the outline: the old one melts, its outline runs, the new one comes from a blur with a moment of light
    const fire = once();
    e.mask();
    await e.run(
      'swap-s2',
      DUR,
      (t) => {
        const o = EASE.in(clamp01(t / 0.45));
        const k = clamp01((t - 0.35) / 0.65);
        const n = EASE.out(k);
        const poses: Pose[] = [];
        if (o < 1) poses.push({ pos: from, a: 1 - o });
        if (k > 0) poses.push({ pos: to, a: n, lod: 3 * (1 - n), gain: 2 ** (0.3 * (1 - n)), s: clamp01((t - 0.65) / 0.35) });
        e.pose(s.id, poses);
        e.d.pulse = [Math.round(s.depth_m * MASK_PER_M) / MASK_PER_M, 0.95 * bump(t)];
        fire('mask', t >= 0.4, () => {
          e.selection = { ...e.selection, [s.id]: to };
          e.mask(false, false);
        });
      },
      done,
    );
  } else {
    // S1, the scan wipe: a thin line of light crosses the product in the drag's direction; behind it the new one
    const u0 = Math.min(a[0], b[0]) - 0.004;
    const u1 = Math.max(a[1], b[1]) + 0.004;
    const LAG = 40;
    const cut = (lo: number, hi: number, k: number): [[number, number], [number, number]] => {
      const x = dir > 0 ? lo + (hi - lo) * k : hi - (hi - lo) * k;
      return dir > 0
        ? [
            [x, 2],
            [-1, x],
          ]
        : [
            [-1, x],
            [x, 2],
          ];
    };
    await e.run(
      'swap-s1',
      DUR,
      (t) => {
        const ms = t * DUR;
        const k = EASE.camera(clamp01(ms / (DUR - LAG)));
        // the shadow changes with the line, 40 ms behind it, across the slot's whole rectangle
        const [oldP, newP] = cut(u0, u1, k);
        const [oldS, newS] = cut(s.rect[0], s.rect[1], EASE.camera(clamp01((ms - LAG) / (DUR - LAG))));
        e.pose(s.id, [
          { pos: from, clip: oldP, sclip: oldS },
          { pos: to, clip: newP, sclip: newS },
        ]);
        e.d.line = [dir > 0 ? u0 + (u1 - u0) * k : u1 - (u1 - u0) * k, Math.min(a[2], b[2]), Math.max(a[3], b[3]), bump(ms / (DUR - LAG))];
      },
      done,
    );
  }
  e.mask();
}

// ---------- the style change ----------
export async function style(e: TourEngine, ui: Ui, to: HouseId, kind: Style, how: Reveal): Promise<void> {
  if (to === e.house) return;
  await Promise.all([e.otherHouse(), e.products()]);
  const dress = () => {
    e.setHouse(to);
    if (to === WM) everything(e)();
  };
  if (e.reduce) {
    ui.spots(false);
    ui.label(null, false);
    ui.count(null);
    await e.between('style-fade', FADE, dress);
    return e.mask();
  }
  if (kind === 'y2') {
    // the material wave: one directed pass from the window across the floor, the next house whole behind it (1.2 s)
    ui.spots(false);
    ui.label(null, false);
    ui.count(null);
    const { x } = tour.camera.room;
    await e.between('style-y2', 1200, dress, (t) => {
      e.d.fx = FX.wave;
      e.d.t = x[0] - 0.3 + (x[1] - x[0] + 0.6) * EASE.camera(t);
      e.d.amt = bump(t);
    });
    return e.mask();
  }
  // Y1, strip and dress: the products go (0.6 s), the house changes from the back wall to the front (1.0 s), the next
  // house's products come in (1.4 s)
  await collect(e, ui);
  await e.between(
    'style-y1',
    1000,
    () => {
      e.setHouse(to);
      nothing(e)();
    },
    (t) => {
      e.d.fx = FX.depth;
      e.d.t = 6.3 - 4.8 * EASE.camera(t);
      e.d.amt = bump(t);
    },
  );
  if (to === WM) return reveal(e, ui, how === 'c' ? 'b' : how, true);
  // the Nordic house's products are part of its temporary picture: the plane passes over them, nothing to bring in
  e.mask();
  await e.run(
    'style-y1-nordic',
    1400,
    (t) => {
      e.d.fx = FX.scan;
      e.d.t = NEAR + (FAR - NEAR) * Math.min(1, t / 0.7);
      e.d.amt = 0.8 * bump(Math.min(1, t / 0.86));
    },
    () => {
      e.d.fx = FX.none;
      e.d.amt = 0;
    },
  );
}

export { NORDIC, WM };
