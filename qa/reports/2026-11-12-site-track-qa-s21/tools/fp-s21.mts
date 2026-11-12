/**
 * qa-agent, S21 (2026-11-12): ת66 on my isolated copy of 7b42ddc1. My S19 fp-scan's groups, each raster judged four
 * ways over every pair of forms (mine plain/trimmed × the supplier's plain/mirrored/trimmed…):
 *   gate  the S21 gate (`nearestPicture`), its verdict and its margin pair (`aEligible`);
 *   R20   my emulation of the S19/S20 gate (no flatness guard);
 *   P3q   my emulation of QA's S19 ruling (P3 on plain vs plain only);
 *   S21   my emulation of S21 (P3 on every pair, and two flat hashes need grey ≤ 8): must equal the gate on every file.
 * Groups: story copies (the flag dist's media/story/products against the set a PUBLIC build has: true copies), the
 * references (assets/renders/house-nordic-*\/refs: true copies), ours (every other raster under the roots, and the flag
 * dist outside the supplier folders), synthetic (flat canvases of many colours, with a little ink, gradients, a dot).
 * The margin: the nearest pair rule A may judge (S21), and under R20 / P3q for the before.
 *
 *   tsx fp-s21.mts <copy site dir> <out.json> <root>...
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
} from '../build-s21/site/tools/lib/rights-content';

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
const dh = new DhashCache(join(process.env.QA_CACHE ?? '/tmp', 'qa21-fp-dhash.json'));
const ledgers = [readLedger(join(GEN, LEDGER_SHOP)), readLedger(join(GEN, LEDGER_STORY))].filter((l) => l !== null);
const set = await supplierSet({ site: SITE, ledgers, cacheDir: join(SITE, '.cache/supplier-images'), hosts: [], dhashes: dh });
const setNoStory = await supplierSet({ site: SITE, ledgers: ledgers.filter((l) => l.source !== 'story'), cacheDir: join(SITE, '.cache/supplier-images'), hosts: [], dhashes: dh });
const POP = (b: Uint8Array) => hammingBytes(b, new Uint8Array(b.length));

type Rule = 'R20' | 'P3q' | 'S21';
type V = { rule: 'A' | 'B' | null; d: number; via: string; pic: string; product: string };
/** my emulation: the verdict, and the nearest pair rule A may judge (the margin) */
function emu(mine: { plain: Prepared; trimmed: Prepared | null }, pics: SupplierPicture[], rule: Rule): { v: V; margin: V | null } {
  const forms: ['plain' | 'trimmed', Prepared][] = [['plain', mine.plain]];
  if (mine.trimmed) forms.push(['trimmed', mine.trimmed]);
  let hitB: V | null = null;
  let margin: V | null = null;
  for (const p of pics)
    for (const [k, f] of forms) {
      const d = hammingBytes(f.bits, p.bits);
      const pp = k === 'plain' && p.variant === 'plain';
      const inked = f.ink >= NEAR_MIN_INK && p.ink >= NEAR_MIN_INK;
      const pa = POP(f.bits);
      const pb = POP(p.bits);
      let elig = pp || inked;
      if (rule === 'P3q' && pp && 2 * d > pa + pb) elig = false;
      if (rule === 'S21' && 2 * d > pa + pb) elig = false;
      if (rule === 'S21' && pa < 8 && pb < 8 && mad32(f.grey, p.grey) > 8) elig = false;
      const via = `${k} vs ${p.variant} pop ${pa}/${pb} ink ${f.ink.toFixed(1)}/${p.ink.toFixed(1)}`;
      if (elig && d <= PIXEL_MAX_HAMMING) return { v: { rule: 'A', d, via, pic: p.picture, product: p.product }, margin: null };
      if (elig && (!margin || d < margin.d)) margin = { rule: null, d, via, pic: p.picture, product: p.product };
      if (!hitB && d <= NEAR_MAX_HAMMING && inked && mad32(f.grey, p.grey) <= NEAR_MAX_MAD32) hitB = { rule: 'B', d, via, pic: p.picture, product: p.product };
    }
  return { v: hitB ?? { rule: null, d: margin?.d ?? 999, via: '', pic: '', product: '' }, margin };
}
type Row = { file: string; ink: number; pop: number; gate: 'A' | 'B' | null; gate_d: number; gate_eligible: boolean; gate_pic: string; R20: V; P3q: V; S21: V; m20: V | null; m3: V | null; m21: V | null; same_product?: boolean };
async function rowOf(buf: Buffer, file: string, against: SupplierPicture[], product?: string): Promise<Row | null> {
  const v = await dh.variants(buf, sha256(buf), ['plain', 'trimmed']);
  if (!v.plain) return null;
  const mine = { plain: prepare(v.plain), trimmed: v.trimmed ? prepare(v.trimmed) : null };
  const { best } = nearestPicture(mine, against, PIXEL_MAX_HAMMING);
  const a = emu(mine, against, 'R20');
  const b = emu(mine, against, 'P3q');
  const c = emu(mine, against, 'S21');
  return {
    file,
    ink: Number(mine.plain.ink.toFixed(1)),
    pop: POP(mine.plain.bits),
    gate: best?.rule ?? null,
    gate_d: best?.d ?? 999,
    gate_eligible: !!best?.aEligible,
    gate_pic: best?.p.picture ?? '',
    R20: a.v,
    P3q: b.v,
    S21: c.v,
    m20: a.margin,
    m3: b.margin,
    m21: c.margin,
    ...(product ? { same_product: !!best?.rule && best.p.product === product } : {}),
  };
}

const t0 = Date.now();
const out: Record<string, unknown> = { supplier_set: set.stats, public_set: setNoStory.stats };
// ---------- synthetic: flat forms of many colours, a little ink, gradients
const flat = (bg: string | { r: number; g: number; b: number; alpha: number }, ch: 3 | 4 = 3, w = 900, h = 900) => sharp({ create: { width: w, height: h, channels: ch, background: bg } });
const synth: Record<string, Buffer> = {
  'white (png)': await flat('#ffffff').png().toBuffer(),
  'transparent (png)': await flat({ r: 0, g: 0, b: 0, alpha: 0 }, 4).png().toBuffer(),
  '#fafafa (jpeg)': await flat('#fafafa').jpeg().toBuffer(),
  'beige #efe7dc (png)': await flat('#efe7dc').png().toBuffer(),
  'linen #d8cbb8 (webp)': await flat('#d8cbb8').webp().toBuffer(),
  'mid grey #808080': await flat('#808080').png().toBuffer(),
  'charcoal #2b2b2b': await flat('#2b2b2b').png().toBuffer(),
  'black': await flat('#000000').png().toBuffer(),
  'a tinted canvas: terracotta #b4532a': await flat('#b4532a').png().toBuffer(),
  'a tinted canvas: sage #9caf88': await flat('#9caf88').jpeg({ quality: 90 }).toBuffer(),
  'black 50% on transparent (a shadow layer, flat)': await flat({ r: 0, g: 0, b: 0, alpha: 0.5 }, 4).png().toBuffer(),
  '#fafafa with a 2 px grey line': await flat('#fafafa').composite([{ input: await flat('#999999', 3, 600, 2).png().toBuffer(), left: 150, top: 450 }]).png().toBuffer(),
  'white with a 40 px dark dot': await flat('#ffffff').composite([{ input: await flat('#333333', 3, 40, 40).png().toBuffer(), left: 430, top: 430 }]).png().toBuffer(),
  'a grey ramp, dark to light (left to right)': await sharp(Buffer.from(Array.from({ length: 256 * 256 }, (_, i) => i % 256)), { raw: { width: 256, height: 256, channels: 1 } }).png().toBuffer(),
  'a grey ramp, light to dark (left to right)': await sharp(Buffer.from(Array.from({ length: 256 * 256 }, (_, i) => 255 - (i % 256))), { raw: { width: 256, height: 256, channels: 1 } }).png().toBuffer(),
  'a beige ramp top to bottom': await sharp(Buffer.from(Array.from({ length: 256 * 256 }, (_, i) => 200 + Math.floor(i / 256 / 6))), { raw: { width: 256, height: 256, channels: 1 } }).png().toBuffer(),
  'a depth map (radial, flat-ish)': await flat('#000000')
    .composite([{ input: Buffer.from('<svg width="900" height="900"><defs><radialGradient id="g"><stop offset="0" stop-color="#ddd"/><stop offset="1" stop-color="#222"/></radialGradient></defs><rect width="900" height="900" fill="url(#g)"/></svg>') }])
    .png()
    .toBuffer(),
};
const synthRows: Row[] = [];
for (const [k, b] of Object.entries(synth)) {
  const r = await rowOf(b, k, set.pixels);
  if (r) synthRows.push(r);
}
out.synthetic = synthRows.map((r) => ({ file: r.file, ink: r.ink, pop: r.pop, gate: r.gate, R20: r.R20.rule && `${r.R20.rule} d${r.R20.d} ${r.R20.via} ${r.R20.pic}`, P3q: r.P3q.rule && `${r.P3q.rule} d${r.P3q.d}`, S21: r.S21.rule }));

const ours: Row[] = [];
const story: Row[] = [];
const refs: Row[] = [];
let n = 0;
for (const root of ROOTS) {
  const isDist = root.endsWith('/web/dist');
  for (const f of walk(root)) {
    const rel = isDist ? `dist/${relative(root, f)}` : relative(resolve(root, '..'), f);
    const inSupplierFolder = isDist && /^dist\/media\/(?:products|story\/products)\//.test(rel);
    const isStory = isDist && /^dist\/media\/story\/products\//.test(rel);
    if (inSupplierFolder && !isStory) continue;
    let buf: Buffer;
    try {
      buf = readFileSync(f);
    } catch {
      continue;
    }
    const isRef = !isDist && /\/house-nordic-[^/]+\/refs\//.test(`/${rel}`);
    const product = isStory ? rel.split('/')[4] : undefined;
    const r = await rowOf(buf, rel, isStory ? setNoStory.pixels : set.pixels, product);
    if (!r) continue;
    (isStory ? story : isRef ? refs : ours).push(r);
    if (++n % 500 === 0) {
      dh.save();
      console.error(`… ${n} files, ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
  }
}
dh.save();
const count = (rows: Row[], k: 'R20' | 'P3q' | 'S21') => rows.filter((r) => r[k].rule).length;
const disagree = (rows: Row[]) => rows.filter((r) => !!r.gate !== !!r.S21.rule).map((r) => ({ file: r.file, gate: r.gate, emu: r.S21.rule }));
const lostVs = (rows: Row[], k: 'R20' | 'P3q') => rows.filter((r) => r[k].rule && !r.S21.rule).map((r) => ({ file: r.file, before: `${r[k].rule} d${r[k].d} ${r[k].via} ${r[k].pic}` }));
const groups = { story, refs, ours };
for (const [g, rows] of Object.entries(groups))
  out[g] = {
    files: rows.length,
    gate: rows.filter((r) => r.gate).length,
    R20: count(rows, 'R20'),
    P3q: count(rows, 'P3q'),
    S21: count(rows, 'S21'),
    gate_vs_my_S21_disagree: disagree(rows),
    lost_by_S21_vs_R20: lostVs(rows, 'R20').slice(0, 40),
    lost_by_S21_vs_P3q: lostVs(rows, 'P3q').slice(0, 40),
    ...(g === 'story' ? { of_their_own_product: rows.filter((r) => r.same_product).length } : {}),
    ...(g === 'ours'
      ? {
          hits_R20: rows.filter((r) => r.R20.rule).length,
          hits_examples_R20: rows.filter((r) => r.R20.rule).slice(0, 6).map((r) => `${r.file} ${r.R20.rule} d${r.R20.d} ${r.R20.via}`),
          margin_S21: [...rows].filter((r) => r.m21).sort((a, b) => a.m21!.d - b.m21!.d).slice(0, 8).map((r) => `${r.file} d${r.m21!.d} ${r.m21!.via} ${r.m21!.pic}`),
          margin_P3q: [...rows].filter((r) => r.m3).sort((a, b) => a.m3!.d - b.m3!.d).slice(0, 5).map((r) => `${r.file} d${r.m3!.d} ${r.m3!.via} ${r.m3!.pic}`),
          margin_R20: [...rows].filter((r) => r.m20).sort((a, b) => a.m20!.d - b.m20!.d).slice(0, 5).map((r) => `${r.file} d${r.m20!.d} ${r.m20!.via} ${r.m20!.pic}`),
          gate_margin_pairs: [...rows].filter((r) => r.gate_eligible && !r.gate).sort((a, b) => a.gate_d - b.gate_d).slice(0, 5).map((r) => `${r.file} d${r.gate_d} ${r.gate_pic}`),
          flat_files_pop_under_8: rows.filter((r) => r.pop < 8).length,
        }
      : {}),
  };
out.seconds = Math.round((Date.now() - t0) / 1000);
writeFileSync(OUT!, JSON.stringify(out, null, 1));
const o = out as Record<string, { files: number; gate: number; R20: number; P3q: number; S21: number; gate_vs_my_S21_disagree: unknown[]; lost_by_S21_vs_R20: unknown[]; lost_by_S21_vs_P3q: unknown[]; margin_S21?: string[] }>;
console.log(`QA S21 fp-scan: supplier set ${JSON.stringify(set.stats)}`);
for (const g of ['story', 'refs', 'ours'])
  console.log(`  ${g}: ${o[g]!.files} files; gate ${o[g]!.gate}; R20 ${o[g]!.R20}, P3q ${o[g]!.P3q}, S21(mine) ${o[g]!.S21}; gate≠mine ${o[g]!.gate_vs_my_S21_disagree.length}; lost vs R20 ${o[g]!.lost_by_S21_vs_R20.length}, vs P3q ${o[g]!.lost_by_S21_vs_P3q.length}`);
console.log(`  margin (S21, eligible pairs): ${o.ours!.margin_S21!.slice(0, 3).join(' | ')}`);
console.log(`  synthetic: ${(out.synthetic as { file: string; R20: string | null; P3q: string | null; S21: string | null; gate: string | null }[]).map((r) => `${r.file}: R20 ${r.R20 ? 'MATCH' : '-'} P3q ${r.P3q ? 'MATCH' : '-'} S21 ${r.S21 ?? '-'} gate ${r.gate ?? '-'}`).join(' | ')}`);
console.log(`  (${out.seconds}s)`);
