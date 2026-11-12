/**
 * qa-agent, S21 (2026-11-12): ת66 and frontend-dev's question 1 (the two extensions of P3), on my isolated copy of
 * 7b42ddc1. Does S21's rule lose a true copy that the rule before it caught?
 * Rules, each my own emulation over every pair of forms (mine plain/trimmed × the supplier's plain/mirrored/trimmed…):
 *   R20   the S19/S20 gate: A d ≤ 24 (plain vs plain, or ink ≥ 4 on both sides for the other forms); B d ≤ 48, grey ≤ 3, ink
 *   P3q   QA's S19 ruling: R20, and plain-vs-plain A only when d ≤ (pop a + pop b) / 2
 *   S21   as briefed + both extensions: R20's A also needs d ≤ (pop a + pop b) / 2 on EVERY pair of forms, and two flat
 *         hashes (pop < 8 both) also a 32×32 grey difference ≤ 8
 *   gate  the S21 gate itself (`nearestPicture`), to check my S21 emulation equals it on every copy
 * Originals (plain pictures in the supplier cache, against the set a PUBLIC build has; caught = a match with a picture
 * of the same product):
 *   every3   every third original (S19's 78)
 *   lowpop   the 25 originals whose lowest form popcount is lowest (where the extensions bite first), and the thin lamp
 * Changes: S19's 30, and mine: an inverted picture, inverted + flip, grey + flip, a strong sepia, ±15% brightness, low
 * contrast, 2% crop, 2% crop + flip, 180°, padded onto black, a ghost (the picture at 12% on a beige canvas: a tinted
 * canvas), posterized; and, for the flat forms, tinted copies of every supplier picture with a form under 8 set bits.
 *
 *   tsx mut-s21.mts <copy site dir> <out.json>
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
} from '../build-s21/site/tools/lib/rights-content';

const [SITE_ARG, OUT] = process.argv.slice(2);
const SITE = resolve(SITE_ARG!);
const sharp = createRequire(join(SITE, 'package.json'))('sharp') as typeof import('sharp');
sharp.concurrency(2);
const dh = new DhashCache(join(process.env.QA_CACHE ?? '/tmp', 'qa21-mut-dhash.json'));
const shop = readLedger(join(SITE, '.generated', LEDGER_SHOP))!;
const set = await supplierSet({ site: SITE, ledgers: [shop], cacheDir: join(SITE, '.cache/supplier-images'), hosts: [], dhashes: dh });
const POP = (b: Uint8Array) => hammingBytes(b, new Uint8Array(b.length));
const plainCache = set.pixels.filter((p) => p.variant === 'plain' && p.file.startsWith('.cache/'));
const every3 = plainCache.filter((_, i) => i % 3 === 0);
const lowestPop = (p: SupplierPicture) => Math.min(...set.pixels.filter((q) => q.file === p.file).map((q) => POP(q.bits)));
const lowpop = [...plainCache].sort((a, b) => lowestPop(a) - lowestPop(b)).slice(0, 25);
const thin = plainCache.filter((p) => /floor-lamp/.test(p.product) && p.ink < 4);
for (const t of thin) if (!lowpop.includes(t)) lowpop.push(t);

type Rule = 'R20' | 'P3q' | 'S21';
function emu(mine: { plain: Prepared; trimmed: Prepared | null }, pics: SupplierPicture[], rule: Rule): { rule: 'A' | 'B' | null; via: string } {
  const forms: ['plain' | 'trimmed', Prepared][] = [['plain', mine.plain]];
  if (mine.trimmed) forms.push(['trimmed', mine.trimmed]);
  let hit: { rule: 'A' | 'B'; via: string } | null = null;
  for (const p of pics)
    for (const [k, f] of forms) {
      const d = hammingBytes(f.bits, p.bits);
      const pp = k === 'plain' && p.variant === 'plain';
      const inked = f.ink >= NEAR_MIN_INK && p.ink >= NEAR_MIN_INK;
      const pa = POP(f.bits);
      const pb = POP(p.bits);
      let aOk = d <= PIXEL_MAX_HAMMING && (pp || inked);
      if (aOk && rule === 'P3q' && pp && 2 * d > pa + pb) aOk = false;
      if (aOk && rule === 'S21' && 2 * d > pa + pb) aOk = false;
      if (aOk && rule === 'S21' && pa < 8 && pb < 8 && mad32(f.grey, p.grey) > 8) aOk = false;
      if (aOk) return { rule: 'A', via: `${k} vs ${p.variant} d${d} pop ${pa}/${pb}` };
      if (!hit && d <= NEAR_MAX_HAMMING && inked && mad32(f.grey, p.grey) <= NEAR_MAX_MAD32) hit = { rule: 'B', via: `${k} vs ${p.variant} d${d}` };
    }
  return hit ?? { rule: null, via: '' };
}

type M = (b: Buffer, w: number, h: number) => Promise<Buffer>;
const S = (b: Buffer) => sharp(b, { failOn: 'none' }).rotate();
const W = (b: Buffer) => S(b).flatten({ background: '#ffffff' });
const MUT: Record<string, M> = {
  // S19's
  'resize 50% (webp q80)': (b, w) => S(b).resize(Math.round(w / 2)).webp({ quality: 80 }).toBuffer(),
  'resize 25% (jpeg q60)': (b, w) => S(b).resize(Math.round(w / 4)).jpeg({ quality: 60 }).toBuffer(),
  'thumbnail 160 px (webp)': (b) => S(b).resize(160).webp({ quality: 70 }).toBuffer(),
  'thumbnail 96 px (jpeg q50)': (b) => S(b).resize(96).jpeg({ quality: 50 }).toBuffer(),
  'recompress jpeg q35': (b) => S(b).jpeg({ quality: 35 }).toBuffer(),
  'recompress avif q30': (b) => S(b).avif({ quality: 30 }).toBuffer(),
  'crop 5% each side': (b, w, h) => S(b).extract({ left: Math.round(w * 0.05), top: Math.round(h * 0.05), width: Math.round(w * 0.9), height: Math.round(h * 0.9) }).toBuffer(),
  'crop 10% each side': (b, w, h) => S(b).extract({ left: Math.round(w * 0.1), top: Math.round(h * 0.1), width: Math.round(w * 0.8), height: Math.round(h * 0.8) }).toBuffer(),
  'crop left third off': (b, w, h) => S(b).extract({ left: Math.round(w / 3), top: 0, width: w - Math.round(w / 3), height: h }).toBuffer(),
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
  // S21, mine
  'invert (negative)': (b) => W(b).negate({ alpha: false }).toBuffer(),
  'invert + flip': (b) => W(b).negate({ alpha: false }).flop().toBuffer(),
  'grayscale + flip': (b) => S(b).grayscale().flop().toBuffer(),
  'strong sepia': (b) => S(b).recomb([[0.393, 0.769, 0.189], [0.349, 0.686, 0.168], [0.272, 0.534, 0.131]]).toBuffer(),
  'brightness +15%': (b) => S(b).modulate({ brightness: 1.15 }).toBuffer(),
  'brightness −15%': (b) => S(b).modulate({ brightness: 0.85 }).toBuffer(),
  'low contrast (×0.6, +50)': (b) => W(b).linear(0.6, 50).toBuffer(),
  'crop 2% each side': (b, w, h) => S(b).extract({ left: Math.round(w * 0.02), top: Math.round(h * 0.02), width: Math.round(w * 0.96), height: Math.round(h * 0.96) }).toBuffer(),
  'crop 2% + flip': (b, w, h) => S(b).extract({ left: Math.round(w * 0.02), top: Math.round(h * 0.02), width: Math.round(w * 0.96), height: Math.round(h * 0.96) }).flop().toBuffer(),
  'rotate 180°': (b) => S(b).rotate(180).toBuffer(),
  'pad onto black 4:3': (b, w, h) => W(b).extend({ left: Math.round(w * 0.2), right: Math.round(w * 0.2), top: 0, bottom: Math.round(h * 0.1), background: '#000000' }).toBuffer(),
  'a ghost: 12% on a beige canvas (tinted canvas)': async (b, w, h) => {
    const inner = await W(b).ensureAlpha(0.12).png().toBuffer();
    return sharp({ create: { width: w, height: h, channels: 3, background: '#efe7dc' } }).composite([{ input: inner }]).png().toBuffer();
  },
  'posterize (4 levels)': async (b) => {
    const { data, info } = await W(b).raw().toBuffer({ resolveWithObject: true });
    for (let i = 0; i < data.length; i++) data[i] = Math.round(data[i]! / 85) * 85;
    return sharp(data, { raw: { width: info.width, height: info.height, channels: info.channels } }).png().toBuffer();
  },
};

type Row = { n: number; gate: number; R20: number; P3q: number; S21: number; emu_equals_gate: boolean; lost_vs_R20: string[]; lost_vs_P3q: string[]; gained_vs_R20: string[] };
async function study(name: string, originals: SupplierPicture[]) {
  const rows: Record<string, Row> = {};
  for (const [mname, f] of Object.entries(MUT)) {
    const r: Row = { n: 0, gate: 0, R20: 0, P3q: 0, S21: 0, emu_equals_gate: true, lost_vs_R20: [], lost_vs_P3q: [], gained_vs_R20: [] };
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
      const e20 = emu(mine, pics, 'R20');
      const e3 = emu(mine, pics, 'P3q');
      const e21 = emu(mine, pics, 'S21');
      if (!!best?.rule !== !!e21.rule) r.emu_equals_gate = false;
      if (best?.rule) r.gate++;
      if (e20.rule) r.R20++;
      if (e3.rule) r.P3q++;
      if (e21.rule) r.S21++;
      const tag = `${p.product} (${p.file.split('/').pop()}; R20 ${e20.via || '-'})`;
      if (e20.rule && !e21.rule) r.lost_vs_R20.push(tag);
      if (e3.rule && !e21.rule) r.lost_vs_P3q.push(tag);
      if (!e20.rule && e21.rule) r.gained_vs_R20.push(tag);
    }
    rows[mname] = r;
    dh.save();
    console.error(`${name} ${mname}: gate ${r.gate}/${r.n}; R20 ${r.R20}, P3q ${r.P3q}, S21 ${r.S21}${r.emu_equals_gate ? '' : ' EMU≠GATE'}${r.lost_vs_R20.length ? ` LOST ${r.lost_vs_R20.length}` : ''}`);
  }
  return rows;
}

const t0 = Date.now();
const out: Record<string, unknown> = {
  public_set: set.stats,
  originals: { every3: every3.length, lowpop: lowpop.map((p) => `${p.product} ${p.file.split('/').pop()} min-pop ${lowestPop(p)} ink ${p.ink.toFixed(1)}`) },
  supplier_forms_popcount: (() => {
    const pops = set.pixels.map((p) => POP(p.bits)).sort((a, b) => a - b);
    return {
      fingerprints: pops.length,
      under_8: set.pixels.filter((p) => POP(p.bits) < 8).map((p) => `${p.product} ${p.variant} pop ${POP(p.bits)} ink ${p.ink.toFixed(1)}`),
      under_48: pops.filter((x) => x < 48).length,
      p01: pops[Math.floor(pops.length / 100)],
      median: pops[Math.floor(pops.length / 2)],
    };
  })(),
};
out.lowpop = await study('lowpop', lowpop);
// the flat forms: tinted copies of every supplier picture with a form under 8 set bits
const flatSrc = [...new Set(set.pixels.filter((p) => POP(p.bits) < 8 && p.file.startsWith('.cache/')).map((p) => p.file))];
const flatOriginals = flatSrc.map((f) => set.pixels.find((p) => p.file === f && p.variant === 'plain')!).filter(Boolean);
out.flat_supplier_pictures = flatOriginals.map((p) => p.product);
out.flat = flatOriginals.length ? await study('flat', flatOriginals) : {};
out.every3 = await study('every3', every3);
out.seconds = Math.round((Date.now() - t0) / 1000);
writeFileSync(OUT!, JSON.stringify(out, null, 1));
for (const k of ['lowpop', 'flat', 'every3'] as const) {
  const rows = out[k] as Record<string, Row>;
  const lost = Object.entries(rows).flatMap(([m, r]) => r.lost_vs_R20.map((x) => `${m}: ${x}`));
  const lost3 = Object.entries(rows).flatMap(([m, r]) => r.lost_vs_P3q.map((x) => `${m}: ${x}`));
  console.log(`QA S21 mut (${k}): ${Object.keys(rows).length} changes; copies lost by S21 against R20: ${lost.length}; against P3q: ${lost3.length}; emu=gate in all: ${Object.values(rows).every((r) => r.emu_equals_gate)}`);
  for (const [m, r] of Object.entries(rows)) console.log(`  ${m.padEnd(48)} R20 ${String(r.R20).padStart(3)} | P3q ${String(r.P3q).padStart(3)} | S21 ${String(r.S21).padStart(3)} | gate ${String(r.gate).padStart(3)} / ${r.n}`);
  for (const x of lost.slice(0, 20)) console.log(`  LOST ${x}`);
}
