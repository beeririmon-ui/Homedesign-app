/**
 * qa-agent, S17 (2026-11-12): the pixel rule of check:rights (dHash ≤ 24, or ≤ 48 with a 32×32 grey MAD ≤ 3) against
 * (1) everything that is NOT a supplier picture: every raster under assets/renders (our renders, layers, sheets, the IMG1
 *     pilot, render-agent's work files as they were at the time of the run) and every raster of the flag build's dist
 *     outside the supplier folders, plus synthetic flat images (white, transparent, a dot, a grey ramp);
 * (2) what IS one: the flag build's 321 story copies (every width).
 * The supplier set and the fingerprint are the copy's own (tools/lib/rights-content.ts at a988b099, `supplierSet`,
 * `fingerprint`), so the numbers are the gate's numbers. Fingerprints are cached by sha256 in my own file, not the copy's.
 *
 *   tsx fp-scan.mts <copy site dir> <out.json> <root>...
 */
import { readFileSync, readdirSync, statSync, writeFileSync, existsSync } from 'node:fs';
import { join, relative, extname, resolve } from 'node:path';
import { createRequire } from 'node:module';
import {
  DhashCache,
  LEDGER_SHOP,
  LEDGER_STORY,
  NEAR_MAX_HAMMING,
  NEAR_MAX_MAD32,
  PIXEL_MAX_HAMMING,
  hamming,
  mad32,
  readLedger,
  sha256,
  supplierSet,
  type SupplierPicture,
} from '../build-s17/site/tools/lib/rights-content';

const [SITE_ARG, OUT, ...ROOTS] = process.argv.slice(2);
const SITE = resolve(SITE_ARG!);
const sharp = createRequire(join(SITE, 'package.json'))('sharp') as typeof import('sharp');
sharp.concurrency(1);
const GEN = join(SITE, '.generated');
const RASTER = /\.(?:png|jpe?g|webp|avif|gif|tiff?)$/i;
const walk = (d: string): string[] =>
  readdirSync(d).flatMap((n) => {
    const p = join(d, n);
    let s;
    try {
      s = statSync(p);
    } catch {
      return [];
    }
    return s.isDirectory() ? walk(p) : RASTER.test(n) ? [p] : [];
  });

const dh = new DhashCache(join(process.env.QA_CACHE ?? '/tmp', 'qa17-fp-dhash.json'));
const ledgers = [readLedger(join(GEN, LEDGER_SHOP)), readLedger(join(GEN, LEDGER_STORY))].filter((l) => l !== null);
const set = await supplierSet({ site: SITE, ledgers, cacheDir: join(SITE, '.cache/supplier-images'), hosts: [], dhashes: dh });
const pixels = set.pixels;
// the story's copies are measured against the set a PUBLIC build has: no story ledger (the cache's originals and the shop's)
const setNoStory = await supplierSet({ site: SITE, ledgers: ledgers.filter((l) => l.source !== 'story'), cacheDir: join(SITE, '.cache/supplier-images'), hosts: [], dhashes: dh });
const pop = (hex: string) => hamming(hex, '0'.repeat(hex.length));

type Row = { file: string; d: number; pic: string; mad_at_d: number | null; best_mad: number | null; best_mad_d: number | null; best_mad_pic?: string; rule: 'A' | 'B' | null };
function compare(fp: { dhash: string; grey: Buffer }, file: string, against: SupplierPicture[] = pixels): Row {
  let best: { d: number; p: SupplierPicture } | null = null;
  let bm: { m: number; d: number; p: SupplierPicture } | null = null;
  let rule: Row['rule'] = null;
  for (const p of against) {
    const d = hamming(fp.dhash, p.dhash);
    if (!best || d < best.d) best = { d, p };
    if (d <= NEAR_MAX_HAMMING) {
      const m = mad32(fp.grey, p.grey);
      if (!bm || m < bm.m) bm = { m, d, p };
      if (d <= PIXEL_MAX_HAMMING) rule = 'A';
      else if (m <= NEAR_MAX_MAD32 && rule !== 'A') rule = 'B';
    }
  }
  return {
    file,
    d: best!.d,
    pic: best!.p.picture,
    mad_at_d: best!.d <= NEAR_MAX_HAMMING ? Number(mad32(fp.grey, best!.p.grey).toFixed(2)) : null,
    best_mad: bm ? Number(bm.m.toFixed(2)) : null,
    best_mad_d: bm?.d ?? null,
    ...(bm ? { best_mad_pic: bm.p.picture } : {}),
    rule,
  };
}

const t0 = Date.now();
const out: Record<string, unknown> = {
  supplier_set: { ...set.stats, pixel_pictures: pixels.length, pixel_pictures_without_story_ledger: setNoStory.pixels.length },
  supplier_dhash_popcount: (() => {
    const ps = pixels.map((p) => pop(p.dhash)).sort((a, b) => a - b);
    return { min: ps[0], p5: ps[Math.floor(ps.length * 0.05)], median: ps[Math.floor(ps.length / 2)], at_or_below_24: ps.filter((x) => x <= 24).length };
  })(),
};

// (0) synthetic flat images
const synth: Record<string, Buffer> = {
  'white 1000×1000 (png)': await sharp({ create: { width: 1000, height: 1000, channels: 3, background: '#ffffff' } }).png().toBuffer(),
  'transparent 1000×1000 (png)': await sharp({ create: { width: 1000, height: 1000, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } }).png().toBuffer(),
  'near-white #fafafa (jpeg)': await sharp({ create: { width: 800, height: 800, channels: 3, background: '#fafafa' } }).jpeg().toBuffer(),
  'a 40 px dark dot on white': await sharp({ create: { width: 800, height: 800, channels: 3, background: '#ffffff' } })
    .composite([{ input: await sharp({ create: { width: 40, height: 40, channels: 3, background: '#333333' } }).png().toBuffer(), left: 380, top: 380 }])
    .png()
    .toBuffer(),
  'a light grey ramp': await sharp(Buffer.from(Array.from({ length: 256 * 256 }, (_, i) => 200 + Math.floor((i % 256) / 5))), { raw: { width: 256, height: 256, channels: 1 } })
    .png()
    .toBuffer(),
};
const synthRows: Row[] = [];
for (const [k, b] of Object.entries(synth)) {
  const f = await dh.of(b);
  if (f) synthRows.push({ ...compare(f, k), file: k });
}
out.synthetic = synthRows;

// (1) not supplier pictures, (2) the story's copies
const notSupplier: Row[] = [];
const story: Row[] = [];
const unreadable: string[] = [];
let n = 0;
for (const root of ROOTS) {
  const isDist = root.endsWith('/web/dist');
  for (const f of walk(root)) {
    const rel = isDist ? `dist/${relative(root, f)}` : relative(resolve(root, '..'), f);
    const inSupplierFolder = isDist && /^dist\/media\/(?:products|story\/products)\//.test(rel);
    const isStory = isDist && /^dist\/media\/story\/products\//.test(rel);
    if (inSupplierFolder && !isStory) continue; // the shop's own supplier copies: by bytes, not this question
    let buf: Buffer;
    try {
      buf = readFileSync(f);
    } catch {
      unreadable.push(rel);
      continue;
    }
    const fp = await dh.of(buf, sha256(buf));
    if (!fp) {
      unreadable.push(rel);
      continue;
    }
    if (isStory) story.push(compare(fp, rel, setNoStory.pixels));
    else notSupplier.push(compare(fp, rel));
    if (++n % 200 === 0) {
      dh.save();
      console.error(`… ${n} files, ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
  }
}
dh.save();
const hist = (rows: Row[], key: 'd' | 'best_mad', edges: number[]) =>
  Object.fromEntries(edges.map((e, i) => [`${i ? edges[i - 1]! + 1 : 0}–${e}`, rows.filter((r) => r[key] !== null && r[key]! <= e && (i === 0 || r[key]! > edges[i - 1]!)).length]));
const ns = notSupplier;
out.not_supplier = {
  files: ns.length,
  unreadable: unreadable.length,
  unreadable_files: unreadable.slice(0, 20),
  rule_A_hits: ns.filter((r) => r.rule === 'A').map((r) => r),
  rule_B_hits: ns.filter((r) => r.rule === 'B').map((r) => r),
  nearest_by_dhash: [...ns].sort((a, b) => a.d - b.d).slice(0, 15),
  nearest_by_mad_within_48: ns.filter((r) => r.best_mad !== null).sort((a, b) => a.best_mad! - b.best_mad!).slice(0, 15),
  dhash_histogram: hist(ns, 'd', [24, 32, 40, 48, 64, 96, 256]),
  within_48: ns.filter((r) => r.best_mad !== null).length,
  by_root: Object.fromEntries(
    [...new Set(ns.map((r) => r.file.split('/').slice(0, 3).join('/')))].map((k) => [k, ns.filter((r) => r.file.startsWith(k)).length]),
  ),
};
out.story_copies = {
  files: story.length,
  caught_A: story.filter((r) => r.rule === 'A').length,
  caught_B_only: story.filter((r) => r.rule === 'B').length,
  missed: story.filter((r) => !r.rule).map((r) => r),
  worst_by_dhash: [...story].sort((a, b) => b.d - a.d).slice(0, 12),
  worst_mad_of_B: story.filter((r) => r.rule === 'B').sort((a, b) => b.best_mad! - a.best_mad!).slice(0, 5),
};
out.seconds = Number(((Date.now() - t0) / 1000).toFixed(1));
writeFileSync(OUT!, JSON.stringify(out, null, 1));
const o = out as { not_supplier: { files: number; rule_A_hits: Row[]; rule_B_hits: Row[]; within_48: number }; story_copies: { files: number; caught_A: number; caught_B_only: number; missed: Row[] } };
console.log(
  `QA fp-scan: supplier set ${pixels.length} pictures; not supplier: ${o.not_supplier.files} files, rule A ${o.not_supplier.rule_A_hits.length}, rule B ${o.not_supplier.rule_B_hits.length}, within dHash 48: ${o.not_supplier.within_48}; ` +
    `story copies ${o.story_copies.files}: A ${o.story_copies.caught_A}, B only ${o.story_copies.caught_B_only}, missed ${o.story_copies.missed.length}; synthetic: ${synthRows.map((r) => `${r.file} d${r.d} mad${r.best_mad} ${r.rule ?? '-'}`).join(' | ')} (${out.seconds}s)`,
);
if (!existsSync(OUT!)) process.exit(1);
