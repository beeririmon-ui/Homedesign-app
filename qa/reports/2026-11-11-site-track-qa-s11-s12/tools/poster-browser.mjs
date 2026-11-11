/**
 * qa-agent, 2026-11-11 (S12 question 4): the poster as the browser paints it at rest (img.poster, the engine not
 * started), with its requests answered by candidate encodings of the picture the poster should be: the warm-modern
 * house's default composition (the approved composite-set-B) and the Nordic source. ref = the same pixels lossless.
 * Views 1920@1, 1280@1, 400@1, 400@3. Measure: measure.mjs (all pixels for ΔE with QA_DE_ALL=1).
 *   QA_BASE=… QA_COPY=<copy>/site QA_REPO=<copy root> QA_OUT=<qa folder> QA_TOOLS=<tools> node poster-browser.mjs
 */
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
const COPY = process.env.QA_COPY, REPO = process.env.QA_REPO, OUT = process.env.QA_OUT;
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const require = createRequire(join(COPY, 'package.json'));
const sharp = require('sharp');
const { chromium } = require('playwright-core');
const { compare, fmt } = await import(join(process.env.QA_TOOLS, 'measure.mjs'));
const wm = JSON.parse(readFileSync(join(COPY, 'tools/house/living-room.warm-modern.json'), 'utf8'));
const temp = JSON.parse(readFileSync(join(COPY, 'tools/temp/living-room.nordic.json'), 'utf8'));
const manifest = JSON.parse(readFileSync(join(REPO, 'assets/manifest.json'), 'utf8'));
const HOUSES = [
  { name: 'warm-modern', url: '/rooms/living-room/?style=warm-modern', re: /\/media\/house\/living-room\/warm-modern\/M0\/base\/shell\.(\d+)\.(avif|webp)$/, src: join(REPO, wm.pilot, wm.approved.composites.B) },
  { name: 'nordic', url: '/rooms/living-room/', re: /\/media\/rooms\/living-room\/nordic\/M0\/base\/shell\.(\d+)\.(avif|webp)$/, src: join(REPO, manifest.assets.find((a) => a.id === temp.source_manifest_id).path) },
];
const CANDS = {
  ref: (s) => s.png({ compressionLevel: 1 }),
  'avif-q70': (s) => s.avif({ quality: 70, effort: 4 }),
  'avif-q80': (s) => s.avif({ quality: 80, effort: 4 }),
  'avif-q85': (s) => s.avif({ quality: 85, effort: 4 }),
  'avif-q90': (s) => s.avif({ quality: 90, effort: 4 }),
  'webp-q95': (s) => s.webp({ quality: 95, effort: 5 }),
};
const TYPE = { ref: 'image/png', 'webp-q95': 'image/webp' };
const cache = new Map();
const enc = (src, w, c) => {
  const k = `${src}|${w}|${c}`;
  if (!cache.has(k)) cache.set(k, CANDS[c](sharp(src).removeAlpha().resize({ width: w })).toBuffer());
  return cache.get(k);
};
const VIEWS = [
  { id: '1920@1', w: 1920, h: 1080, dpr: 1 },
  { id: '1280@1', w: 1280, h: 720, dpr: 1 },
  { id: '400@1', w: 400, h: 800, dpr: 1 },
  { id: '400@3', w: 400, h: 800, dpr: 3 },
];
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-background-networking'] });
async function shot(h, v, c) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: v.w, height: v.h }, deviceScaleFactor: v.dpr, isMobile: v.dpr > 1, hasTouch: v.dpr > 1, reducedMotion: 'reduce' });
  ctx.setDefaultTimeout(120000);
  const p = await ctx.newPage();
  let file = null;
  await p.route(h.re, async (route) => {
    const m = h.re.exec(new URL(route.request().url()).pathname);
    file = m[0].split('/').pop();
    await route.fulfill({ status: 200, contentType: TYPE[c] ?? 'image/avif', body: await enc(h.src, Number(m[1]), c), headers: { 'cache-control': 'no-store' } });
  });
  await p.goto(`${BASE}${h.url}`, { waitUntil: 'load' });
  await p.waitForFunction(() => { const i = document.querySelector('img.poster'); return i && i.complete && i.naturalWidth > 0; });
  await p.evaluate(() => document.querySelectorAll('.stage-ui, .hotspots, button.hotspot, .stage-temp-note, .outlines, .stage-back, .stage-vignette, canvas.room-canvas').forEach((el) => (el.style.visibility = 'hidden')));
  await p.waitForTimeout(500);
  const loc = p.locator('img.poster');
  let b = await loc.screenshot();
  for (let i = 0; i < 20; i++) { const n = await loc.screenshot(); if (n.equals(b)) break; b = n; }
  await ctx.close();
  const { data, info } = await sharp(b).removeAlpha().raw().toBuffer({ resolveWithObject: true });
  return { data, w: info.width, h: info.height, file };
}
const res = [];
for (const h of HOUSES)
  for (const v of VIEWS) {
    const R = await shot(h, v, 'ref');
    const row = { house: h.name, view: v.id, file: R.file, size: [R.w, R.h], cands: {} };
    for (const c of Object.keys(CANDS).filter((x) => x !== 'ref')) {
      const X = await shot(h, v, c);
      const kb = +((await enc(h.src, Number(/shell\.(\d+)/.exec(R.file)[1]), c)).length / 1024).toFixed(1);
      row.cands[c] = { kb, ...compare(R, X) };
    }
    res.push(row);
    console.log(h.name, v.id, R.file, '|', Object.entries(row.cands).map(([k, m]) => `${k} ${m.kb}KB ${fmt(m)}`).join(' | '));
  }
await browser.close();
writeFileSync(join(OUT, 'data/poster-browser.json'), JSON.stringify(res, null, 1));
