/**
 * qa-agent, 2026-11-11 (ת29/ת30 follow-up at a8104956): the warm-modern house's handoff from the poster (the approved
 * set-B composite, what the page rests on) to the engine's canvas (base + set-B layers, once the first intent starts it).
 * Same page, same view: the poster at rest, then the engine started by a pointer move over the stage (no click), the UI
 * hidden in both. Saved side by side; the best alignment between them searched over scale and shift (grey, 1/4 size),
 * and the difference left after it (is the jump framing, or the picture itself?).
 *   QA_BASE=… QA_COPY=… QA_OUT=… node handoff.mjs
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
const COPY = process.env.QA_COPY;
const OUT = process.env.QA_OUT;
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const require = createRequire(join(COPY, 'package.json'));
const { chromium } = require('playwright-core');
const sharp = require('sharp');
const URL_WM = '/rooms/living-room/?style=warm-modern';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-background-networking'] });
const hide = (p) =>
  p.addStyleTag({ content: '.stage-ui,.hotspots,.stage-temp-note,.outlines,.stage-back,.stage-vignette,.hotspot,header,.site-header{visibility:hidden!important}' });
const VIEWS = [
  { id: '1920@1', w: 1920, h: 1080, dpr: 1 },
  { id: '1280@1', w: 1280, h: 720, dpr: 1 },
  { id: '400@3', w: 400, h: 800, dpr: 3 },
];
const grey = async (buf, w) => {
  const { data, info } = await sharp(buf).greyscale().resize({ width: w }).raw().toBuffer({ resolveWithObject: true });
  return { d: data, w: info.width, h: info.height };
};
/** mean abs difference of b, scaled by s about the centre and shifted by (dx, dy), against a; central 80% only */
function score(a, b, s, dx, dy) {
  let sum = 0;
  let n = 0;
  const cx = a.w / 2, cy = a.h / 2;
  for (let y = Math.floor(a.h * 0.1); y < a.h * 0.9; y += 2)
    for (let x = Math.floor(a.w * 0.1); x < a.w * 0.9; x += 2) {
      const bx = Math.round((x - cx - dx) / s + cx), by = Math.round((y - cy - dy) / s + cy);
      if (bx < 0 || by < 0 || bx >= b.w || by >= b.h) continue;
      sum += Math.abs(a.d[y * a.w + x] - b.d[by * b.w + bx]);
      n++;
    }
  return sum / n;
}
const res = [];
for (const v of VIEWS) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: v.w, height: v.h }, deviceScaleFactor: v.dpr, isMobile: v.dpr > 1, hasTouch: v.dpr > 1, reducedMotion: 'reduce', bypassCSP: true });
  ctx.setDefaultTimeout(120000);
  const p = await ctx.newPage();
  await p.goto(`${BASE}${URL_WM}`, { waitUntil: 'load' });
  await p.waitForFunction(() => {
    const i = document.querySelector('img.poster');
    return i && i.complete && i.naturalWidth > 0;
  });
  await hide(p);
  await p.waitForTimeout(800);
  const stage = p.locator('section.stage');
  const box = await stage.boundingBox();
  const poster = await p.screenshot({ clip: box });
  const pinfo = await p.evaluate(() => {
    const i = document.querySelector('img.poster');
    const cs = getComputedStyle(i);
    return { src: i.currentSrc.split('/').pop(), fit: cs.objectFit, pos: cs.objectPosition, box: [i.clientWidth, i.clientHeight] };
  });
  // the first intent
  // as my encoding tool starts it (S11–S12): a click near the stage's edge, away from any product
  await p.mouse.click(box.x + 20, box.y + box.height / 2);
  for (let i = 0; i < 160 && !(await p.evaluate(() => window.__hdEngine?.ready)); i++) await p.waitForTimeout(250);
  await p.mouse.move(0, 0).catch(() => undefined);
  await hide(p);
  await p.waitForTimeout(1500);
  const eng = await p.evaluate(() => ({ cam: { ...window.__hdEngine.cam }, vp: { ...window.__hdEngine.vp }, posterOpacity: getComputedStyle(document.querySelector('img.poster')).opacity, canvasOpacity: getComputedStyle(document.querySelector('canvas.room-canvas')).opacity }));
  const engine = await p.screenshot({ clip: box });
  await ctx.close();
  const W = 320;
  const a = await grey(poster, W);
  const b = await grey(engine, W);
  const base = score(a, b, 1, 0, 0);
  let best = { s: 1, dx: 0, dy: 0, m: base };
  for (let s = 0.9; s <= 1.12; s += 0.005)
    for (let dx = -16; dx <= 16; dx += 1)
      for (let dy = -10; dy <= 10; dy += 1) {
        const m = score(a, b, s, dx, dy);
        if (m < best.m) best = { s: +s.toFixed(3), dx, dy, m };
      }
  // full resolution, RGB: the signed mean per channel (a tonal shift?), and the 99th percentile of a blurred difference
  // (σ 2 px: what is left once the two encodings' pixel noise is smoothed away)
  const rgb = async (buf, blur) => (await (blur ? sharp(buf).removeAlpha().blur(blur) : sharp(buf).removeAlpha()).raw().toBuffer({ resolveWithObject: true }));
  const P = await rgb(poster, 0), E = await rgb(engine, 0), Pb = await rgb(poster, 2), Eb = await rgb(engine, 2);
  const mean = [0, 0, 0];
  const hist = new Uint32Array(256);
  for (let i = 0; i < P.data.length; i += 3) {
    for (let c = 0; c < 3; c++) mean[c] += E.data[i + c] - P.data[i + c];
    hist[Math.max(Math.abs(Eb.data[i] - Pb.data[i]), Math.abs(Eb.data[i + 1] - Pb.data[i + 1]), Math.abs(Eb.data[i + 2] - Pb.data[i + 2]))]++;
  }
  const npx = P.data.length / 3;
  const pct = (q) => { let c = 0; for (let d = 0; d < 256; d++) { c += hist[d]; if (c >= q * npx) return d; } return 255; };
  let over4 = 0;
  for (let d = 5; d < 256; d++) over4 += hist[d];
  const tone = { signed_mean_rgb_engine_minus_poster: mean.map((m) => +(m / npx).toFixed(2)), blurred_p99: pct(0.99), blurred_p999: pct(0.999), blurred_over4_pct: +((100 * over4) / npx).toFixed(3) };
  const row = { view: v.id, poster: pinfo, engine: eng, tone, mad_as_is: +base.toFixed(2), best_alignment: { scale_engine_vs_poster: best.s, dx_px_at_320: best.dx, dy_px_at_320: best.dy, mad: +best.m.toFixed(2) } };
  res.push(row);
  const name = `handoff-${v.id.replace('@', 'x')}`;
  // a 1:1 crop of the sofa's middle (device pixels), poster above, engine below
  {
    const m = await sharp(poster).metadata();
    const cw = Math.min(600, m.width), ch = Math.min(300, Math.round(m.height / 4));
    const left = Math.round(m.width * (v.dpr > 1 ? 0.25 : 0.42)), top = Math.round(m.height * (v.dpr > 1 ? 0.62 : 0.55));
    const c1 = await sharp(poster).extract({ left, top, width: Math.min(cw, m.width - left), height: ch }).toBuffer();
    const c2 = await sharp(engine).extract({ left, top, width: Math.min(cw, m.width - left), height: ch }).toBuffer();
    const cm = await sharp(c1).metadata();
    await sharp({ create: { width: cm.width, height: ch * 2 + 8, channels: 3, background: '#ffffff' } })
      .composite([{ input: c1, left: 0, top: 0 }, { input: c2, left: 0, top: ch + 8 }])
      .png()
      .toFile(join(OUT, 'overlays', `${name}-crop-1to1-poster-top-engine-bottom.png`));
  }
  const half = await sharp(poster).resize({ width: 640 }).toBuffer();
  const half2 = await sharp(engine).resize({ width: 640 }).toBuffer();
  const m1 = await sharp(half).metadata();
  await sharp({ create: { width: 1300, height: m1.height, channels: 3, background: '#ffffff' } })
    .composite([
      { input: half, left: 0, top: 0 },
      { input: half2, left: 660, top: 0 },
    ])
    .jpeg({ quality: 82 })
    .toFile(join(OUT, 'overlays', `${name}-poster-vs-engine.jpg`));
  console.log('handoff', JSON.stringify(row));
}
await browser.close();
writeFileSync(join(OUT, 'data/handoff.json'), JSON.stringify(res, null, 1));
