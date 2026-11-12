/**
 * qa-agent, S19 (2026-11-12): my S17 fp-scan (qa/reports/2026-11-12-site-track-qa-s17/tools/fp-scan.mts), run on my
 * isolated copy of f33cfe42. Every raster is judged three ways:
 *   gate    the gate's own rule as shipped (tools/lib/rights-content.ts `nearestPicture`: A; B with the ink guard; the
 *           mirrored and trimmed forms), so the numbers are the gate's numbers;
 *   brief   my own re-implementation of ת50 as briefed, plain against plain only: A dHash ≤ 24, or B dHash ≤ 48 and
 *           32×32 grey MAD ≤ 3 and the mean ink (255 − grey) ≥ 4 in both (an independent check of the gate's code);
 *   s17     the S17 rule (no ink guard), for the before/after.
 * And, for frontend-dev's question 1 (rule A against near-blank pictures), plain against plain: the nearest picture
 * with both inks and dHash popcounts, and the nearest under each candidate guard:
 *   P1      A skips when one ink < 2 and the other ≥ 8 (frontend-dev's proposal)
 *   P2      A skips when one ink < 2 and the other ≥ 2 (a near-blank picture against any inked one)
 *   P3      A needs the differing bits to be at most half of the set bits of the two hashes (d ≤ (pop a + pop b) / 2)
 * Groups: story copies (the flag dist's media/story/products, against the set a PUBLIC build has), references (the
 * downloaded supplier photos kept under assets/renders/house-nordic-*\/refs: true copies), ours (every other raster under
 * the roots, and the flag dist outside the supplier folders), synthetic (white, transparent, near-white, a dot, a ramp).
 * Fingerprints are cached by sha256 in my own file (QA_CACHE), never the copy's.
 *
 *   tsx fp-scan.mts <copy site dir> <out.json> <root>...
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
  NEAR_MIN_INK,
  PIXEL_MAX_HAMMING,
  hammingBytes,
  mad32,
  nearestPicture,
  prepare,
  readLedger,
  sha256,
  supplierSet,
  type Prepared,
  type SupplierPicture,
} from '../build-s19/site/tools/lib/rights-content';

const [SITE_ARG, OUT, ...ROOTS] = process.argv.slice(2);
const SITE = resolve(SITE_ARG!);
const sharp = createRequire(join(SITE, 'package.json'))('sharp') as typeof import('sharp');
sharp.concurrency(2);
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

const dh = new DhashCache(join(process.env.QA_CACHE ?? '/tmp', 'qa19-fp-dhash.json'));
const ledgers = [readLedger(join(GEN, LEDGER_SHOP)), readLedger(join(GEN, LEDGER_STORY))].filter((l) => l !== null);
const set = await supplierSet({ site: SITE, ledgers, cacheDir: join(SITE, '.cache/supplier-images'), hosts: [], dhashes: dh });
const setNoStory = await supplierSet({ site: SITE, ledgers: ledgers.filter((l) => l.source !== 'story'), cacheDir: join(SITE, '.cache/supplier-images'), hosts: [], dhashes: dh });
dh.save();
const POP = (b: Uint8Array) => hammingBytes(b, new Uint8Array(b.length));
const r1 = (x: number) => Number(x.toFixed(1));

type Pair = { d: number; pic: string; ink_mine: number; ink_pic: number; pop_mine: number; pop_pic: number; mad: number };
type Row = {
  file: string;
  ink: number;
  pop: number;
  gate: 'A' | 'B' | null;
  gate_d: number;
  gate_m: number | null;
  gate_forms: string;
  gate_pic: string;
  brief: 'A' | 'B' | null;
  s17: 'A' | 'B' | null;
  same_product?: boolean;
  nearest: Pair;
  nearest_P1: Pair;
  nearest_P2: Pair;
  nearest_P3: Pair;
};
const pairOf = (f: Prepared, p: SupplierPicture, d: number): Pair => ({
  d,
  pic: p.picture,
  ink_mine: r1(f.ink),
  ink_pic: r1(p.ink),
  pop_mine: POP(f.bits),
  pop_pic: POP(p.bits),
  mad: r1(mad32(f.grey, p.grey)),
});
function judge(mine: { plain: Prepared; trimmed: Prepared | null }, file: string, against: SupplierPicture[], product?: string): Row {
  const { best } = nearestPicture(mine, against, PIXEL_MAX_HAMMING);
  const f = mine.plain;
  let brief: Row['brief'] = null;
  let s17: Row['s17'] = null;
  let n: Pair | null = null;
  let n1: Pair | null = null;
  let n2: Pair | null = null;
  let n3: Pair | null = null;
  const pf = POP(f.bits);
  for (const p of against) {
    if (p.variant !== 'plain') continue;
    const d = hammingBytes(f.bits, p.bits);
    if (d <= PIXEL_MAX_HAMMING) brief = s17 = 'A';
    else if (d <= NEAR_MAX_HAMMING) {
      const m = mad32(f.grey, p.grey);
      if (m <= NEAR_MAX_MAD32) {
        if (s17 !== 'A') s17 = 'B';
        if (brief !== 'A' && f.ink >= NEAR_MIN_INK && p.ink >= NEAR_MIN_INK) brief = 'B';
      }
    }
    const lo = Math.min(f.ink, p.ink);
    const hi = Math.max(f.ink, p.ink);
    if (!n || d < n.d) n = pairOf(f, p, d);
    if (!(lo < 2 && hi >= 8) && (!n1 || d < n1.d)) n1 = pairOf(f, p, d);
    if (!(lo < 2 && hi >= 2) && (!n2 || d < n2.d)) n2 = pairOf(f, p, d);
    if (d <= (pf + POP(p.bits)) / 2 && (!n3 || d < n3.d)) n3 = pairOf(f, p, d);
  }
  const none: Pair = { d: 999, pic: '', ink_mine: 0, ink_pic: 0, pop_mine: 0, pop_pic: 0, mad: 0 };
  return {
    file,
    ink: r1(f.ink),
    pop: pf,
    gate: best?.rule ?? null,
    gate_d: best?.d ?? 999,
    gate_m: best?.m == null ? null : r1(best.m),
    gate_forms: best ? `${best.mine} vs ${best.p.variant}` : '',
    gate_pic: best?.p.picture ?? '',
    brief,
    s17,
    ...(product ? { same_product: !!best?.rule && best.p.product === product } : {}),
    nearest: n ?? none,
    nearest_P1: n1 ?? none,
    nearest_P2: n2 ?? none,
    nearest_P3: n3 ?? none,
  };
}
async function rowOf(buf: Buffer, file: string, against: SupplierPicture[], product?: string): Promise<Row | null> {
  const v = await dh.variants(buf, sha256(buf), ['plain', 'trimmed']);
  if (!v.plain) return null;
  return judge({ plain: prepare(v.plain), trimmed: v.trimmed ? prepare(v.trimmed) : null }, file, against, product);
}

const t0 = Date.now();
const pics = set.pixels.filter((p) => p.variant === 'plain');
const out: Record<string, unknown> = {
  supplier_set: { ...set.stats, without_story_ledger: setNoStory.stats },
  supplier_plain_pictures: {
    n: pics.length,
    ink_below_2: pics.filter((p) => p.ink < 2).map((p) => `${p.picture} ink ${r1(p.ink)}`),
    ink_below_4: pics.filter((p) => p.ink < 4).length,
    ink_below_8: pics.filter((p) => p.ink < 8).length,
    popcount_min: Math.min(...pics.map((p) => POP(p.bits))),
    popcount_at_or_below_24: pics.filter((p) => POP(p.bits) <= 24).map((p) => `${p.picture} pop ${POP(p.bits)} ink ${r1(p.ink)}`),
    popcount_at_or_below_32: pics.filter((p) => POP(p.bits) <= 32).map((p) => `${p.picture} pop ${POP(p.bits)} ink ${r1(p.ink)}`),
  },
};

// (0) synthetic
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
  'a soft grey blob on transparent (a shadow layer)': await sharp({ create: { width: 1000, height: 800, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } })
    .composite([{ input: Buffer.from('<svg width="1000" height="800"><defs><radialGradient id="g"><stop offset="0" stop-color="#000" stop-opacity="0.35"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient></defs><ellipse cx="500" cy="600" rx="260" ry="60" fill="url(#g)"/></svg>') }])
    .png()
    .toBuffer(),
};
const synthRows: Row[] = [];
for (const [k, b] of Object.entries(synth)) {
  const r = await rowOf(b, k, set.pixels);
  if (r) synthRows.push(r);
}
out.synthetic = synthRows;

const ours: Row[] = [];
const story: Row[] = [];
const refs: Row[] = [];
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
    const isRef = !isDist && /\/house-nordic-[^/]+\/refs\//.test(`/${rel}`);
    const product = isStory ? rel.split('/')[4] : undefined;
    const r = await rowOf(buf, rel, isStory ? setNoStory.pixels : set.pixels, product);
    if (!r) {
      unreadable.push(rel);
      continue;
    }
    (isStory ? story : isRef ? refs : ours).push(r);
    if (++n % 250 === 0) {
      dh.save();
      console.error(`… ${n} files, ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
  }
}
dh.save();
const slim = (r: Row) => ({ file: r.file, gate: r.gate, d: r.gate_d, m: r.gate_m, forms: r.gate_forms, pic: r.gate_pic, ink: r.ink, brief: r.brief, s17: r.s17 });
const byTop = (rows: Row[]) =>
  Object.fromEntries([...new Set(rows.map((r) => r.file.split('/').slice(0, 3).join('/')))].sort().map((k) => [k, rows.filter((r) => r.file.startsWith(k + '/') || r.file === k).length]));
const near = (rows: Row[], key: 'nearest' | 'nearest_P1' | 'nearest_P2' | 'nearest_P3', k = 8) =>
  [...rows].sort((a, b) => a[key].d - b[key].d).slice(0, k).map((r) => ({ file: r.file, ...r[key] }));
out.ours = {
  files: ours.length,
  unreadable: unreadable.length,
  unreadable_files: unreadable.slice(0, 20),
  by_top_dir: byTop(ours),
  gate_hits: ours.filter((r) => r.gate).map(slim),
  brief_rule_hits: ours.filter((r) => r.brief).map(slim),
  s17_rule_hits: { A: ours.filter((r) => r.s17 === 'A').length, B: ours.filter((r) => r.s17 === 'B').length, examples: ours.filter((r) => r.s17).slice(0, 5).map(slim) },
  gate_vs_brief_disagree: ours.filter((r) => !!r.gate !== !!r.brief).map(slim),
  nearest_gate: [...ours].sort((a, b) => a.gate_d - b.gate_d).slice(0, 10).map(slim),
  nearest_by_grey_within_48: [...ours].filter((r) => r.gate_m !== null && r.gate_d <= NEAR_MAX_HAMMING).sort((a, b) => a.gate_m! - b.gate_m!).slice(0, 10).map(slim),
  q1_rule_A_margin: { now: near(ours, 'nearest'), P1: near(ours, 'nearest_P1'), P2: near(ours, 'nearest_P2'), P3: near(ours, 'nearest_P3') },
  near_blank_files_ink_below_2: ours.filter((r) => r.ink < 2).length,
  within_32_now: ours.filter((r) => r.nearest.d <= 32).length,
};
const caught = (rows: Row[]) => ({
  files: rows.length,
  gate: rows.filter((r) => r.gate).length,
  gate_A: rows.filter((r) => r.gate === 'A').length,
  gate_B: rows.filter((r) => r.gate === 'B').length,
  gate_by_forms: rows.reduce<Record<string, number>>((o, r) => (r.gate ? ((o[`${r.gate} ${r.gate_forms}`] = (o[`${r.gate} ${r.gate_forms}`] ?? 0) + 1), o) : o), {}),
  brief: rows.filter((r) => r.brief).length,
  s17: rows.filter((r) => r.s17).length,
  missed_by_gate: rows.filter((r) => !r.gate).map(slim),
  // question 1: a true copy caught ONLY by rule A on plain/plain whose pair the candidate guard would skip
  A_pairs_with_min_ink_below_2: rows.filter((r) => r.nearest.d <= PIXEL_MAX_HAMMING && Math.min(r.nearest.ink_mine, r.nearest.ink_pic) < 2).map((r) => ({ file: r.file, ...r.nearest })),
  lost_under_P1: rows.filter((r) => r.nearest.d <= PIXEL_MAX_HAMMING && r.nearest_P1.d > PIXEL_MAX_HAMMING && r.gate_forms === 'plain vs plain' && r.gate === 'A').map((r) => r.file),
  lost_under_P3: rows.filter((r) => r.nearest.d <= PIXEL_MAX_HAMMING && r.nearest_P3.d > PIXEL_MAX_HAMMING && r.gate_forms === 'plain vs plain' && r.gate === 'A').map((r) => r.file),
  ink_range: [Math.min(...rows.map((r) => r.ink)), Math.max(...rows.map((r) => r.ink))],
});
out.story_copies = { ...caught(story), of_their_own_product: story.filter((r) => r.same_product).length, worst: [...story].sort((a, b) => b.gate_d - a.gate_d).slice(0, 8).map(slim) };
out.references = { ...caught(refs), rows: refs.map(slim) };
out.seconds = Number(((Date.now() - t0) / 1000).toFixed(1));
writeFileSync(OUT!, JSON.stringify(out, null, 1));
const o = out as { ours: { files: number; gate_hits: unknown[]; brief_rule_hits: unknown[]; gate_vs_brief_disagree: unknown[]; s17_rule_hits: { A: number; B: number } } };
const s = out.story_copies as ReturnType<typeof caught> & { of_their_own_product: number };
const rf = out.references as ReturnType<typeof caught>;
console.log(
  `QA S19 fp-scan: supplier set ${set.stats.pictures} pictures (${set.stats.fingerprints} fingerprints); ours ${o.ours.files} files: gate ${o.ours.gate_hits.length}, brief rule ${o.ours.brief_rule_hits.length}, S17 rule A ${o.ours.s17_rule_hits.A} B ${o.ours.s17_rule_hits.B}, gate≠brief ${o.ours.gate_vs_brief_disagree.length}; ` +
    `story ${s.files}: gate ${s.gate} (A ${s.gate_A}, B ${s.gate_B}; own product ${s.of_their_own_product}), brief ${s.brief}; references ${rf.files}: gate ${rf.gate}, brief ${rf.brief}, S17 ${rf.s17}; ` +
    `synthetic: ${synthRows.map((r) => `${r.file} ${r.gate ?? '-'} d${r.gate_d}`).join(' | ')} (${out.seconds}s)`,
);
