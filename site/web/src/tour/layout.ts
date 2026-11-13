/**
 * MOCK3 (2026-11-13), the owner's feedback FB2 and FB3: the whole frame first, and the controls folded away
 * (docs/proposals/tour-whole-frame-phone-2026-11-13.md). The numbers of that spec that are arithmetic live here, as pure
 * functions the page and the tests share: which of the three layouts a screen gets, the window's size in each, the
 * door's portal inside the window, the tap rules on the window, the zoom's limits, and the wheel's arc.
 *
 * The page's stylesheet lays the window out by the same numbers (styles/tour.css); `windowBox` is what the tests hold
 * the rendered box to.
 */
import { MAX_ZOOM, clampCam, coverSize } from '../engine/camera';
import type { Box, Cam, Viewport } from '../engine/types';

export type Layout = 'portrait' | 'rails' | 'desk';
/** the same queries the stylesheet uses: a phone held upright (and a tablet upright), a phone turned on its side */
export const MQ = {
  portrait: '(max-aspect-ratio: 11/10)',
  rails: '(min-aspect-ratio: 11/10) and (max-height: 500px)',
} as const;
export const layoutOf = (vw: number, vh: number): Layout => (vw / vh <= 1.1 ? 'portrait' : vh <= 500 ? 'rails' : 'desk');

/** the bands around the window (CSS px): the top band's and the bottom band's minimum, the rails, the desktop's bar */
export const BAND = { top: 72, bottom: 220, rail: 88, bar: 64, gutter: 24 } as const;
export type Safe = { l: number; r: number; b: number };
/**
 * The 16:9 window in a stage of `sw` × `sh` CSS px (the stage is the screen under the site's header; turned on its
 * side there is no header). Upright: the full width, and what is left is shared 1 : 1.618 between the band above and
 * the band under it, over their minimums, so the window sits at the optical centre.
 */
export function windowBox(layout: Layout, sw: number, sh: number, safe: Safe = { l: 0, r: 0, b: 0 }): { w: number; h: number; top: number } {
  if (layout === 'portrait') {
    const h = (sw * 9) / 16;
    const rest = Math.max(0, sh - h - BAND.top - BAND.bottom - safe.b);
    return { w: sw, h, top: BAND.top + rest * 0.382 };
  }
  if (layout === 'rails') {
    const h = Math.min(sh, ((sw - 2 * BAND.rail - safe.l - safe.r) * 9) / 16);
    return { w: (h * 16) / 9, h, top: (sh - h) / 2 };
  }
  const h = Math.min(sh - BAND.bar, ((sw - 2 * BAND.gutter) * 9) / 16);
  return { w: (h * 16) / 9, h, top: (sh - BAND.bar - h) / 2 };
}

/**
 * The door's portal, in the window's CSS px (temporary, in code). `whole`: the portal inside the 16:9 window — 84% of
 * its height, 0.62 as wide as it is tall, its centre at a third of the width (the opening's third in H0). Otherwise the
 * window fills the screen ("מילוי וגרירה", the mock-up's earlier mode) and the portal is placed as it was there.
 */
export function doorRect(w: number, h: number, whole = true): { cx: number; cy: number; hw: number; hh: number; r: number } {
  if (whole) {
    const ph = h * 0.84;
    const pw = ph * 0.62;
    return { cx: w * 0.33, cy: h * 0.5, hw: pw / 2, hh: ph / 2, r: Math.min(pw * 0.14, 44) };
  }
  const portrait = w / h < 1.1;
  const ph = h * (portrait ? 0.54 : 0.74);
  const pw = Math.min(w * (portrait ? 0.66 : 0.36), ph * (portrait ? 0.62 : 0.7));
  return { cx: w * (portrait ? 0.5 : 0.31), cy: h * (portrait ? 0.42 : 0.47), hw: pw / 2, hh: ph / 2, r: Math.min(pw * 0.14, 44) };
}

// ---------- a tap on the window (a phone: the marks are decoration, the window is the touch target) ----------
export const TAP = { near: 28, apart: 10 } as const;
export type Mark = { id: string; x: number; y: number };
/**
 * A tap at (x, y) among the marks, all in the window's CSS px: the nearest mark opens when it is within 28 px and the
 * next one is 10 px further or out of reach (an effective target of 56 px for a mark on its own); two marks within
 * reach and that close to each other zoom ×2 to the point, where they stand apart; a tap away from every mark is nothing.
 */
export function tapRule(x: number, y: number, marks: readonly Mark[]): { open: string } | { zoom: true; nearest: string } | null {
  let nearest: Mark | null = null;
  let d1 = Infinity;
  let d2 = Infinity;
  for (const m of marks) {
    const d = Math.hypot(m.x - x, m.y - y);
    if (d < d1) {
      d2 = d1;
      d1 = d;
      nearest = m;
    } else if (d < d2) d2 = d;
  }
  if (!nearest || d1 > TAP.near) return null;
  return d2 - d1 >= TAP.apart || d2 > TAP.near ? { open: nearest.id } : { zoom: true, nearest: nearest.id };
}

// ---------- zoom ----------
/** ×1 to ×2.5 inside the window; a pinch stretches to ×2.75 like rubber; one that ends under ×1.15 goes back to ×1 */
export const ZOOM = { max: 2.5, rubber: 2.75, snap: 1.15, step: 2, over: 24, ms: 600 } as const;
/**
 * A pinch asking for `raw`: the zoom the camera takes, and what is left over as a stretch of the picture itself (the
 * rubber: the camera never leaves its limits, the canvas is scaled over it and springs back).
 */
export function pinchZoom(raw: number): { z: number; stretch: number } {
  if (raw > ZOOM.max) return { z: ZOOM.max, stretch: 1 + (ZOOM.rubber / ZOOM.max - 1) * (1 - Math.exp(-(raw - ZOOM.max) / 0.6)) };
  if (raw < 1) return { z: 1, stretch: 1 - 0.06 * (1 - Math.exp(-(1 - raw) / 0.4)) };
  return { z: raw, stretch: 1 };
}
/** a drag past the frame's edge by `over` px moves the picture at most 24 px, like rubber */
export const rubber = (over: number): number => Math.sign(over) * ZOOM.over * (1 - Math.exp(-Math.abs(over) / 60));

// ---------- the wheel ----------
export type Arc = { cw: number; step: number; radius: number; shrink: number };
const clamp = (lo: number, x: number, hi: number): number => Math.min(hi, Math.max(lo, x));
/**
 * The wheel's arc from the window's size, which the page already holds: nothing is measured when the wheel opens.
 *  - upright: under the window, in the strip's place — the centre card clamp(96px, 28vw, 128px), its neighbours at 0.72
 *    and two of them in view on each side;
 *  - on its side: on the window's bottom edge, a centre card of 88;
 *  - a wide screen (and "מילוי וגרירה"): over the bottom of the picture, as before.
 */
export function wheelArc(layout: Layout, win: { w: number; h: number }, vh: number, fill = false): Arc {
  if (layout === 'desk' || fill) {
    const cw = Math.max(104, Math.min(200, clamp(96, vh * 0.2, 148) * 0.78, win.w * 0.34));
    return { cw, step: 34, radius: cw * 1.9, shrink: 1 };
  }
  const cw = layout === 'rails' ? 88 : Math.round(clamp(96, win.w * 0.28, 128));
  return { cw, step: 30, radius: cw * 1.75, shrink: 0.72 };
}
/** how much of the window's height the close-up keeps free under the product: nothing upright (nothing is over the
 *  window), the arc on its side (the product in the upper 62%), the wheel on a wide screen */
export const closeReserve = (layout: Layout, winH: number, fill = false): number =>
  layout === 'desk' || fill ? (winH > 520 ? 0.52 : 0.46) : layout === 'rails' ? 0.38 : 0;

/** on its side the arc takes the bottom 128 px of the window (a card of 88, the name and the price under it), and a
 *  product's box ends 16 px over it at the least */
export const ARC = { h: 128, clear: 16 } as const;
/** a product's box with a third of its size round it, kept inside the frame: the close-up shows it at 60% of the view */
export const padded = (b: Box): Box => {
  const gu = (b[1] - b[0]) / 3;
  const gv = (b[3] - b[2]) / 3;
  return [Math.max(0, b[0] - gu), Math.min(1, b[1] + gu), Math.max(0, b[2] - gv), Math.min(1, b[3] + gv)];
};
/**
 * On its side: the close-up's camera, moved so the product's box `b` ends 16 px over the arc. `cam` is the camera that
 * frames the product in the upper 62% of the window. The view never goes under the frame, so a product low in the
 * frame is lifted by zooming in until the frame's own bottom is that far under it — as long as the product still fits
 * over the arc. A product that reaches the frame's bottom (the rug) cannot be lifted: `cam` comes back as it is, and
 * the arc is over the product's lower part.
 */
export function overArc(cam: Cam, b: Box, vp: Viewport, aspect: number): Cam {
  const { fw, fh } = coverSize(vp, aspect);
  const limit = vp.h - ARC.h - ARC.clear;
  if (vp.h / 2 + (b[3] - cam.cv) * fh * cam.z <= limit) return cam;
  const need = (vp.h - limit) / ((1 - b[3]) * fh);
  const fit = Math.min(MAX_ZOOM, limit / ((b[3] - b[2]) * fh), vp.w / ((b[1] - b[0]) * fw));
  if (!(need <= fit)) return cam;
  const z = Math.max(cam.z, need);
  return clampCam({ z, cu: cam.cu, cv: b[3] - (limit - vp.h / 2) / (fh * z) }, vp, aspect);
}
