/**
 * frontend-dev, S19 (2026-11-12), ת50 and ת51: QA's fp-scan (qa/reports/2026-11-12-site-track-qa-s17/tools/fp-scan.mts)
 * on the live tree, with the gate's OWN rule (site/tools/lib/rights-content.ts: `nearestPicture`, `pixelRule`), next to
 * the S17 rule as QA re-implemented it (plain against plain, A dHash ≤ 24 or B dHash ≤ 48 with grey MAD ≤ 3, no ink guard).
 *
 * The same groups as QA's two tools:
 *   story copies       the flag build's dist/media/story/products (every width): TRUE copies, against the set a PUBLIC
 *                      build has (no story ledger); caught by any picture (fp-scan) and by a picture of their own product
 *                      (fp-rule-alt)
 *   references         the downloaded supplier photos kept under assets/renders/house-nordic-*\/refs: TRUE copies
 *   ours               every other raster under assets/renders (renders, layers, sheets, the IMG1 pilot, work files as
 *                      they are now), and the flag dist outside the supplier folders: NOT supplier pictures
 *   synthetic          white, transparent, near-white, a dot, a grey ramp
 * Fingerprints are cached by sha256 in a file of my own (QA_CACHE), not the build's.
 *
 *   tsx fp-scan.mts <site dir> <out.json> <root>...
 */
import { readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
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
  nearestPicture,
  prepare,
  readLedger,
  sha256,
  supplierSet,
  type Fingerprint,
  type SupplierPicture,
} from '../../../../../site/tools/lib/rights-content';

const [SITE_ARG, OUT, ...ROOTS] = process.argv.slice(2);
const SITE = resolve(SITE_ARG!);
const sharp = createRequire(join(SITE, 'package.json'))('sharp') as typeof import('sharp');
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

const dh = new DhashCache(join(process.env.QA_CACHE ?? '/tmp', 's19-fp-dhash.json'));
const ledgers = [readLedger(join(GEN, LEDGER_SHOP)), readLedger(join(GEN, LEDGER_STORY))].filter((l) => l !== null);
const set = await supplierSet({ site: SITE, ledgers, cacheDir: join(SITE, '.cache/supplier-images'), hosts: [], dhashes: dh });
const setNoStory = await supplierSet({
  site: SITE,
  ledgers: ledgers.filter((l) => l.source !== 'story'),
  cacheDir: join(SITE, '.cache/supplier-images'),
  hosts: [],
  dhashes: dh,
});
dh.save();

/** the S17 rule as QA re-implemented it: plain against plain, no ink guard */
function oldRule(fp: Fingerprint, against: SupplierPicture[], only?: (p: SupplierPicture) => boolean): { rule: 'A' | 'B' | null; d: number; pic: string } {
  let rule: 'A' | 'B' | null = null;
  let bestD = 999;
  let pic = '';
  for (const p of against) {
    if (p.variant !== 'plain' || (only && !only(p))) continue;
    const d = hamming(fp.dhash, p.dhash);
    if (d < bestD) [bestD, pic] = [d, p.picture];
    if (d <= PIXEL_MAX_HAMMING) rule = 'A';
    else if (d <= NEAR_MAX_HAMMING && rule !== 'A' && mad32(fp.grey, p.grey) <= NEAR_MAX_MAD32) rule = 'B';
  }
  return { rule, d: bestD, pic };
}
type Row = { file: string; old: 'A' | 'B' | null; now: 'A' | 'B' | null; d: number; m: number | null; pic: string; forms: string; ink: number };
async function judge(buf: Buffer, file: string, against: SupplierPicture[], only?: (p: SupplierPicture) => boolean): Promise<Row | null> {
  const v = await dh.variants(buf, sha256(buf), ['plain', 'trimmed']);
  if (!v.plain) return null;
  const mine = { plain: prepare(v.plain), trimmed: v.trimmed ? prepare(v.trimmed) : null };
  const { best } = nearestPicture(mine, against, PIXEL_MAX_HAMMING, only);
  const o = oldRule(v.plain, against, only);
  return {
    file,
    old: o.rule,
    now: best?.rule ?? null,
    d: best?.d ?? 999,
    m: best?.m === null || best?.m === undefined ? null : Number(best.m.toFixed(2)),
    pic: best?.p.picture ?? '',
    forms: best ? `${best.mine} vs ${best.p.variant}` : '',
    ink: Number(mine.plain.ink.toFixed(1)),
  };
}

const t0 = Date.now();
const synth: Record<string, Buffer> = {
  'white 1000×1000 (png)': await sharp({ create: { width: 1000, height: 1000, channels: 3, background: '#ffffff' } }).png().toBuffer(),
  'transparent 1000×1000 (png)': await sharp({ create: { width: 1000, height: 1000, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } })
    .png()
    .toBuffer(),
  'near-white #fafafa (jpeg)': await sharp({ create: { width: 800, height: 800, channels: 3, background: '#fafafa' } }).jpeg().toBuffer(),
  'a 40 px dark dot on white': await sharp({ create: { width: 800, height: 800, channels: 3, background: '#ffffff' } })
    .composite([{ input: await sharp({ create: { width: 40, height: 40, channels: 3, background: '#333333' } }).png().toBuffer(), left: 380, top: 380 }])
    .png()
    .toBuffer(),
  'a light grey ramp': await sharp(Buffer.from(Array.from({ length: 256 * 256 }, (_, i) => 200 + Math.floor((i % 256) / 5))), {
    raw: { width: 256, height: 256, channels: 1 },
  })
    .png()
    .toBuffer(),
};
const synthetic: Row[] = [];
for (const [k, b] of Object.entries(synth)) {
  const r = await judge(b, k, set.pixels);
  if (r) synthetic.push(r);
}

const ours: Row[] = [];
const refs: Row[] = [];
const story: Row[] = [];
const storyOwn: Row[] = [];
const unreadable: string[] = [];
let n = 0;
for (const root of ROOTS) {
  const isDist = root.endsWith('/web/dist');
  for (const f of walk(root)) {
    const rel = isDist ? `dist/${relative(root, f)}` : relative(resolve(root, '..'), f);
    const isStory = isDist && /^dist\/media\/story\/products\//.test(rel);
    if (isDist && /^dist\/media\/products\//.test(rel)) continue; // the shop's own supplier copies: by bytes
    const isRef = /^renders\/house-nordic-[^/]+\/refs\//.test(rel);
    const buf = readFileSync(f);
    if (isStory) {
      const own = /story\/products\/([^/]+)\//.exec(rel)?.[1];
      const a = await judge(buf, rel, setNoStory.pixels);
      const b = await judge(buf, rel, setNoStory.pixels, (p) => p.product === own || p.picture.includes(own!));
      if (a) story.push(a);
      if (b) storyOwn.push(b);
      if (!a) unreadable.push(rel);
    } else {
      const r = await judge(buf, rel, set.pixels);
      if (!r) unreadable.push(rel);
      else (isRef ? refs : ours).push(r);
    }
    if (++n % 200 === 0) {
      dh.save();
      console.error(`… ${n} files, ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
  }
}
dh.save();
const count = (rows: Row[], k: 'old' | 'now') => ({ A: rows.filter((r) => r[k] === 'A').length, B: rows.filter((r) => r[k] === 'B').length, any: rows.filter((r) => r[k]).length });
const top = (k: string) => k.split('/').slice(0, 3).join('/');
const byRoot = (rows: Row[]) =>
  Object.fromEntries(
    [...new Set(rows.map((r) => top(r.file)))].sort().map((k) => {
      const g = rows.filter((r) => top(r.file) === k);
      return [k, { files: g.length, old: count(g, 'old').any, now: count(g, 'now').any }];
    }),
  );
const out = {
  measured_at: new Date().toISOString(),
  rule_now: `A dHash ≤ ${PIXEL_MAX_HAMMING}, or B dHash ≤ ${NEAR_MAX_HAMMING} with grey MAD ≤ ${NEAR_MAX_MAD32} when both have ink ≥ 4; plain and trimmed against plain, mirrored, trimmed and trimmed-mirrored`,
  rule_old: 'S17: plain against plain, A or B without the ink guard (QA fp-scan.mts compare())',
  supplier_set: { full: set.stats, public: setNoStory.stats },
  synthetic,
  story_copies: { files: story.length, any_picture: { old: count(story, 'old'), now: count(story, 'now') }, own_product: { old: count(storyOwn, 'old'), now: count(storyOwn, 'now') }, missed_now: storyOwn.filter((r) => !r.now) },
  references: { files: refs.length, old: count(refs, 'old'), now: count(refs, 'now'), matched_now: refs.filter((r) => r.now), lost: refs.filter((r) => r.old && !r.now), gained: refs.filter((r) => !r.old && r.now) },
  ours: {
    files: ours.length,
    unreadable,
    old: count(ours, 'old'),
    now: count(ours, 'now'),
    false_matches_now: ours.filter((r) => r.now),
    false_matches_old: ours.filter((r) => r.old).map((r) => `${r.file} (${r.old}, ink ${r.ink})`),
    phase2_warm_modern: (() => {
      const g = ours.filter((r) => r.file.includes('warm-modern/phase2-2026-11-10'));
      return { files: g.length, old: count(g, 'old'), now: count(g, 'now') };
    })(),
    img1_pilot: (() => {
      const g = ours.filter((r) => r.file.includes('img1-pilot-2026-11-12'));
      return { files: g.length, old: count(g, 'old'), now: count(g, 'now') };
    })(),
    flag_dist_outside_supplier_folders: (() => {
      const g = ours.filter((r) => r.file.startsWith('dist/'));
      return { files: g.length, old: count(g, 'old'), now: count(g, 'now') };
    })(),
    nearest_now: [...ours].sort((a, b) => a.d - b.d).slice(0, 15),
    by_root: byRoot(ours),
  },
  seconds: Number(((Date.now() - t0) / 1000).toFixed(1)),
};
writeFileSync(OUT!, JSON.stringify(out, null, 1));
console.log(
  `S19 fp-scan: supplier set ${set.stats.pictures} pictures (${set.stats.fingerprints} fingerprints); ` +
    `story copies ${story.length}: any picture old ${out.story_copies.any_picture.old.any} → now ${out.story_copies.any_picture.now.any}, own product old ${out.story_copies.own_product.old.any} → now ${out.story_copies.own_product.now.any}; ` +
    `references ${refs.length}: old ${out.references.old.any} → now ${out.references.now.any}; ` +
    `ours ${ours.length}: false matches old ${out.ours.old.any} (A ${out.ours.old.A}, B ${out.ours.old.B}) → now ${out.ours.now.any} (A ${out.ours.now.A}, B ${out.ours.now.B}); ` +
    `phase-2 ${JSON.stringify(out.ours.phase2_warm_modern)}; IMG1 ${JSON.stringify(out.ours.img1_pilot)}; ` +
    `synthetic: ${synthetic.map((r) => `${r.file} old ${r.old ?? '-'} now ${r.now ?? '-'}`).join(' | ')} (${out.seconds}s)`,
);
