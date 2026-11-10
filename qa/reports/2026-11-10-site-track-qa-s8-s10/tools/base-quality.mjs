/**
 * qa-agent, 2026-11-10 (S10, question 4): the encoding of the warm-modern house's base against the approved file, measured
 * on what the browser paints. The engine composes the house at 2720 (native) from base/shell.2720.avif, so the base's
 * codec residual reaches the screen as it is, resampled once. Here the same page is loaded several times, each time with
 * the base's request answered by another encoding of the same approved pixels:
 *   ref  the approved base itself (base.png = shell-furniture-v3-graded-v3c.png, lossless)
 *   q52  the file the build made (AVIF q52, effort 4: make-house.ts)
 *   q60, q70, q80  sharp, the same call as make-house.ts with another quality
 * and the stage is captured at rest (set B, the default) at 1920×1080 @1, 1280×720 @1, 400×800 @1 and 400×800 @3, and
 * zoomed into the set (the wheel's camera) at 1280×720. Every capture is compared with the ref capture: 8-bit levels,
 * the worst channel per pixel, p99 / p99.9 / max, the share above 4 and 8 levels, and CIEDE2000 mean / p99. Crops of the
 * worst 64×64 block and of a flat wall at ×1 and ×4: ref | q52 | q70 | |q52−ref|×8 | |q70−ref|×8.
 *   QA_BASE=http://127.0.0.1:8799 QA_COPY=<copy>/site QA_REPO=<repo> QA_OUT=<qa folder> QA_TMP=<scratch> node base-quality.mjs
 */
import { createRequire } from 'node:module';
import { mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const COPY = process.env.QA_COPY;
const REPO = process.env.QA_REPO;
const OUT = process.env.QA_OUT;
const TMP = process.env.QA_TMP;
const require = createRequire(join(COPY, 'package.json'));
const { chromium } = require('playwright-core');
const sharp = require('sharp');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OV = join(OUT, 'overlays');
mkdirSync(TMP, { recursive: true });

const approved = join(REPO, 'assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07/layers-v3c/base.png');
const built = join(COPY, 'web/public/media/house/living-room/warm-modern/M0/base/shell.2720.avif');
const enc = { ref: { file: approved, type: 'image/png' }, q52: { file: built, type: 'image/avif' } };
for (const q of [52, 60, 70, 80]) {
  const f = join(TMP, `shell.2720.q${q}.avif`);
  await sharp(approved).removeAlpha().resize({ width: 2720 }).avif({ quality: q, effort: 4 }).toFile(f);
  enc[`q${q}-mine`] = { file: f, type: 'image/avif' };
}
// my q52 must be the build's byte for byte, or the other qualities are not the same recipe
const same52 = Buffer.compare(readFileSync(built), readFileSync(enc['q52-mine'].file)) === 0;
const sizes = Object.fromEntries(Object.entries(enc).map(([k, v]) => [k, +(statSync(v.file).size / 1024).toFixed(1)]));
for (const q of [60, 70, 80]) enc[`q${q}`] = enc[`q${q}-mine`];
delete enc['q60-mine']; delete enc['q70-mine']; delete enc['q80-mine'];
const VARIANTS = ['ref', 'q52', 'q60', 'q70', 'q80'];

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-background-networking'] });
const SLOT = 'cushions';
async function capture(variant, v) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: v.w, height: v.h }, deviceScaleFactor: v.dpr, isMobile: v.dpr > 1, hasTouch: v.dpr > 1, reducedMotion: 'reduce', extraHTTPHeaders: { 'cf-connecting-ip': '203.0.113.83' } });
  const p = await ctx.newPage();
  const served = [];
  await p.route(/\/media\/house\/living-room\/warm-modern\/M0\/base\/shell\.\d+\.(avif|webp)/, (route) => {
    served.push(route.request().url().split('/').pop());
    route.fulfill({ status: 200, contentType: enc[variant].type, body: readFileSync(enc[variant].file), headers: { 'cache-control': 'no-store' } });
  });
  await p.goto(`${BASE}/rooms/living-room/?style=warm-modern`, { waitUntil: 'load' });
  await p.locator('section.stage[data-house="warm-modern"]').waitFor({ timeout: 20000 });
  const sb = await p.locator('section.stage').boundingBox();
  await p.mouse.click(sb.x + 20, sb.y + sb.height / 2);
  for (let i = 0; i < 80; i++) { if (await p.evaluate(() => window.__hdEngine?.ready)) break; await p.waitForTimeout(250); }
  if (v.zoom) {
    await p.locator(`button.hotspot[data-slot="${SLOT}"]`).focus();
    await p.keyboard.press('Enter');
    await p.getByRole('dialog').waitFor({ timeout: 15000 });
    await p.waitForTimeout(1500);
    await p.evaluate(() => document.querySelectorAll('[role="dialog"], .wheel, .wheel-wrap').forEach((el) => (el.style.visibility = 'hidden')));
  }
  await p.evaluate(() => document.querySelectorAll('.stage-ui, .hotspots, .stage-temp-note, .outlines, .stage-back, .stage-vignette').forEach((el) => (el.style.visibility = 'hidden')));
  await p.mouse.move(0, 0);
  await p.waitForTimeout(1500);
  const shot = await p.locator('canvas.room-canvas').screenshot();
  const eng = await p.evaluate(() => ({ cam: { ...window.__hdEngine.cam }, vp: { ...window.__hdEngine.vp }, compWidth: window.__hdEngine.compWidth }));
  await ctx.close();
  const { data, info } = await sharp(shot).removeAlpha().raw().toBuffer({ resolveWithObject: true });
  return { data, w: info.width, h: info.height, png: shot, served, eng };
}

// sRGB 8-bit → Lab (D65), and CIEDE2000
const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
const LUT = Float64Array.from({ length: 256 }, (_, i) => lin(i));
function lab(r, g, b) {
  const R = LUT[r], G = LUT[g], B = LUT[b];
  let x = (0.4124564 * R + 0.3575761 * G + 0.1804375 * B) / 0.95047, y = 0.2126729 * R + 0.7151522 * G + 0.072175 * B, z = (0.0193339 * R + 0.119192 * G + 0.9503041 * B) / 1.08883;
  const f = (t) => (t > 216 / 24389 ? Math.cbrt(t) : (24389 / 27 * t + 16) / 116);
  x = f(x); y = f(y); z = f(z);
  return [116 * y - 16, 500 * (x - y), 200 * (y - z)];
}
function de2000([L1, a1, b1], [L2, a2, b2]) {
  const C1 = Math.hypot(a1, b1), C2 = Math.hypot(a2, b2), Cb = (C1 + C2) / 2, G = 0.5 * (1 - Math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)));
  const a1p = (1 + G) * a1, a2p = (1 + G) * a2, C1p = Math.hypot(a1p, b1), C2p = Math.hypot(a2p, b2);
  const h = (a, b) => { if (a === 0 && b === 0) return 0; const t = (Math.atan2(b, a) * 180) / Math.PI; return t < 0 ? t + 360 : t; };
  const h1p = h(a1p, b1), h2p = h(a2p, b2), dLp = L2 - L1, dCp = C2p - C1p;
  let dhp = 0;
  if (C1p * C2p) { dhp = h2p - h1p; if (dhp > 180) dhp -= 360; else if (dhp < -180) dhp += 360; }
  const dHp = 2 * Math.sqrt(C1p * C2p) * Math.sin((dhp * Math.PI) / 360), Lbp = (L1 + L2) / 2, Cbp = (C1p + C2p) / 2;
  let hbp = h1p + h2p;
  if (C1p * C2p) { if (Math.abs(h1p - h2p) > 180) hbp += h1p + h2p < 360 ? 360 : -360; hbp /= 2; }
  const T = 1 - 0.17 * Math.cos(((hbp - 30) * Math.PI) / 180) + 0.24 * Math.cos((2 * hbp * Math.PI) / 180) + 0.32 * Math.cos(((3 * hbp + 6) * Math.PI) / 180) - 0.2 * Math.cos(((4 * hbp - 63) * Math.PI) / 180);
  const dth = 30 * Math.exp(-(((hbp - 275) / 25) ** 2)), RC = 2 * Math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7));
  const SL = 1 + (0.015 * (Lbp - 50) ** 2) / Math.sqrt(20 + (Lbp - 50) ** 2), SC = 1 + 0.045 * Cbp, SH = 1 + 0.015 * Cbp * T, RT = -Math.sin((2 * dth * Math.PI) / 180) * RC;
  return Math.sqrt((dLp / SL) ** 2 + (dCp / SC) ** 2 + (dHp / SH) ** 2 + RT * (dCp / SC) * (dHp / SH));
}
function compare(ref, x) {
  const n = ref.w * ref.h;
  const hist = new Uint32Array(256);
  const des = [];
  let sumDe = 0;
  for (let i = 0; i < n; i++) {
    const d = Math.max(Math.abs(ref.data[i * 3] - x.data[i * 3]), Math.abs(ref.data[i * 3 + 1] - x.data[i * 3 + 1]), Math.abs(ref.data[i * 3 + 2] - x.data[i * 3 + 2]));
    hist[d]++;
    if (i % 7 === 0) { const e = de2000(lab(ref.data[i * 3], ref.data[i * 3 + 1], ref.data[i * 3 + 2]), lab(x.data[i * 3], x.data[i * 3 + 1], x.data[i * 3 + 2])); des.push(e); sumDe += e; }
  }
  const pct = (q) => { let c = 0; for (let d = 0; d < 256; d++) { c += hist[d]; if (c >= q * n) return d; } return 255; };
  let max = 0; for (let d = 255; d >= 0; d--) if (hist[d]) { max = d; break; }
  const above = (t) => { let c = 0; for (let d = t + 1; d < 256; d++) c += hist[d]; return +((100 * c) / n).toFixed(3); };
  des.sort((a, b) => a - b);
  return { p99: pct(0.99), p999: pct(0.999), max, pct_above_4: above(4), pct_above_8: above(8), de_mean: +(sumDe / des.length).toFixed(3), de_p99: +des[Math.floor(des.length * 0.99)].toFixed(2), de_p999: +des[Math.floor(des.length * 0.999)].toFixed(2) };
}
/** the worst 64×64 block of a residual (mean worst-channel difference), and the flattest bright block (a wall) */
function blocks(ref, x, B = 64) {
  let worst = null, flat = null;
  for (let by = 0; by + B <= ref.h; by += B / 2)
    for (let bx = 0; bx + B <= ref.w; bx += B / 2) {
      let s = 0, m = 0, m2 = 0;
      for (let y = by; y < by + B; y++)
        for (let xx = bx; xx < bx + B; xx++) {
          const i = (y * ref.w + xx) * 3;
          s += Math.max(Math.abs(ref.data[i] - x.data[i]), Math.abs(ref.data[i + 1] - x.data[i + 1]), Math.abs(ref.data[i + 2] - x.data[i + 2]));
          const g = (ref.data[i] + ref.data[i + 1] + ref.data[i + 2]) / 3;
          m += g; m2 += g * g;
        }
      const N = B * B, mean = m / N, sd = Math.sqrt(Math.max(0, m2 / N - mean * mean)), res = s / N;
      if (!worst || res > worst.res) worst = { x: bx, y: by, res: +res.toFixed(2) };
      if (mean > 120 && (!flat || sd < flat.sd)) flat = { x: bx, y: by, sd: +sd.toFixed(2), mean: +mean.toFixed(1) };
    }
  return { worst, flat };
}
async function sheet(caps, at, name, B = 64) {
  const tiles = [];
  const crop = (c) => sharp(c.data, { raw: { width: c.w, height: c.h, channels: 3 } }).extract({ left: at.x, top: at.y, width: B, height: B });
  const diff = (a, b) => { const o = Buffer.alloc(B * B * 3); for (let y = 0; y < B; y++) for (let x = 0; x < B; x++) for (let c = 0; c < 3; c++) { const i = ((at.y + y) * a.w + at.x + x) * 3 + c; o[(y * B + x) * 3 + c] = Math.min(255, Math.abs(a.data[i] - b.data[i]) * 8); } return sharp(o, { raw: { width: B, height: B, channels: 3 } }); };
  const parts = [crop(caps.ref), crop(caps.q52), crop(caps.q70), diff(caps.q52, caps.ref), diff(caps.q70, caps.ref)];
  for (const scale of [1, 4]) {
    const row = [];
    for (const s of parts) row.push(await s.clone().resize(B * scale, B * scale, { kernel: 'nearest' }).png().toBuffer());
    const gap = 4 * scale;
    const W = row.length * B * scale + (row.length - 1) * gap;
    await sharp({ create: { width: W, height: B * scale, channels: 3, background: { r: 255, g: 255, b: 255 } } })
      .composite(row.map((b, i) => ({ input: b, left: i * (B * scale + gap), top: 0 })))
      .png()
      .toFile(join(OV, `${name}-x${scale}.png`));
  }
}

const res = { base: BASE, run_at: new Date().toISOString(), same_q52_as_build: same52, sizes_kb: sizes, views: [] };
for (const v of [
  { id: '1920', w: 1920, h: 1080, dpr: 1 },
  { id: '1280', w: 1280, h: 720, dpr: 1 },
  { id: '400@1', w: 400, h: 800, dpr: 1 },
  { id: '400@3', w: 400, h: 800, dpr: 3 },
  { id: '1280-zoomed', w: 1280, h: 720, dpr: 1, zoom: true },
]) {
  const caps = {};
  for (const k of VARIANTS) caps[k] = await capture(k, v);
  // the ref twice: the pipeline's own noise
  const ref2 = await capture('ref', v);
  const r = { view: v.id, canvas_px: [caps.ref.w, caps.ref.h], engine: caps.ref.eng, served: caps.ref.served, ref_vs_ref: compare(caps.ref, ref2), vs_ref: {} };
  for (const k of VARIANTS.slice(1)) r.vs_ref[k] = compare(caps.ref, caps[k]);
  const b = blocks(caps.ref, caps.q52);
  r.worst_block_q52 = b.worst;
  r.flat_block = b.flat;
  await sheet(caps, b.worst, `base-q-${v.id}-worst`);
  await sheet(caps, b.flat, `base-q-${v.id}-wall`);
  await sharp(caps.q52.png).jpeg({ quality: 85 }).toFile(join(OV, `base-q-${v.id}-q52-full.jpg`));
  res.views.push(r);
  console.log(v.id, JSON.stringify({ ref_vs_ref: r.ref_vs_ref, ...Object.fromEntries(Object.entries(r.vs_ref).map(([k, x]) => [k, `p99 ${x.p99} p99.9 ${x.p999} max ${x.max} >8 ${x.pct_above_8}% dE ${x.de_mean}/${x.de_p99}/${x.de_p999}`])) }));
}
await browser.close();
writeFileSync(join(OUT, 'data/base-quality.json'), JSON.stringify(res, null, 1));
console.log(JSON.stringify({ same52, sizes }, null, 1));
