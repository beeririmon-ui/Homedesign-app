/**
 * qa-agent, S17 (2026-11-12): how far the pixel rule of check:rights reaches. Every third supplier original in the cache
 * (the pictures a public build may not ship) is changed the ways a copy gets changed (resized, recompressed, cropped,
 * flipped, colour-shifted, padded…), and each result is compared with the set a PUBLIC build has (no story ledger), by
 * the gate's own fingerprint and rule (tools/lib/rights-content.ts at a988b099): A = dHash ≤ 24; B = dHash ≤ 48 and the
 * 32×32 grey MAD ≤ 3. A result counts as caught when it matches ITS OWN picture (or any picture of the same product).
 *
 *   tsx mut-pixels.mts <copy site dir> <out.json>
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { createRequire } from 'node:module';
import {
  DhashCache,
  LEDGER_SHOP,
  NEAR_MAX_HAMMING,
  NEAR_MAX_MAD32,
  PIXEL_MAX_HAMMING,
  fingerprint,
  hamming,
  mad32,
  readLedger,
  supplierSet,
} from '../build-s17/site/tools/lib/rights-content';

const [SITE_ARG, OUT] = process.argv.slice(2);
const SITE = resolve(SITE_ARG!);
const sharp = createRequire(join(SITE, 'package.json'))('sharp') as typeof import('sharp');
sharp.concurrency(1);
const dh = new DhashCache(join(process.env.QA_CACHE ?? '/tmp', 'qa17-mut-dhash.json'));
const shop = readLedger(join(SITE, '.generated', LEDGER_SHOP))!;
const set = await supplierSet({ site: SITE, ledgers: [shop], cacheDir: join(SITE, '.cache/supplier-images'), hosts: [], dhashes: dh });
const originals = set.pixels.filter((p) => p.file.startsWith('.cache/')).filter((_, i) => i % 3 === 0);

type M = (b: Buffer, w: number, h: number) => Promise<Buffer>;
const S = (b: Buffer) => sharp(b, { failOn: 'none' }).rotate();
const MUT: Record<string, M> = {
  'resize 50% (webp q80)': (b, w) => S(b).resize(Math.round(w / 2)).webp({ quality: 80 }).toBuffer(),
  'resize 25% (jpeg q60)': (b, w) => S(b).resize(Math.round(w / 4)).jpeg({ quality: 60 }).toBuffer(),
  'thumbnail 160 px (webp)': (b) => S(b).resize(160).webp({ quality: 70 }).toBuffer(),
  'thumbnail 96 px (jpeg q50)': (b) => S(b).resize(96).jpeg({ quality: 50 }).toBuffer(),
  'recompress jpeg q35': (b) => S(b).jpeg({ quality: 35 }).toBuffer(),
  'recompress avif q30': (b) => S(b).avif({ quality: 30 }).toBuffer(),
  'crop 5% each side': (b, w, h) => S(b).extract({ left: Math.round(w * 0.05), top: Math.round(h * 0.05), width: Math.round(w * 0.9), height: Math.round(h * 0.9) }).toBuffer(),
  'crop 10% each side': (b, w, h) => S(b).extract({ left: Math.round(w * 0.1), top: Math.round(h * 0.1), width: Math.round(w * 0.8), height: Math.round(h * 0.8) }).toBuffer(),
  'crop left third off': (b, w, h) => S(b).extract({ left: Math.round(w / 3), top: 0, width: w - Math.round(w / 3), height: h }).toBuffer(),
  'crop to the top half': (b, w, h) => S(b).extract({ left: 0, top: 0, width: w, height: Math.round(h / 2) }).toBuffer(),
  'crop a centre square 60%': (b, w, h) => {
    const s = Math.round(Math.min(w, h) * 0.6);
    return S(b).extract({ left: Math.round((w - s) / 2), top: Math.round((h - s) / 2), width: s, height: s }).toBuffer();
  },
  'pad onto a white 4:3 canvas': (b, w, h) => S(b).extend({ left: Math.round(w * 0.2), right: Math.round(w * 0.2), top: 0, bottom: Math.round(h * 0.1), background: '#ffffff' }).toBuffer(),
  'grey 3% border': (b, w) => S(b).extend({ top: Math.round(w * 0.03), bottom: Math.round(w * 0.03), left: Math.round(w * 0.03), right: Math.round(w * 0.03), background: '#bbbbbb' }).toBuffer(),
  'flip left-right': (b) => S(b).flop().toBuffer(),
  'flip upside-down': (b) => S(b).flip().toBuffer(),
  'rotate 3°': (b) => S(b).rotate(3, { background: '#ffffff' }).toBuffer(),
  'brightness +8%': (b) => S(b).modulate({ brightness: 1.08 }).toBuffer(),
  'brightness −10%': (b) => S(b).modulate({ brightness: 0.9 }).toBuffer(),
  'hue +20°': (b) => S(b).modulate({ hue: 20 }).toBuffer(),
  'saturation ×1.3': (b) => S(b).modulate({ saturation: 1.3 }).toBuffer(),
  'warm tint': (b) => S(b).tint({ r: 255, g: 236, b: 210 }).toBuffer(),
  grayscale: (b) => S(b).grayscale().toBuffer(),
  'gamma 1.4': (b) => S(b).gamma(1.4).toBuffer(),
  'blur σ1.5': (b) => S(b).blur(1.5).toBuffer(),
  'a text watermark': (b, w, h) =>
    S(b)
      .composite([{ input: Buffer.from(`<svg width="${w}" height="${h}"><text x="5%" y="55%" font-size="${Math.round(h / 8)}" fill="rgba(0,0,0,0.35)" font-family="sans-serif">HOME · DESIGN</text></svg>`) }])
      .toBuffer(),
};

const rows: Record<string, { n: number; A: number; AB: number; dhash_median: number; missed_examples: string[] }> = {};
const t0 = Date.now();
for (const [name, f] of Object.entries(MUT)) {
  let A = 0;
  let AB = 0;
  const ds: number[] = [];
  const missed: string[] = [];
  for (const p of originals) {
    const buf = readFileSync(join(SITE, p.file));
    const meta = await sharp(buf, { failOn: 'none' }).rotate().toBuffer({ resolveWithObject: true });
    let out: Buffer;
    try {
      out = await f(buf, meta.info.width, meta.info.height);
    } catch {
      continue;
    }
    const fp = await fingerprint(out);
    if (!fp) continue;
    let a = false;
    let b = false;
    let own = 999;
    for (const q of set.pixels) {
      if (q.product !== p.product) continue;
      const d = hamming(fp.dhash, q.dhash);
      own = Math.min(own, d);
      if (d <= PIXEL_MAX_HAMMING) a = true;
      else if (d <= NEAR_MAX_HAMMING && mad32(fp.grey, q.grey) <= NEAR_MAX_MAD32) b = true;
    }
    ds.push(own);
    if (a) A++;
    if (a || b) AB++;
    else if (missed.length < 3) missed.push(`${p.product} (dHash ${own})`);
  }
  ds.sort((x, y) => x - y);
  rows[name] = { n: ds.length, A, AB, dhash_median: ds[Math.floor(ds.length / 2)] ?? -1, missed_examples: missed };
  console.error(`${name}: ${AB}/${ds.length} (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
}
dh.save();
writeFileSync(OUT!, JSON.stringify({ originals: originals.length, public_set: set.pixels.length, rule: `A dHash ≤ ${PIXEL_MAX_HAMMING}; B dHash ≤ ${NEAR_MAX_HAMMING} and MAD32 ≤ ${NEAR_MAX_MAD32}`, rows }, null, 1));
console.log(`QA mut-pixels (${originals.length} originals, every third of the cache; caught = A or B against the same product):`);
for (const [k, r] of Object.entries(rows)) console.log(`  ${k.padEnd(28)} ${String(r.AB).padStart(3)}/${r.n} (A alone ${r.A}; median dHash to its own ${r.dhash_median})`);
