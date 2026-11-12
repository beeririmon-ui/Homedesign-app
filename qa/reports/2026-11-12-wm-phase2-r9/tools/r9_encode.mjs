/**
 * qa-agent 2026-11-12 (R9; copied from ../../2026-11-12-wm-phase2-r8/tools/r8_encode.mjs, inputs changed): the encoding gate, as a
 * FILE-LEVEL PROXY, on the two layers R9 changed (pendant 2, curtain 3) and, for comparison, their R8 files. The phase-2 layers have no site encodes yet (site/tools/make-house.ts
 * builds only the phase-1 cushion slot of this house), so the binding in-browser gate (site e2e/encoding.spec.ts, QA's five views) cannot
 * run on them. Here every file R8 changed is encoded the way make-house encodes a tool slot today (product: WebP near-lossless q60
 * effort 5; shadow: WebP lossless effort 5), cut to the slot's rect (the region's bbox + 8 px), at the site widths 1920 and 2720, and
 * measured with the gate's own formula (site/tools/lib/encoding.ts measure(), re-written here): worst channel per pixel in 8-bit levels,
 * p99 <= 6, p99.9 <= 10, <= 0.2 % above 8, CIEDE2000 p99 <= 3.5; the product over mid grey (alpha), and the scene as drawn: base (lossless)
 * x the encoded shadow, then the encoded product, against the same with the lossless files, on the slot's rect.
 * The base: the site's shell.<w>.avif (AVIF q70) decoded vs base.png resized losslessly, at 1280 / 1920 / 2720 (file-level, information;
 * S12's in-browser gate passed on these bytes, and base.png is unchanged byte for byte).
 *   node r9_encode.mjs     (sharp from site/node_modules; writes ../data/encode.json)
 */
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const REPO = '/home/user/homedesign-app';
const require = createRequire(join(REPO, 'site/package.json'));
const sharp = require('sharp');
const P2 = join(REPO, 'assets/renders/living-room/warm-modern/phase2-2026-11-10');
const LD = join(P2, 'layers');
const OUT = join(REPO, 'qa/reports/2026-11-12-wm-phase2-r9');
const man = JSON.parse(readFileSync(join(LD, 'manifest-r9.json'), 'utf8'));
const man8 = JSON.parse(readFileSync(join(LD, 'manifest-r8.json'), 'utf8'));
const V8 = Object.fromEntries(Object.values(man8.variants).flat().map((v) => [v.id, v]));
const byId = Object.fromEntries(man.layers.map((l) => [l.id, l]));
const V = Object.fromEntries(Object.values(man.variants).flat().map((v) => [v.id, v]));
const W = 2720;
const H = 1530;

const TH = { p99: 6, p999: 10, over8: 0.002, de00_p99: 3.5 };
const LIN = Float64Array.from({ length: 256 }, (_, i) => {
  const c = i / 255;
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
});
const f = (t) => (t > 216 / 24389 ? Math.cbrt(t) : (24389 / 27 / 116) * t + 16 / 116);
function lab(r, g, b) {
  const R = LIN[r], G = LIN[g], B = LIN[b];
  const x = f((0.4124564 * R + 0.3575761 * G + 0.1804375 * B) / 0.95047);
  const y = f(0.2126729 * R + 0.7151522 * G + 0.072175 * B);
  const z = f((0.0193339 * R + 0.119192 * G + 0.9503041 * B) / 1.08883);
  return [116 * y - 16, 500 * (x - y), 200 * (y - z)];
}
const RAD = Math.PI / 180;
function de2000(L1, a1, b1, L2, a2, b2) {
  const C1 = Math.hypot(a1, b1), C2 = Math.hypot(a2, b2), Cb = (C1 + C2) / 2;
  const G = 0.5 * (1 - Math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)));
  const a1p = (1 + G) * a1, a2p = (1 + G) * a2;
  const C1p = Math.hypot(a1p, b1), C2p = Math.hypot(a2p, b2);
  const hh = (b, a) => (b === 0 && a === 0 ? 0 : ((Math.atan2(b, a) / RAD) + 360) % 360);
  const h1p = hh(b1, a1p), h2p = hh(b2, a2p);
  const dLp = L2 - L1, dCp = C2p - C1p;
  let dhp = 0;
  if (C1p * C2p !== 0) { dhp = h2p - h1p; if (dhp > 180) dhp -= 360; else if (dhp < -180) dhp += 360; }
  const dHp = 2 * Math.sqrt(C1p * C2p) * Math.sin((dhp / 2) * RAD);
  const Lbp = (L1 + L2) / 2, Cbp = (C1p + C2p) / 2;
  let hbp = h1p + h2p;
  if (C1p * C2p !== 0) { if (Math.abs(h1p - h2p) > 180) hbp += h1p + h2p < 360 ? 360 : -360; hbp /= 2; }
  const T = 1 - 0.17 * Math.cos((hbp - 30) * RAD) + 0.24 * Math.cos(2 * hbp * RAD) + 0.32 * Math.cos((3 * hbp + 6) * RAD) - 0.2 * Math.cos((4 * hbp - 63) * RAD);
  const dTh = 30 * Math.exp(-(((hbp - 275) / 25) ** 2));
  const Rc = 2 * Math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7));
  const Sl = 1 + (0.015 * (Lbp - 50) ** 2) / Math.sqrt(20 + (Lbp - 50) ** 2), Sc = 1 + 0.045 * Cbp, Sh = 1 + 0.015 * Cbp * T;
  const Rt = -Math.sin(2 * dTh * RAD) * Rc;
  return Math.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh));
}
/** ref / enc: RGBA (4 ch) buffers of the same size; alpha: only covered pixels, over mid grey */
function measure(ref, enc, alpha, mask = null) {
  const n = ref.length / 4;
  const hist = new Float64Array(256);
  const de = [];
  let px = 0;
  const over = (c, a) => Math.round((c * a + 128 * (255 - a)) / 255);
  for (let i = 0; i < n; i++) {
    if (mask && !mask[i]) continue;
    const k = i * 4;
    let r1 = ref[k], g1 = ref[k + 1], b1 = ref[k + 2], r2 = enc[k], g2 = enc[k + 1], b2 = enc[k + 2];
    if (alpha) {
      const a1 = ref[k + 3], a2 = enc[k + 3];
      if (!a1 && !a2) continue;
      r1 = over(r1, a1); g1 = over(g1, a1); b1 = over(b1, a1); r2 = over(r2, a2); g2 = over(g2, a2); b2 = over(b2, a2);
    }
    px++;
    const d = Math.max(Math.abs(r1 - r2), Math.abs(g1 - g2), Math.abs(b1 - b2));
    hist[d]++;
    if (!d) { de.push(0); continue; }
    const l1 = lab(r1, g1, b1), l2 = lab(r2, g2, b2);
    de.push(de2000(...l1, ...l2));
  }
  const pct = (q) => { const t = q * px; let acc = 0; for (let i = 0; i < 256; i++) { acc += hist[i]; if (acc >= t) return i; } return 255; };
  let max = 0;
  for (let i = 255; i >= 0; i--) if (hist[i]) { max = i; break; }
  let above = 0;
  for (let i = 9; i < 256; i++) above += hist[i];
  de.sort((a, b) => a - b);
  const m = { pixels: px, p99: pct(0.99), p999: pct(0.999), max, over8: px ? above / px : 0, de00_p99: +(de[Math.min(de.length - 1, Math.floor(0.99 * de.length))] ?? 0).toFixed(2) };
  m.pass = m.p99 <= TH.p99 && m.p999 <= TH.p999 && m.over8 <= TH.over8 && m.de00_p99 <= TH.de00_p99;
  return m;
}

async function raw(img, w) {
  const { data, info } = await img.clone().ensureAlpha().resize({ width: w }).raw().toBuffer({ resolveWithObject: true });
  return { data, info };
}
async function decode(buf) {
  const { data, info } = await sharp(buf).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  return { data, info };
}
async function regionRect(lf, sf) {
  const L = await sharp(join(LD, lf)).ensureAlpha().raw().toBuffer();
  const S = await sharp(join(LD, sf)).removeAlpha().raw().toBuffer();
  let x0 = W, y0 = H, x1 = -1, y1 = -1;
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const i = y * W + x;
    if (L[i * 4 + 3] > 0 || Math.min(S[i * 3], S[i * 3 + 1], S[i * 3 + 2]) < 255) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
  }
  const p = 8;
  x0 = Math.max(0, x0 - p); y0 = Math.max(0, y0 - p); x1 = Math.min(W - 1, x1 + p); y1 = Math.min(H - 1, y1 + p);
  return { left: x0, top: y0, width: x1 - x0 + 1, height: y1 - y0 + 1 };
}

const res = { method: 'file-level proxy of the site gate (see the header)', thresholds: TH, layers: {}, base: {} };
const JOBS = [
  ['pendant-v2 R9 (P2-1)', V['pendant-v2'].file, V['pendant-v2'].shadow],
  ['pendant-v2 R8 (for comparison)', V8['pendant-v2'].file, V8['pendant-v2'].shadow],
  ['curtains-v3 R9 (Linen, F1)', V['curtains-v3'].file, V['curtains-v3'].shadow],
];
const baseImg = sharp(join(LD, 'base.png')).ensureAlpha();
for (const [name, lf, sf] of JOBS) {
  const rect = await regionRect(lf, sf);
  res.layers[name] = { rect, widths: {} };
  for (const w of [1920, 2720]) {
    const cw = Math.round((rect.width * w) / W);
    const prod = sharp(join(LD, lf)).ensureAlpha().extract(rect);
    const shad = sharp(join(LD, sf)).ensureAlpha().extract(rect);
    const pRef = await raw(prod, cw);
    const sRef = await raw(shad, cw);
    const pEncBuf = await prod.clone().resize({ width: cw }).webp({ nearLossless: true, quality: 60, effort: 5 }).toBuffer();
    const sEncBuf = await shad.clone().resize({ width: cw }).webp({ lossless: true, effort: 5 }).toBuffer();
    const pEnc = await decode(pEncBuf);
    const sEnc = await decode(sEncBuf);
    // the scene as drawn on the rect: base (lossless, same resize) x shadow, then the product
    const bRef = await raw(baseImg.clone().extract(rect), cw);
    const n = pRef.data.length / 4;
    const comp = (P, S) => {
      const o = Buffer.alloc(n * 4);
      for (let i = 0; i < n; i++) {
        const a = P[i * 4 + 3] / 255;
        for (let c = 0; c < 3; c++) {
          const below = (bRef.data[i * 4 + c] * S[i * 4 + c]) / 255;
          o[i * 4 + c] = Math.max(0, Math.min(255, Math.round(below * (1 - a) + P[i * 4 + c] * a)));
        }
        o[i * 4 + 3] = 255;
      }
      return o;
    };
    const cRef = comp(pRef.data, sRef.data);
    const cEnc = comp(pEnc.data, sEnc.data);
    res.layers[name].widths[w] = {
      product_over_grey: measure(pRef.data, pEnc.data, true),
      shadow: measure(sRef.data, sEnc.data, false),
      scene_on_rect: measure(cRef, cEnc, false),
      bytes: { product_webp_nearlossless_q60: pEncBuf.length, shadow_webp_lossless: sEncBuf.length },
    };
    console.log(name, w, JSON.stringify(res.layers[name].widths[w]));
  }
}
// the base: the site's AVIF q70 files, decoded, vs base.png resized losslessly (file level, information)
for (const w of [1280, 1920, 2720]) {
  const f = join(REPO, `site/web/public/media/house/living-room/warm-modern/M0/base/shell.${w}.avif`);
  if (!existsSync(f)) { res.base[w] = 'missing'; continue; }
  const enc = await decode(readFileSync(f));
  const ref = await raw(sharp(join(LD, 'base.png')).removeAlpha().ensureAlpha(), w);
  res.base[w] = measure(ref.data, enc.data, false);
  console.log('base avif', w, JSON.stringify(res.base[w]));
}
writeFileSync(join(OUT, 'data/encode.json'), JSON.stringify(res, null, 1));
