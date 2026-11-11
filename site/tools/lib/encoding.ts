/**
 * S12, QA S8–S10 §4 (S10 question 4): the encoding threshold of a tool layer on the public site, measured on what the
 * browser draws against what it draws from the approved pixels (the same resize, lossless):
 *   - the worst channel per pixel, in 8-bit levels: p99 ≤ 6 and p99.9 ≤ 10;
 *   - at most 0.2% of the pixels above 8 levels;
 *   - CIEDE2000 p99 ≤ 3.5.
 * "No defect visible at ×1" stays an eye check (QA). The check itself is e2e/encoding.spec.ts: QA's method, the real
 * engine in the browser, at QA's five views. (Measured on the file alone, at 1:1, no lossy setting near these sizes
 * meets it: the engine's own resampling is part of what the threshold was set on.)
 */

export const THRESHOLD = { p99: 6, p999: 10, over8: 0.002, de00_p99: 3.5 } as const;

export type Measure = { pixels: number; p99: number; p999: number; max: number; over8: number; de00_p99: number; de00_mean: number };

const LIN = new Float64Array(256).map((_, i) => {
  const c = i / 255;
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
});
const f = (t: number) => (t > 216 / 24389 ? Math.cbrt(t) : (24389 / 27 / 116) * t + 16 / 116);
function lab(r: number, g: number, b: number, out: Float64Array, o: number): void {
  const R = LIN[r]!;
  const G = LIN[g]!;
  const B = LIN[b]!;
  const x = f((0.4124564 * R + 0.3575761 * G + 0.1804375 * B) / 0.95047);
  const y = f(0.2126729 * R + 0.7151522 * G + 0.072175 * B);
  const z = f((0.0193339 * R + 0.119192 * G + 0.9503041 * B) / 1.08883);
  out[o] = 116 * y - 16;
  out[o + 1] = 500 * (x - y);
  out[o + 2] = 200 * (y - z);
}

const RAD = Math.PI / 180;
/** CIEDE2000 (Sharma, Wu and Dalal 2005), kL = kC = kH = 1 */
export function de2000(L1: number, a1: number, b1: number, L2: number, a2: number, b2: number): number {
  const C1 = Math.hypot(a1, b1);
  const C2 = Math.hypot(a2, b2);
  const Cb = (C1 + C2) / 2;
  const G = 0.5 * (1 - Math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)));
  const a1p = (1 + G) * a1;
  const a2p = (1 + G) * a2;
  const C1p = Math.hypot(a1p, b1);
  const C2p = Math.hypot(a2p, b2);
  const h = (b: number, a: number) => {
    if (b === 0 && a === 0) return 0;
    const v = Math.atan2(b, a) / RAD;
    return v < 0 ? v + 360 : v;
  };
  const h1p = h(b1, a1p);
  const h2p = h(b2, a2p);
  const dLp = L2 - L1;
  const dCp = C2p - C1p;
  let dhp = 0;
  if (C1p * C2p !== 0) {
    dhp = h2p - h1p;
    if (dhp > 180) dhp -= 360;
    else if (dhp < -180) dhp += 360;
  }
  const dHp = 2 * Math.sqrt(C1p * C2p) * Math.sin((dhp / 2) * RAD);
  const Lbp = (L1 + L2) / 2;
  const Cbp = (C1p + C2p) / 2;
  let hbp = h1p + h2p;
  if (C1p * C2p !== 0) {
    if (Math.abs(h1p - h2p) > 180) hbp += h1p + h2p < 360 ? 360 : -360;
    hbp /= 2;
  }
  const T =
    1 - 0.17 * Math.cos((hbp - 30) * RAD) + 0.24 * Math.cos(2 * hbp * RAD) + 0.32 * Math.cos((3 * hbp + 6) * RAD) - 0.2 * Math.cos((4 * hbp - 63) * RAD);
  const dTheta = 30 * Math.exp(-(((hbp - 275) / 25) ** 2));
  const Rc = 2 * Math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7));
  const Sl = 1 + (0.015 * (Lbp - 50) ** 2) / Math.sqrt(20 + (Lbp - 50) ** 2);
  const Sc = 1 + 0.045 * Cbp;
  const Sh = 1 + 0.015 * Cbp * T;
  const Rt = -Math.sin(2 * dTheta * RAD) * Rc;
  return Math.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh));
}

/** The residual of `enc` against `ref` (both RGBA, same size). With `alpha`, only covered pixels, over mid grey. */
export function measure(ref: Uint8Array, enc: Uint8Array, alpha: boolean): Measure {
  const n = ref.length / 4;
  const hist = new Float64Array(256);
  const deBins = 4000; // 0.01 per bin, to 40
  const deHist = new Float64Array(deBins + 1);
  const lab1 = new Float64Array(3);
  const lab2 = new Float64Array(3);
  let pixels = 0;
  let deSum = 0;
  const over = (c: number, a: number) => Math.round((c * a + 128 * (255 - a)) / 255);
  for (let i = 0; i < n; i++) {
    const k = i * 4;
    let r1 = ref[k]!;
    let g1 = ref[k + 1]!;
    let b1 = ref[k + 2]!;
    let r2 = enc[k]!;
    let g2 = enc[k + 1]!;
    let b2 = enc[k + 2]!;
    if (alpha) {
      const a1 = ref[k + 3]!;
      const a2 = enc[k + 3]!;
      if (!a1 && !a2) continue;
      r1 = over(r1, a1);
      g1 = over(g1, a1);
      b1 = over(b1, a1);
      r2 = over(r2, a2);
      g2 = over(g2, a2);
      b2 = over(b2, a2);
    }
    pixels++;
    const d = Math.max(Math.abs(r1 - r2), Math.abs(g1 - g2), Math.abs(b1 - b2));
    hist[d]!++;
    if (!d) {
      deHist[0]!++;
      continue;
    }
    lab(r1, g1, b1, lab1, 0);
    lab(r2, g2, b2, lab2, 0);
    const de = de2000(lab1[0]!, lab1[1]!, lab1[2]!, lab2[0]!, lab2[1]!, lab2[2]!);
    deSum += de;
    deHist[Math.min(deBins, Math.round(de * 100))]!++;
  }
  const pct = (h: Float64Array, q: number, scale: number) => {
    const target = q * pixels;
    let acc = 0;
    for (let i = 0; i < h.length; i++) {
      acc += h[i]!;
      if (acc >= target) return i * scale;
    }
    return (h.length - 1) * scale;
  };
  let max = 0;
  for (let i = 255; i >= 0; i--)
    if (hist[i]) {
      max = i;
      break;
    }
  let above = 0;
  for (let i = 9; i < 256; i++) above += hist[i]!;
  return {
    pixels,
    p99: pct(hist, 0.99, 1),
    p999: pct(hist, 0.999, 1),
    max,
    over8: pixels ? above / pixels : 0,
    de00_p99: +pct(deHist, 0.99, 0.01).toFixed(2),
    de00_mean: pixels ? +(deSum / pixels).toFixed(3) : 0,
  };
}

/** What fails the threshold, in words; empty when the entry passes. */
export function failures(m: Measure): string[] {
  const out: string[] = [];
  if (m.p99 > THRESHOLD.p99) out.push(`p99 ${m.p99} > ${THRESHOLD.p99}`);
  if (m.p999 > THRESHOLD.p999) out.push(`p99.9 ${m.p999} > ${THRESHOLD.p999}`);
  if (m.over8 > THRESHOLD.over8) out.push(`${(m.over8 * 100).toFixed(2)}% above 8 levels > ${THRESHOLD.over8 * 100}%`);
  if (m.de00_p99 > THRESHOLD.de00_p99) out.push(`ΔE00 p99 ${m.de00_p99} > ${THRESHOLD.de00_p99}`);
  return out;
}

/**
 * S16, QA ת43 (QA's ruling on the poster's WebP fallback, S13–S14 §ת30): the fallback serves only browsers without AVIF,
 * which the site does not support, so it is exempt from THRESHOLD; it is still held to "no defect visible at ×1" (QA's
 * eye: lossy q95 shows none at 1:1, at p99 7–9 · ΔE 4.1–4.5). This bound is the regression guard around that: a setting
 * clearly worse than q95 (q90 measured p99 8–10 · 0.9–2.4% · ΔE 4.7–5.0) fails it.
 */
export const FALLBACK_BOUND = { p99: 10, p999: 16, over8: 0.02, de00_p99: 4.6 } as const;
export function fallbackFailures(m: Measure): string[] {
  const out: string[] = [];
  if (m.p99 > FALLBACK_BOUND.p99) out.push(`p99 ${m.p99} > ${FALLBACK_BOUND.p99}`);
  if (m.p999 > FALLBACK_BOUND.p999) out.push(`p99.9 ${m.p999} > ${FALLBACK_BOUND.p999}`);
  if (m.over8 > FALLBACK_BOUND.over8) out.push(`${(m.over8 * 100).toFixed(2)}% above 8 levels > ${FALLBACK_BOUND.over8 * 100}%`);
  if (m.de00_p99 > FALLBACK_BOUND.de00_p99) out.push(`ΔE00 p99 ${m.de00_p99} > ${FALLBACK_BOUND.de00_p99}`);
  return out;
}

/** The views QA measured (qa/reports/2026-11-10-site-track-qa-s8-s10/tools/base-quality.mjs): the page, its dpr, and the
 * wheel's camera on the set ("zoom"). */
export type View = { id: string; w: number; h: number; dpr: number; zoom?: boolean };
export const VIEWS: View[] = [
  { id: '1920@1', w: 1920, h: 1080, dpr: 1 },
  { id: '1280@1', w: 1280, h: 720, dpr: 1 },
  { id: '400@1', w: 400, h: 800, dpr: 1 },
  { id: '400@3', w: 400, h: 800, dpr: 3 },
  { id: '1280-zoom', w: 1280, h: 720, dpr: 1, zoom: true },
];
