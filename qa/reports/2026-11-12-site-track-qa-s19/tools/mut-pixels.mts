/**
 * qa-agent, S19 (2026-11-12): my S17 pixel study (qa/reports/2026-11-12-site-track-qa-s17/tools/mut-pixels.mts) on my
 * isolated copy of f33cfe42. The same 78 originals (every third supplier original in the cache, plain), the same 25
 * changes and four more on flip, pad and border, against the set a PUBLIC build has (no story ledger). Caught = a match
 * with a picture of the same product, by:
 *   gate   the gate's own rule (`nearestPicture`: A; B with ink; mirrored and trimmed forms);
 *   emu    my emulation of that rule (to check it equals the gate's, then to try the guards of question 1 on it):
 *   P1     emu, but plain-vs-plain A skips when one ink < 2 and the other ≥ 8 (frontend-dev's proposal)
 *   P3     emu, but plain-vs-plain A needs d ≤ (popcount a + popcount b) / 2
 * Also, per change: the median dHash of the copy to its own picture's plain and mirrored forms, how many catches come
 * from B alone (the grey test), and the inks of the copies whose only catch is plain-vs-plain A with a near-blank side.
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

const [SITE_ARG, OUT] = process.argv.slice(2);
const SITE = resolve(SITE_ARG!);
const sharp = createRequire(join(SITE, 'package.json'))('sharp') as typeof import('sharp');
sharp.concurrency(2);
const dh = new DhashCache(join(process.env.QA_CACHE ?? '/tmp', 'qa19-mut-dhash.json'));
const shop = readLedger(join(SITE, '.generated', LEDGER_SHOP))!;
const set = await supplierSet({ site: SITE, ledgers: [shop], cacheDir: join(SITE, '.cache/supplier-images'), hosts: [], dhashes: dh });
const originals = set.pixels.filter((p) => p.variant === 'plain' && p.file.startsWith('.cache/')).filter((_, i) => i % 3 === 0);
const POP = (b: Uint8Array) => hammingBytes(b, new Uint8Array(b.length));

type Guard = 'none' | 'P1' | 'P3';
/** my emulation of nearestPicture's verdict (a match or not), with an optional guard on plain-vs-plain A */
function emu(mine: { plain: Prepared; trimmed: Prepared | null }, pics: SupplierPicture[], guard: Guard): { rule: 'A' | 'B' | null; via: string } {
  const forms: ['plain' | 'trimmed', Prepared][] = [['plain', mine.plain]];
  if (mine.trimmed) forms.push(['trimmed', mine.trimmed]);
  let hit: { rule: 'A' | 'B'; via: string } | null = null;
  for (const p of pics)
    for (const [k, f] of forms) {
      const d = hammingBytes(f.bits, p.bits);
      const pp = k === 'plain' && p.variant === 'plain';
      const inked = f.ink >= NEAR_MIN_INK && p.ink >= NEAR_MIN_INK;
      let aOk = d <= PIXEL_MAX_HAMMING && (pp || inked);
      if (aOk && pp && guard === 'P1' && Math.min(f.ink, p.ink) < 2 && Math.max(f.ink, p.ink) >= 8) aOk = false;
      if (aOk && pp && guard === 'P3' && d > (POP(f.bits) + POP(p.bits)) / 2) aOk = false;
      if (aOk) return { rule: 'A', via: `${k} vs ${p.variant}` };
      if (!hit && d <= NEAR_MAX_HAMMING && inked && mad32(f.grey, p.grey) <= NEAR_MAX_MAD32) hit = { rule: 'B', via: `${k} vs ${p.variant}` };
    }
  return hit ?? { rule: null, via: '' };
}

type M = (b: Buffer, w: number, h: number) => Promise<Buffer>;
const S = (b: Buffer) => sharp(b, { failOn: 'none' }).rotate();
const W = (b: Buffer) => S(b).flatten({ background: '#ffffff' });
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
  // S19: flip, pad and border, harder
  'flip + 50% jpeg q60': (b, w) => S(b).flop().resize(Math.round(w / 2)).jpeg({ quality: 60 }).toBuffer(),
  'flip + brightness +6%, hue +12°': (b) => S(b).flop().modulate({ brightness: 1.06, hue: 12, saturation: 1.1 }).toBuffer(),
  'pad at 60% onto a beige 1200×630 card': async (b) => {
    const inner = await W(b).resize({ height: 380, width: 1000, fit: 'inside' }).toBuffer();
    const m = await sharp(inner).metadata();
    return sharp({ create: { width: 1200, height: 630, channels: 3, background: '#efe7dc' } })
      .composite([{ input: inner, left: Math.round((1200 - m.width!) / 2), top: Math.round((630 - m.height!) / 2) }])
      .jpeg({ quality: 82 })
      .toBuffer();
  },
  'passe-partout: 4% white mat, 12 px dark frame': (b, w) =>
    W(b)
      .extend({ top: Math.round(w * 0.04), bottom: Math.round(w * 0.04), left: Math.round(w * 0.04), right: Math.round(w * 0.04), background: '#ffffff' })
      .png()
      .toBuffer()
      .then((x) => sharp(x).extend({ top: 12, bottom: 12, left: 12, right: 12, background: '#2b2b2b' }).webp().toBuffer()),
  'pad onto a white 4:3 canvas + flip': (b, w, h) => S(b).flop().extend({ left: Math.round(w * 0.2), right: Math.round(w * 0.2), top: 0, bottom: Math.round(h * 0.1), background: '#ffffff' }).toBuffer(),
};

type Row = {
  n: number;
  gate: number;
  emu: number;
  emu_equals_gate: boolean;
  P1: number;
  P3: number;
  gate_by: Record<string, number>;
  B_only: number;
  dhash_median_plain: number;
  dhash_median_mirrored: number;
  lost_P1: string[];
  lost_P3: string[];
  missed_examples: string[];
};
const rows: Record<string, Row> = {};
const inkPairs: { change: string; product: string; ink_copy: number; ink_pic: number; d: number }[] = [];
const t0 = Date.now();
const med = (x: number[]) => (x.sort((a, b) => a - b), x[Math.floor(x.length / 2)] ?? -1);
for (const [name, f] of Object.entries(MUT)) {
  const r: Row = { n: 0, gate: 0, emu: 0, emu_equals_gate: true, P1: 0, P3: 0, gate_by: {}, B_only: 0, dhash_median_plain: -1, dhash_median_mirrored: -1, lost_P1: [], lost_P3: [], missed_examples: [] };
  const dp: number[] = [];
  const dm: number[] = [];
  for (const p of originals) {
    const buf = readFileSync(join(SITE, p.file));
    const meta = await sharp(buf, { failOn: 'none' }).rotate().toBuffer({ resolveWithObject: true });
    let out: Buffer;
    try {
      out = await f(buf, meta.info.width, meta.info.height);
    } catch {
      continue;
    }
    const v = await dh.variants(out, sha256(out), ['plain', 'trimmed']);
    if (!v.plain) continue;
    r.n++;
    const mine = { plain: prepare(v.plain), trimmed: v.trimmed ? prepare(v.trimmed) : null };
    const own = (q: SupplierPicture) => q.product === p.product;
    const pics = set.pixels.filter(own);
    const { best } = nearestPicture(mine, set.pixels, PIXEL_MAX_HAMMING, own);
    const e = emu(mine, pics, 'none');
    const e1 = emu(mine, pics, 'P1');
    const e3 = emu(mine, pics, 'P3');
    if (!!best?.rule !== !!e.rule) r.emu_equals_gate = false;
    if (best?.rule) {
      r.gate++;
      const k = `${best.rule} ${best.mine} vs ${best.p.variant}`;
      r.gate_by[k] = (r.gate_by[k] ?? 0) + 1;
      if (best.rule === 'B') r.B_only++;
    } else if (r.missed_examples.length < 3) r.missed_examples.push(p.product);
    if (e.rule) r.emu++;
    if (e1.rule) r.P1++;
    else if (e.rule) r.lost_P1.push(p.product);
    if (e3.rule) r.P3++;
    else if (e.rule) r.lost_P3.push(p.product);
    const plainPic = pics.find((q) => q.file === p.file && q.variant === 'plain');
    const mirPic = pics.find((q) => q.file === p.file && q.variant === 'mirrored');
    if (plainPic) {
      const d = hammingBytes(mine.plain.bits, plainPic.bits);
      dp.push(d);
      if (d <= PIXEL_MAX_HAMMING && Math.min(mine.plain.ink, plainPic.ink) < 2) inkPairs.push({ change: name, product: p.product, ink_copy: Number(mine.plain.ink.toFixed(1)), ink_pic: Number(plainPic.ink.toFixed(1)), d });
    }
    if (mirPic) dm.push(hammingBytes(mine.plain.bits, mirPic.bits));
  }
  r.dhash_median_plain = med(dp);
  r.dhash_median_mirrored = med(dm);
  rows[name] = r;
  dh.save();
  console.error(`${name}: gate ${r.gate}/${r.n} (B only ${r.B_only}); emu=gate ${r.emu_equals_gate}; P1 ${r.P1}, P3 ${r.P3} (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
}
dh.save();
const inks = originals.map((p) => p.ink).sort((a, b) => a - b);
writeFileSync(
  OUT!,
  JSON.stringify(
    {
      originals: originals.length,
      originals_ink: { min: Number(inks[0]!.toFixed(1)), p10: Number(inks[Math.floor(inks.length / 10)]!.toFixed(1)), median: Number(med([...inks]).toFixed(1)), below_4: inks.filter((x) => x < 4).length, below_8: inks.filter((x) => x < 8).length },
      public_set: set.stats,
      rows,
      plain_A_pairs_with_a_near_blank_side: inkPairs,
    },
    null,
    1,
  ),
);
console.log(`QA S19 mut-pixels (${originals.length} originals, every third of the cache; caught = a match with the same product): gate (B only) | P1 | P3 | median dHash to its own plain / mirrored`);
for (const [k, r] of Object.entries(rows))
  console.log(
    `  ${k.padEnd(44)} ${String(r.gate).padStart(3)}/${r.n} (B ${String(r.B_only).padStart(2)})${r.emu_equals_gate ? '' : ' EMU≠GATE'} | P1 ${String(r.P1).padStart(3)} | P3 ${String(r.P3).padStart(3)} | ${r.dhash_median_plain}/${r.dhash_median_mirrored}  ${JSON.stringify(r.gate_by)}`,
  );
console.log(`  plain-vs-plain A pairs with a near-blank side (ink < 2): ${inkPairs.length}`);
