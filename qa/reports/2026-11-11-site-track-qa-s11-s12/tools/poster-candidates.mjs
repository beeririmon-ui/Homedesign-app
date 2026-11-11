/**
 * qa-agent, 2026-11-11 (S12 question 4): encodings for the poster, measured on the file at 1:1 (what a desktop poster
 * paints: shell.1280 at 1280@1, shell.1920 at 1920@1, natural size into the box, cover). The warm-modern poster's source
 * is the approved default composition (composite-set-B, what the engine draws at rest), the Nordic one its source.
 * The same measure as encoding-qa.mjs (worst channel p99 / p99.9 / max, % above 8, ΔE00 p99 on every 3rd pixel).
 *   QA_COPY=<copy>/site QA_REPO=<copy root> QA_OUT=<qa folder> node poster-candidates.mjs
 */
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
const COPY = process.env.QA_COPY, REPO = process.env.QA_REPO, OUT = process.env.QA_OUT;
const require = createRequire(join(COPY, 'package.json'));
const sharp = require('sharp');
const src = await import(join(process.env.QA_TOOLS, 'measure.mjs'));
const wm = JSON.parse(readFileSync(join(COPY, 'tools/house/living-room.warm-modern.json'), 'utf8'));
const temp = JSON.parse(readFileSync(join(COPY, 'tools/temp/living-room.nordic.json'), 'utf8'));
const manifest = JSON.parse(readFileSync(join(REPO, 'assets/manifest.json'), 'utf8'));
const SOURCES = {
  'warm-modern (set B composite)': join(REPO, wm.pilot, wm.approved.composites.B),
  nordic: join(REPO, manifest.assets.find((a) => a.id === temp.source_manifest_id).path),
};
const CANDS = [
  ['avif q70 4:2:0 (today)', (s) => s.avif({ quality: 70, effort: 4 })],
  ['avif q70 4:4:4', (s) => s.avif({ quality: 70, effort: 4, chromaSubsampling: '4:4:4' })],
  ['avif q75 4:4:4', (s) => s.avif({ quality: 75, effort: 4, chromaSubsampling: '4:4:4' })],
  ['avif q80 4:4:4', (s) => s.avif({ quality: 80, effort: 4, chromaSubsampling: '4:4:4' })],
  ['avif q85 4:4:4', (s) => s.avif({ quality: 85, effort: 4, chromaSubsampling: '4:4:4' })],
  ['avif q90 4:2:0', (s) => s.avif({ quality: 90, effort: 4 })],
  ['jpeg q90 4:4:4 mozjpeg', (s) => s.jpeg({ quality: 90, chromaSubsampling: '4:4:4', mozjpeg: true })],
  ['jpeg q94 4:4:4 mozjpeg', (s) => s.jpeg({ quality: 94, chromaSubsampling: '4:4:4', mozjpeg: true })],
  ['webp q95 (today)', (s) => s.webp({ quality: 95, effort: 5 })],
  ['webp near-lossless 60', (s) => s.webp({ nearLossless: true, quality: 60, effort: 5 })],
];
const raw = async (b) => { const { data, info } = await sharp(b).removeAlpha().raw().toBuffer({ resolveWithObject: true }); return { data, w: info.width, h: info.height }; };
const res = [];
for (const [name, file] of Object.entries(SOURCES))
  for (const w of [1280, 1920]) {
    const ref = await sharp(file).removeAlpha().resize({ width: w }).png({ compressionLevel: 1 }).toBuffer();
    const R = await raw(ref);
    for (const [cn, enc] of CANDS) {
      const b = await enc(sharp(ref)).toBuffer();
      const m = src.compare(R, await raw(b));
      res.push({ source: name, width: w, candidate: cn, kb: +(b.length / 1024).toFixed(1), ...m });
      console.log(name, w, cn.padEnd(26), `${(b.length / 1024).toFixed(0)} KB`.padStart(8), src.fmt(m));
    }
  }
writeFileSync(join(OUT, 'data/poster-candidates.json'), JSON.stringify(res, null, 1));
