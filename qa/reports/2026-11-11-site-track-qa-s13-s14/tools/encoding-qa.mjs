/**
 * qa-agent, 2026-11-11 (S14 ת30 at a8104956; first written for S12 at b94c5bc1): my own re-measurement, my own code (the S8–S10 method,
 * tools/base-quality.mjs there), against my thresholds: p99 ≤ 6, p99.9 ≤ 10, ≤ 0.2% of pixels above 8 levels (worst
 * channel, 8-bit), ΔE00 p99 ≤ 3.5. What the browser paints, built file vs the approved pixels (the same resize,
 * lossless PNG), every other layer answered losslessly in both, ref twice for the pipeline's own noise.
 *
 *  ENGINE (canvas.room-canvas, the engine started), views 1920@1, 1280@1, 400@1, 400@3, 1280 zoomed into the slot:
 *   wm base AVIF q70 · wm base WebP fallback · wm set B, A, C product layers (inside the set's area) ·
 *   Nordic base AVIF · Nordic base WebP fallback
 *  POSTER (img.poster, the page at rest, no intent: the engine not started), views 1920@1, 1280@1, 400@1, 400@3:
 *   wm base AVIF and WebP · Nordic base AVIF and WebP
 *  FILE at 1:1 (no browser): every base file the build made vs its reference, and candidate settings, for S12 question 4
 *
 *   QA_BASE=http://127.0.0.1:8799 QA_COPY=<copy>/site QA_REPO=<copy root> QA_OUT=<qa folder> node encoding-qa.mjs [engine|poster|file ...]
 */
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const COPY = process.env.QA_COPY;
const REPO = process.env.QA_REPO;
const OUT = process.env.QA_OUT;
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const require = createRequire(join(COPY, 'package.json'));
const { chromium } = require('playwright-core');
const sharp = require('sharp');
const PARTS = process.argv.slice(2).length ? process.argv.slice(2) : ['file', 'poster', 'engine'];
const DIST = join(COPY, 'web/dist/media');

// ---------- the approved pixels ----------
const wm = JSON.parse(readFileSync(join(COPY, 'tools/house/living-room.warm-modern.json'), 'utf8'));
const LAY = join(REPO, wm.pilot, wm.layers_dir);
const WM_BASE = join(LAY, 'base.png');
const house = JSON.parse(readFileSync(join(COPY, '.generated/house.living-room.warm-modern.json'), 'utf8'));
const RECT = house.scene.slots.cushions.product.rect;
const ASPECT = house.scene.aspect;
const SETS = house.sets.map((s) => ({ id: s.id, position: s.position }));
const WM_DEF = house.sets.find((x) => x.position === 1)?.id ?? 'B';
const WM_COMPOSITE = join(REPO, wm.pilot, wm.approved.composites[WM_DEF]);
const temp = JSON.parse(readFileSync(join(COPY, 'tools/temp/living-room.nordic.json'), 'utf8'));
const manifest = JSON.parse(readFileSync(join(REPO, 'assets/manifest.json'), 'utf8'));
const NORDIC_SRC = join(REPO, manifest.assets.find((a) => a.id === temp.source_manifest_id).path);

const cache = new Map();
const memo = (k, f) => (cache.has(k) ? cache.get(k) : (cache.set(k, f()), cache.get(k)));
const refBase = (src, w, removeAlpha) => memo(`${src}@${w}`, () => (removeAlpha ? sharp(src).removeAlpha() : sharp(src)).resize({ width: w }).png({ compressionLevel: 1 }).toBuffer());
function refProduct(setId, w) {
  return memo(`prod-${setId}@${w}`, () => {
    const W = 2720;
    const H = 1530;
    const cut = { left: Math.round(RECT[0] * W), top: Math.round(RECT[2] * H), width: Math.round((RECT[1] - RECT[0]) * W), height: Math.round((RECT[3] - RECT[2]) * H) };
    return sharp(join(LAY, `cushions-set-${setId}.png`)).ensureAlpha().extract(cut).resize({ width: Math.round((cut.width * w) / W) }).png({ compressionLevel: 1 }).toBuffer();
  });
}
const built = (rel) => readFileSync(join(DIST, rel));

// ---------- the measure (my own, as in S8–S10) ----------
const lin = (c) => {
  c /= 255;
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
};
const LUT = Float64Array.from({ length: 256 }, (_, i) => lin(i));
function lab(r, g, b) {
  const R = LUT[r], G = LUT[g], B = LUT[b];
  let x = (0.4124564 * R + 0.3575761 * G + 0.1804375 * B) / 0.95047, y = 0.2126729 * R + 0.7151522 * G + 0.072175 * B, z = (0.0193339 * R + 0.119192 * G + 0.9503041 * B) / 1.08883;
  const f = (t) => (t > 216 / 24389 ? Math.cbrt(t) : ((24389 / 27) * t + 16) / 116);
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
/** ref and x: {data (RGB), w, h}; box: optional {x0,x1,y0,y1} */
function compare(ref, x, box) {
  const b = box ?? { x0: 0, x1: ref.w, y0: 0, y1: ref.h };
  const hist = new Uint32Array(256);
  const des = [];
  let n = 0;
  for (let y = b.y0; y < b.y1; y++)
    for (let xx = b.x0; xx < b.x1; xx++) {
      const i = (y * ref.w + xx) * 3;
      const d = Math.max(Math.abs(ref.data[i] - x.data[i]), Math.abs(ref.data[i + 1] - x.data[i + 1]), Math.abs(ref.data[i + 2] - x.data[i + 2]));
      hist[d]++;
      n++;
      // ΔE on every 3rd pixel (deterministic sampling); 0 for identical pixels
      if (process.env.QA_DE_ALL === '1' || n % 3 === 0) des.push(d ? de2000(lab(ref.data[i], ref.data[i + 1], ref.data[i + 2]), lab(x.data[i], x.data[i + 1], x.data[i + 2])) : 0);
    }
  const pct = (q) => { let c = 0; for (let d = 0; d < 256; d++) { c += hist[d]; if (c >= q * n) return d; } return 255; };
  let max = 0;
  for (let d = 255; d >= 0; d--) if (hist[d]) { max = d; break; }
  let over = 0;
  for (let d = 9; d < 256; d++) over += hist[d];
  des.sort((a, c) => a - c);
  const m = { px: n, p99: pct(0.99), p999: pct(0.999), max, over8_pct: +((100 * over) / n).toFixed(3), de_p99: +des[Math.floor(des.length * 0.99)].toFixed(2) };
  m.pass = m.p99 <= 6 && m.p999 <= 10 && m.over8_pct <= 0.2 && m.de_p99 <= 3.5;
  return m;
}
const fmt = (m) => `${m.p99}/${m.p999}/${m.max} · ${m.over8_pct}% · ΔE ${m.de_p99}${m.pass ? '' : '  FAIL'}`;

const res = { base: BASE, run_at: new Date().toISOString(), threshold: 'p99 ≤ 6, p99.9 ≤ 10, ≤ 0.2% above 8 levels, ΔE00 p99 ≤ 3.5', engine: [], poster: [], file: [] };
const resFile = join(OUT, process.env.QA_RESFILE ?? 'data/encoding-qa.json');
const prev = existsSync(resFile) ? JSON.parse(readFileSync(resFile, 'utf8')) : null;
for (const k of ['engine', 'poster', 'file']) if (!PARTS.includes(k) && prev?.[k]) res[k] = prev[k];
const save = () => writeFileSync(resFile, JSON.stringify(res, null, 1));

// ---------- FILE at 1:1 ----------
if (PARTS.includes('file')) {
  const raw = async (buf) => {
    const { data, info } = await sharp(buf).removeAlpha().raw().toBuffer({ resolveWithObject: true });
    return { data, w: info.width, h: info.height };
  };
  const jobs = [
    { house: 'warm-modern', src: WM_BASE, alpha: true, dir: 'house/living-room/warm-modern/M0/base', widths: [1280, 1920, 2720] },
    { house: 'nordic', src: NORDIC_SRC, alpha: false, dir: 'rooms/living-room/nordic/M0/base', widths: [1280, 1920, 2752] },
  ];
  for (const j of jobs)
    for (const w of j.widths) {
      const ref = await raw(await refBase(j.src, w, j.alpha));
      const row = { house: j.house, width: w, built: {}, candidates: {} };
      for (const fmtName of ['avif', 'webp']) {
        const f = built(`${j.dir}/shell.${w}.${fmtName}`);
        row.built[fmtName] = { kb: +(f.length / 1024).toFixed(1), ...compare(ref, await raw(f)) };
      }
      // candidates for the poster widths (the ones a poster is painted from on the five views)
      if (w <= 1920) {
        const src = await refBase(j.src, w, j.alpha);
        for (const [name, enc] of [
          ['avif-q80', (s) => s.avif({ quality: 80, effort: 4 })],
          ['avif-q90', (s) => s.avif({ quality: 90, effort: 4 })],
          ['webp-q95', (s) => s.webp({ quality: 95, effort: 5 })],
          ['webp-nl60', (s) => s.webp({ nearLossless: true, quality: 60, effort: 5 })],
          ['webp-nl80', (s) => s.webp({ nearLossless: true, quality: 80, effort: 5 })],
        ]) {
          const b = await enc(sharp(src)).toBuffer();
          row.candidates[name] = { kb: +(b.length / 1024).toFixed(1), ...compare(ref, await raw(b)) };
        }
      }
      res.file.push(row);
      console.log('file', j.house, w, Object.entries(row.built).map(([k, m]) => `${k} ${m.kb}KB ${fmt(m)}`).join(' | '), '||', Object.entries(row.candidates).map(([k, m]) => `${k} ${m.kb}KB ${fmt(m)}`).join(' | '));
      save();
    }
}

// ---------- the browser ----------
const browser = PARTS.some((p) => p !== 'file')
  ? await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-background-networking'] })
  : null;
const WM_BASE_RE = /\/media\/house\/living-room\/warm-modern\/M0\/base\/shell\.(\d+)\.(avif|webp)$/;
const WM_PROD_RE = /\/media\/house\/living-room\/warm-modern\/M0\/slots\/cushions\/(\d)\.product\.(\d+)\.webp$/;
const N_BASE_RE = /\/media\/rooms\/living-room\/nordic\/M0\/base\/shell\.(\d+)\.(avif|webp)$/;
const WM_POSTER_RE = /\/media\/house\/living-room\/warm-modern\/M0\/poster\/default\.(\d+)\.(avif|webp)$/;
const png = (b) => ({ body: b, type: 'image/png' });
const ANS = {
  wmBaseRef: (m) => refBase(WM_BASE, Number(m[1]), true).then(png),
  wmBaseAvif: (m) => ({ body: built(`house/living-room/warm-modern/M0/base/shell.${m[1]}.avif`), type: 'image/avif' }),
  wmBaseWebp: (m) => ({ body: built(`house/living-room/warm-modern/M0/base/shell.${m[1]}.webp`), type: 'image/webp' }),
  wmProdRef: (m) => refProduct(SETS.find((s) => s.position === Number(m[1])).id, Number(m[2])).then(png),
  wmProdBuilt: (m) => ({ body: built(`house/living-room/warm-modern/M0/slots/cushions/${m[1]}.product.${m[2]}.webp`), type: 'image/webp' }),
  nBaseRef: (m) => refBase(NORDIC_SRC, Number(m[1]), false).then(png),
  wmPosterRef: (m) => refBase(WM_COMPOSITE, Number(m[1]), true).then(png),
  wmPosterAvif: (m) => ({ body: built(`house/living-room/warm-modern/M0/poster/default.${m[1]}.avif`), type: 'image/avif' }),
  wmPosterWebp: (m) => ({ body: built(`house/living-room/warm-modern/M0/poster/default.${m[1]}.webp`), type: 'image/webp' }),
  nBaseAvif: (m) => ({ body: built(`rooms/living-room/nordic/M0/base/shell.${m[1]}.avif`), type: 'image/avif' }),
  nBaseWebp: (m) => ({ body: built(`rooms/living-room/nordic/M0/base/shell.${m[1]}.webp`), type: 'image/webp' }),
};
async function page(v, answers) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: v.w, height: v.h }, deviceScaleFactor: v.dpr, isMobile: v.dpr > 1, hasTouch: v.dpr > 1, reducedMotion: 'reduce', extraHTTPHeaders: { 'cf-connecting-ip': '203.0.113.201' } });
    ctx.setDefaultTimeout(120000);
  const p = await ctx.newPage();
  const served = [];
  for (const [re, fn] of answers)
    await p.route(re, async (route) => {
      const m = re.exec(new URL(route.request().url()).pathname);
      const a = await fn(m);
      served.push(`${m[0].split('/').slice(-2).join('/')}→${a.type}`);
      await route.fulfill({ status: 200, contentType: a.type, body: a.body, headers: { 'cache-control': 'no-store' } });
    });
  return { ctx, p, served };
}
const hide = (p, sel) => p.evaluate((s) => document.querySelectorAll(s).forEach((el) => (el.style.visibility = 'hidden')), sel);
async function still(locator) {
  let shot = await locator.screenshot();
  for (let i = 0; i < 30; i++) {
    const next = await locator.screenshot();
    if (next.equals(shot)) return shot;
    shot = next;
  }
  return shot;
}
async function rgb(buf) {
  const { data, info } = await sharp(buf).removeAlpha().raw().toBuffer({ resolveWithObject: true });
  return { data, w: info.width, h: info.height, buf };
}

/** the engine's canvas, the slot's set chosen, optionally zoomed; with the answers given */
async function engineShot(url, v, answers, slot, position) {
  const { ctx, p, served } = await page(v, answers);
  await p.goto(`${BASE}${url}`, { waitUntil: 'load' });
  await p.locator('button.hotspot').first().waitFor({ state: 'attached', timeout: 120000 });
  const sb = await p.locator('section.stage').boundingBox();
  await p.mouse.click(sb.x + 20, sb.y + sb.height / 2);
  for (let i = 0; i < 160 && !(await p.evaluate(() => window.__hdEngine?.ready)); i++) await p.waitForTimeout(250);
  if (position && position !== 1) await p.evaluate(([s, pos]) => window.__hdEngine.setSelection(s, pos, 0), [slot, position]);
  if (v.zoom) {
    const dialog = p.getByRole('dialog');
    for (let i = 0; i < 6 && !(await dialog.isVisible()); i++) {
      await p.locator(`button.hotspot[data-slot="${slot}"]`).focus();
      await p.keyboard.press('Enter');
      await p.waitForTimeout(1500);
    }
    await hide(p, '[role="dialog"], .wheel, .wheel-wrap');
    // the wheel opens on the slot's current option; set it again in case the wheel's preview moved it
    if (position) await p.evaluate(([s, pos]) => window.__hdEngine.setSelection(s, pos, 0), [slot, position]);
  }
  await hide(p, '.stage-ui, .hotspots, .stage-temp-note, .outlines, .stage-back, .stage-vignette');
  await p.mouse.move(0, 0);
  await p.waitForTimeout(800);
  const shot = await still(p.locator('canvas.room-canvas'));
  const eng = await p.evaluate(() => ({ cam: { ...window.__hdEngine.cam }, vp: { ...window.__hdEngine.vp } }));
  await ctx.close();
  return { ...(await rgb(shot)), eng, served };
}
/** the slot's area in the canvas, through the engine's camera (frame u/v → canvas pixels) */
function within(c) {
  const k = c.w / c.eng.vp.w;
  const fw = Math.max(c.eng.vp.w, c.eng.vp.h * ASPECT) * c.eng.cam.z;
  const fh = fw / ASPECT;
  const x = (u) => Math.round((c.eng.vp.w / 2 + (u - c.eng.cam.cu) * fw) * k);
  const y = (vv) => Math.round((c.eng.vp.h / 2 + (vv - c.eng.cam.cv) * fh) * k);
  return { x0: Math.max(0, x(RECT[0])), x1: Math.min(c.w, x(RECT[1])), y0: Math.max(0, y(RECT[2])), y1: Math.min(c.h, y(RECT[3])) };
}
/** the poster at rest: no pointer, no focus, the engine not started; the painted <img> */
async function posterShot(url, v, answers) {
  const { ctx, p, served } = await page(v, answers);
  await p.goto(`${BASE}${url}`, { waitUntil: 'load' });
  const img = p.locator('img.poster');
  await img.waitFor({ state: 'visible', timeout: 120000 });
  await p.waitForFunction(() => {
    const i = document.querySelector('img.poster');
    return i && i.complete && i.naturalWidth > 0;
  }, null, { timeout: 120000 });
  await hide(p, '.stage-ui, .hotspots, .stage-temp-note, .outlines, .stage-back, .stage-vignette, header, .site-header, canvas.room-canvas');
  const started = await p.evaluate(() => !!window.__hdEngine);
  const info = await p.evaluate(() => {
    const i = document.querySelector('img.poster');
    const r = i.getBoundingClientRect();
    return { src: i.currentSrc.split('/').slice(-1)[0], natural: [i.naturalWidth, i.naturalHeight], box: [r.width, r.height], fit: getComputedStyle(i).objectFit };
  });
  await p.waitForTimeout(400);
  const shot = await still(img);
  await ctx.close();
  return { ...(await rgb(shot)), served, started, info };
}

const VIEWS = [
  { id: '2560@1', w: 2560, h: 1440, dpr: 1, extra: true },
  { id: '1440@1', w: 1440, h: 900, dpr: 1, extra: true },
  { id: '820@2', w: 820, h: 1180, dpr: 2, extra: true },
  { id: '390@3', w: 390, h: 844, dpr: 3, extra: true },
  { id: '1920@1', w: 1920, h: 1080, dpr: 1 },
  { id: '1280@1', w: 1280, h: 720, dpr: 1 },
  { id: '400@1', w: 400, h: 800, dpr: 1 },
  { id: '400@3', w: 400, h: 800, dpr: 3 },
  { id: '1280-zoom', w: 1280, h: 720, dpr: 1, zoom: true },
];
const WM_URL = '/rooms/living-room/?style=warm-modern';
const N_URL = '/rooms/living-room/';

if (PARTS.includes('poster')) {
  const PV = VIEWS.filter((x) => !x.zoom && (!process.env.QA_VIEWS || process.env.QA_VIEWS.split(',').includes(x.id)));
  for (const v of PV) {
    for (const [hname, url, re, ref, avif, webp] of [
      ['warm-modern', WM_URL, WM_POSTER_RE, ANS.wmPosterRef, ANS.wmPosterAvif, ANS.wmPosterWebp],
      ['nordic', N_URL, N_BASE_RE, ANS.nBaseRef, ANS.nBaseAvif, ANS.nBaseWebp],
    ]) {
      const R = await posterShot(url, v, [[re, ref]]);
      const R2 = await posterShot(url, v, [[re, ref]]);
      const A = await posterShot(url, v, [[re, avif]]);
      const Wp = await posterShot(url, v, [[re, webp]]);
      const row = { house: hname, view: v.id, extra: !!v.extra, info: A.info, engine_started: A.started, size: [R.w, R.h], ref_vs_ref: compare(R, R2), avif: compare(R, A), webp: compare(R, Wp), served: { ref: R.served, avif: A.served } };
      res.poster.push(row);
      if (['1920@1', '400@3', '1280@1'].includes(v.id)) await sharp(A.buf).jpeg({ quality: 85 }).toFile(join(OUT, 'overlays', `poster-${hname}-${v.id.replace('@', 'x')}.jpg`));
      console.log('poster', hname, v.id, JSON.stringify(A.info), 'engine', A.started, '| ref²', fmt(row.ref_vs_ref), '| avif', fmt(row.avif), '| webp', fmt(row.webp));
      save();
    }
  }
}

// the WebP fallback (browsers without AVIF): candidates answered in place of the poster, warm-modern, the core views
if (PARTS.includes('fallback')) {
  res.fallback = [];
  const CANDS = [
    ['webp-nl60 (built)', null],
    ['webp-q90', (sh) => sh.webp({ quality: 90, effort: 5 })],
    ['webp-q95', (sh) => sh.webp({ quality: 95, effort: 5 })],
    ['webp-q100', (sh) => sh.webp({ quality: 100, effort: 5 })],
    ['webp-nl80', (sh) => sh.webp({ nearLossless: true, quality: 80, effort: 5 })],
  ];
  const enc = (name, f, w) =>
    memo(`fb-${name}@${w}`, async () => (f ? f(sharp(await refBase(WM_COMPOSITE, w, true))).toBuffer() : built(`house/living-room/warm-modern/M0/poster/default.${w}.webp`)));
  for (const v of VIEWS.filter((x) => ['1920@1', '1280@1', '400@1', '400@3', '390@3'].includes(x.id))) {
    const R = await posterShot(WM_URL, v, [[WM_POSTER_RE, ANS.wmPosterRef]]);
    for (const [name, f] of CANDS) {
      const X = await posterShot(WM_URL, v, [[WM_POSTER_RE, async (m) => ({ body: await enc(name, f, Number(m[1])), type: 'image/webp' })]]);
      const w = Number(/default\.(\d+)/.exec(X.info.src)?.[1] ?? 0);
      const kb = +((await enc(name, f, w)).length / 1024).toFixed(0);
      const row = { view: v.id, cand: name, file: X.info.src, kb, ...compare(R, X) };
      res.fallback.push(row);
      console.log('fallback', v.id, name, X.info.src, `${kb} KB`, fmt(row));
      save();
    }
  }
}

// the handoff: the poster at rest (built) vs the engine's canvas once it starts (built, set B), same view
if (PARTS.includes('handoff')) {
  res.handoff = [];
  for (const v of VIEWS.filter((x) => ['1920@1', '1280@1', '400@3'].includes(x.id))) {
    const P = await posterShot(WM_URL, v, []);
    const E = await engineShot(WM_URL, v, [], 'cushions', 1);
    const same = P.w === E.w && P.h === E.h;
    const row = { view: v.id, poster: [P.w, P.h], canvas: [E.w, E.h], ...(same ? compare(P, E) : { note: 'sizes differ' }) };
    res.handoff.push(row);
    console.log('handoff', v.id, JSON.stringify([P.w, P.h]), JSON.stringify([E.w, E.h]), same ? fmt(row) : 'sizes differ');
    save();
  }
}

const VIEW_ONLY = process.env.QA_VIEWS ? process.env.QA_VIEWS.split(',') : null;
const REPS = Number(process.env.QA_REPS ?? 1);
if (PARTS.includes('engine')) {
  for (const v of VIEWS.filter((x) => !VIEW_ONLY || VIEW_ONLY.includes(x.id))) for (let rep = 0; rep < REPS; rep++) {
    // warm-modern: the base (AVIF and WebP) with set B; each set's product layer with the base losslessly
    const refAll = [
      [WM_BASE_RE, ANS.wmBaseRef],
      [WM_PROD_RE, ANS.wmProdRef],
    ];
    const RB = await engineShot(WM_URL, v, refAll, 'cushions', 1);
    const RB2 = await engineShot(WM_URL, v, refAll, 'cushions', 1);
    const AV = await engineShot(WM_URL, v, [[WM_BASE_RE, ANS.wmBaseAvif], [WM_PROD_RE, ANS.wmProdRef]], 'cushions', 1);
    const WB = await engineShot(WM_URL, v, [[WM_BASE_RE, ANS.wmBaseWebp], [WM_PROD_RE, ANS.wmProdRef]], 'cushions', 1);
    const row = { house: 'warm-modern', view: v.id, size: [RB.w, RB.h], ref_vs_ref: compare(RB, RB2), base_avif: compare(RB, AV), base_webp: compare(RB, WB), sets: {} };
    for (const s of SETS) {
      const R = s.position === 1 ? RB : await engineShot(WM_URL, v, refAll, 'cushions', s.position);
      const P = await engineShot(WM_URL, v, [[WM_BASE_RE, ANS.wmBaseRef], [WM_PROD_RE, ANS.wmProdBuilt]], 'cushions', s.position);
      const box = within(R);
      row.sets[s.id] = { area_px: (box.x1 - box.x0) * (box.y1 - box.y0), ...compare(R, P, box), whole_frame: compare(R, P) };
    }
    row.rep = rep;
    res.engine.push(row);
    console.log('engine wm', v.id, '| ref²', fmt(row.ref_vs_ref), '| base avif', fmt(row.base_avif), '| webp', fmt(row.base_webp), '|', Object.entries(row.sets).map(([k, m]) => `set ${k} ${fmt(m)}`).join(' | '));
    save();
    // Nordic: the base (AVIF and WebP); its product layers are temporary recolours of the same source
    const NR = await engineShot(N_URL, v, [[N_BASE_RE, ANS.nBaseRef]], 'vase');
    const NR2 = await engineShot(N_URL, v, [[N_BASE_RE, ANS.nBaseRef]], 'vase');
    const NA = await engineShot(N_URL, v, [[N_BASE_RE, ANS.nBaseAvif]], 'vase');
    const NW = await engineShot(N_URL, v, [[N_BASE_RE, ANS.nBaseWebp]], 'vase');
    const nrow = { house: 'nordic', view: v.id, size: [NR.w, NR.h], served: NA.served, ref_vs_ref: compare(NR, NR2), base_avif: compare(NR, NA), base_webp: compare(NR, NW) };
    res.engine.push(nrow);
    console.log('engine nordic', v.id, '| ref²', fmt(nrow.ref_vs_ref), '| base avif', fmt(nrow.base_avif), '| webp', fmt(nrow.base_webp));
    save();
  }
}
if (browser) await browser.close();
save();
