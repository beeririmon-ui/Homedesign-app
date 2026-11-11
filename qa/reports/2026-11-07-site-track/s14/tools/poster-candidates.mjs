/**
 * frontend-dev, S14 (QA S11–S12 ת30 §4): candidate encodings of the poster at rest, measured as the browser draws them
 * (QA's method: tools/poster-browser.mjs of the QA report; the threshold of site/tools/lib/encoding.ts). The poster's
 * requests are answered with each candidate's bytes; `ref` is the same pixels lossless at the candidate's width. The
 * engine never starts (no intent). Run from site/ (the preview on HD_BASE_URL, default 127.0.0.1:8788):
 *   node --import tsx ../qa/reports/2026-11-07-site-track/s14/tools/poster-candidates.mjs <out.json>
 */
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
const SITE = process.cwd();
const REPO = resolve(SITE, '..');
const require = createRequire(join(SITE, 'package.json'));
const sharp = require('sharp');
const { chromium } = require('@playwright/test');
const { measure, failures } = await import(join(SITE, 'tools/lib/encoding.ts'));
const BASE = process.env.HD_BASE_URL ?? 'http://127.0.0.1:8788';
const OUT = process.argv[2];
const wm = JSON.parse(readFileSync(join(SITE, 'tools/house/living-room.warm-modern.json'), 'utf8'));
const temp = JSON.parse(readFileSync(join(SITE, 'tools/temp/living-room.nordic.json'), 'utf8'));
const manifest = JSON.parse(readFileSync(join(REPO, 'assets/manifest.json'), 'utf8'));
const HOUSES = {
  'warm-modern': { url: '/rooms/living-room/?style=warm-modern', re: /\/media\/house\/living-room\/warm-modern\/M0\/poster\/default\.(\d+)\.(avif|webp)$/, src: join(REPO, wm.pilot, wm.approved.composites.B), alpha: true },
  nordic: { url: '/rooms/living-room/', re: /\/media\/rooms\/living-room\/nordic\/M0\/base\/shell\.(\d+)\.(avif|webp)$/, src: join(REPO, manifest.assets.find((a) => a.id === temp.source_manifest_id).path), alpha: false },
};
const ENC = {
  png: (s) => s.png({ compressionLevel: 1 }),
  'avif-q80': (s) => s.avif({ quality: 80, effort: 4 }),
  'avif-q85': (s) => s.avif({ quality: 85, effort: 4 }),
  'avif-q90': (s) => s.avif({ quality: 90, effort: 4 }),
  'avif-q95': (s) => s.avif({ quality: 95, effort: 4 }),
  'avif-q85-444': (s) => s.avif({ quality: 85, effort: 4, chromaSubsampling: '4:4:4' }),
  'avif-q90-444': (s) => s.avif({ quality: 90, effort: 4, chromaSubsampling: '4:4:4' }),
  'webp-q95': (s) => s.webp({ quality: 95, effort: 5 }),
  'webp-q95-smart': (s) => s.webp({ quality: 95, smartSubsample: true, effort: 5 }),
  'webp-q100-smart': (s) => s.webp({ quality: 100, smartSubsample: true, effort: 5 }),
  'webp-nl20': (s) => s.webp({ nearLossless: true, quality: 20, effort: 5 }),
  'webp-nl40': (s) => s.webp({ nearLossless: true, quality: 40, effort: 5 }),
  'webp-nl60': (s) => s.webp({ nearLossless: true, quality: 60, effort: 5 }),
  'webp-nl80': (s) => s.webp({ nearLossless: true, quality: 80, effort: 5 }),
};
const TYPE = { png: 'image/png' };
const cache = new Map();
const bytes = (h, w, enc) => {
  const k = `${h}|${w}|${enc}`;
  if (!cache.has(k)) {
    const s = sharp(HOUSES[h].src);
    cache.set(k, ENC[enc]((HOUSES[h].alpha ? s.removeAlpha() : s).resize({ width: w })).toBuffer());
  }
  return cache.get(k);
};
const VIEWS = { '1920@1': { w: 1920, h: 1080, dpr: 1 }, '1280@1': { w: 1280, h: 720, dpr: 1 }, '400@1': { w: 400, h: 800, dpr: 1 }, '400@3': { w: 400, h: 800, dpr: 3 }, '1440@1': { w: 1440, h: 900, dpr: 1 } };
// [house, view, file width answered (whatever the page asks for), candidates]
const PLAN = [
  ['warm-modern', '1920@1', 2720, ['avif-q85', 'webp-q95-smart', 'webp-q100-smart', 'webp-nl20', 'webp-nl40', 'webp-nl60']],
  ['warm-modern', '1920@1', 1920, ['avif-q90', 'avif-q95', 'avif-q85-444', 'avif-q90-444', 'webp-q100-smart', 'webp-nl40']],
  ['warm-modern', '1440@1', 2720, ['avif-q85', 'webp-nl40']],
  ['warm-modern', '1280@1', 1280, ['avif-q90', 'webp-q95', 'webp-q95-smart', 'webp-q100-smart', 'webp-nl20', 'webp-nl40', 'webp-nl60']],
  ['warm-modern', '400@1', 1280, ['avif-q90', 'webp-q95-smart', 'webp-nl40']],
  ['warm-modern', '400@3', 2720, ['avif-q85', 'webp-q95-smart', 'webp-q100-smart', 'webp-nl20', 'webp-nl40', 'webp-nl60']],
  ['nordic', '1920@1', 1920, ['avif-q80']],
  ['nordic', '1280@1', 1280, ['avif-q80']],
  ['nordic', '400@1', 1280, ['avif-q80']],
];
const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM ?? '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-background-networking'] });
async function shot(h, v, width, enc) {
  const V = VIEWS[v];
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: V.w, height: V.h }, deviceScaleFactor: V.dpr, isMobile: V.dpr > 1, hasTouch: V.dpr > 1, reducedMotion: 'reduce' });
  const p = await ctx.newPage();
  let asked = null;
  await p.route(HOUSES[h].re, async (route) => {
    asked = HOUSES[h].re.exec(new URL(route.request().url()).pathname)[1];
    await route.fulfill({ status: 200, contentType: TYPE[enc] ?? `image/${enc.split('-')[0]}`, body: await bytes(h, width, enc), headers: { 'cache-control': 'no-store' } });
  });
  await p.goto(`${BASE}${HOUSES[h].url}`);
  await p.waitForFunction(() => { const i = document.querySelector('img.poster'); return i && i.complete && i.naturalWidth > 0; }, null, { timeout: 60000 });
  await p.evaluate(() => document.querySelectorAll('.stage-ui, .hotspots, .stage-temp-note, .outlines, .stage-back, .stage-vignette, canvas.room-canvas').forEach((el) => (el.style.visibility = 'hidden')));
  const loc = p.locator('img.poster');
  let b = await loc.screenshot();
  for (let i = 0; i < 20; i++) { const n = await loc.screenshot(); if (n.equals(b)) break; b = n; }
  const engine = await p.evaluate(() => !!window.__hdEngine);
  await ctx.close();
  const { data, info } = await sharp(b).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  return { data, w: info.width, h: info.height, asked, engine };
}
const res = [];
for (const [h, v, width, cands] of PLAN) {
  const R = await shot(h, v, width, 'png');
  for (const c of cands) {
    const X = await shot(h, v, width, c);
    const m = measure(R.data, X.data, false);
    const kb = +((await bytes(h, width, c)).length / 1024).toFixed(1);
    const row = { house: h, view: v, page_asked: R.asked, file_width: width, candidate: c, kb, drawn: [R.w, R.h], engine: R.engine || X.engine, ...m, pass: failures(m).length === 0 };
    res.push(row);
    console.log(`${h} ${v} asked ${R.asked} answered ${width} ${c} ${kb} KB: ${m.p99}/${m.p999}/${m.max} · ${(m.over8 * 100).toFixed(2)}% · ΔE ${m.de00_p99} ${row.pass ? 'PASS' : 'fail'}`);
  }
}
await browser.close();
writeFileSync(OUT, JSON.stringify(res, null, 1));
