/**
 * qa-agent, S17 (2026-11-12): the near-miss rule (B: dHash ≤ 48 and 32×32 grey MAD ≤ 3) on the groups that decide it,
 * and two tighter variants, with the copy's own fingerprint and supplier set (tools/lib/rights-content.ts at a988b099):
 *   current  A (dHash ≤ 24) or B
 *   ink      A, or B only when both pictures carry ink: mean(255 − grey) ≥ 4 on the 32×32 image (a near-blank picture,
 *            or a layer that is mostly transparent, is no evidence of anything)
 *   masked   A, or dHash ≤ 48 and the MAD over the pixels where either image has ink (grey < 245) ≤ 6, that area ≥ 3%
 * Groups: the 321 story copies (true copies, against the PUBLIC set: no story ledger; any picture, as the gate does); the warm-modern phase-2 layers and
 * work files (the layers the site ships next as media/house/…/N.product|shadow); the IMG1 pilot (our own product
 * pictures); the downloaded supplier references kept under assets/renders (true copies); synthetic flat images.
 *
 *   tsx fp-rule-alt.mts <copy site dir> <out.json>
 */
import { readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
import { createRequire } from 'node:module';
import {
  DhashCache,
  LEDGER_SHOP,
  LEDGER_STORY,
  hamming,
  mad32,
  readLedger,
  sha256,
  supplierSet,
  type SupplierPicture,
  type Fingerprint,
} from '../build-s17/site/tools/lib/rights-content';

const [SITE_ARG, OUT] = process.argv.slice(2);
const SITE = resolve(SITE_ARG!);
const REPO = '/home/user/homedesign-app';
const sharp = createRequire(join(SITE, 'package.json'))('sharp') as typeof import('sharp');
sharp.concurrency(1);
const RASTER = /\.(?:png|jpe?g|webp|avif)$/i;
const walk = (d: string): string[] =>
  readdirSync(d).flatMap((n) => {
    const p = join(d, n);
    const s = statSync(p);
    return s.isDirectory() ? walk(p) : RASTER.test(n) ? [p] : [];
  });
const dh = new DhashCache(join(process.env.QA_CACHE ?? '/tmp', 'qa17-fp-dhash.json'));
const ledgers = [readLedger(join(SITE, '.generated', LEDGER_SHOP)), readLedger(join(SITE, '.generated', LEDGER_STORY))].filter((l) => l !== null);
const full = await supplierSet({ site: SITE, ledgers, cacheDir: join(SITE, '.cache/supplier-images'), hosts: [], dhashes: dh });
const pub = await supplierSet({ site: SITE, ledgers: ledgers.filter((l) => l.source !== 'story'), cacheDir: join(SITE, '.cache/supplier-images'), hosts: [], dhashes: dh });

const ink = (g: Buffer) => {
  let s = 0;
  for (let i = 0; i < 1024; i++) s += 255 - g[i]!;
  return s / 1024;
};
function masked(a: Buffer, b: Buffer): { m: number; area: number } {
  let s = 0;
  let n = 0;
  for (let i = 0; i < 1024; i++)
    if (a[i]! < 245 || b[i]! < 245) {
      s += Math.abs(a[i]! - b[i]!);
      n++;
    }
  return { m: n ? s / n : 0, area: n / 1024 };
}
type Verdict = { current: boolean; ink: boolean; masked: boolean; d: number; mad: number | null; why: string };
function judge(fp: Fingerprint, set: SupplierPicture[], sameProduct?: string): Verdict {
  let cur = false;
  let ik = false;
  let mk = false;
  let bestD = 999;
  let bestMad: number | null = null;
  let why = '';
  const ic = ink(fp.grey);
  for (const p of set) {
    if (sameProduct && p.product !== sameProduct && !p.picture.includes(sameProduct)) continue;
    const d = hamming(fp.dhash, p.dhash);
    if (d < bestD) bestD = d;
    if (d <= 24) {
      cur = ik = mk = true;
      why ||= `A d${d} ${p.picture}`;
      continue;
    }
    if (d > 48) continue;
    const m = mad32(fp.grey, p.grey);
    if (bestMad === null || m < bestMad) bestMad = m;
    if (m <= 3) {
      cur = true;
      why ||= `B d${d} mad${m.toFixed(2)} ${p.picture} (ink ${ic.toFixed(1)}/${ink(p.grey).toFixed(1)})`;
      if (ic >= 4 && ink(p.grey) >= 4) ik = true;
    }
    const k = masked(fp.grey, p.grey);
    if (k.m <= 6 && k.area >= 0.03) mk = true;
  }
  return { current: cur, ink: ik, masked: mk, d: bestD, mad: bestMad === null ? null : Number(bestMad.toFixed(2)), why };
}

const groups: Record<string, { files: string[]; set: SupplierPicture[]; truth: 'copy' | 'ours'; own?: boolean }> = {
  'story copies (true copies; public set)': { files: walk(join(SITE, 'web/dist/media/story/products')), set: pub.pixels, truth: 'copy', own: false },
  'downloaded supplier references under assets/renders (true copies)': {
    files: [...walk(join(REPO, 'assets/renders/house-nordic-2026-10-25/refs')), ...walk(join(REPO, 'assets/renders/house-nordic-v7-2026-11-02/refs'))],
    set: full.pixels,
    truth: 'copy',
  },
  'warm-modern phase-2 layers and work files (ours)': { files: walk(join(REPO, 'assets/renders/living-room/warm-modern/phase2-2026-11-10')), set: full.pixels, truth: 'ours' },
  'IMG1 pilot (ours)': { files: walk(join(REPO, 'assets/renders/products/img1-pilot-2026-11-12')), set: full.pixels, truth: 'ours' },
  'the flag build media outside the supplier folders (ours)': {
    files: ['house', 'rooms', 'transitions', 'test'].flatMap((d) => walk(join(SITE, 'web/dist/media', d))),
    set: full.pixels,
    truth: 'ours',
  },
};
const out: Record<string, unknown> = {};
for (const [name, g] of Object.entries(groups)) {
  const rows: (Verdict & { file: string })[] = [];
  for (const f of g.files) {
    const buf = readFileSync(f);
    const fp = await dh.of(buf, sha256(buf));
    if (!fp) continue;
    // a story copy counts as caught when it matches a picture of its own product
    const own = g.own ? /story\/products\/([^/]+)\//.exec(f)?.[1] : undefined;
    rows.push({ file: relative(f.startsWith(REPO) ? REPO : SITE, f), ...judge(fp, g.set, own) });
  }
  const c = (k: 'current' | 'ink' | 'masked') => rows.filter((r) => r[k]).length;
  out[name] = {
    files: rows.length,
    truth: g.truth,
    matched: { current: c('current'), ink: c('ink'), masked: c('masked') },
    current_only_B_examples: rows.filter((r) => r.current && r.why.startsWith('B')).slice(0, 6).map((r) => `${r.file}: ${r.why}`),
    lost_by_ink: rows.filter((r) => r.current && !r.ink).slice(0, 10).map((r) => `${r.file}: ${r.why}`),
    lost_by_masked: rows.filter((r) => r.current && !r.masked).slice(0, 10).map((r) => `${r.file}: ${r.why}`),
    nearest: [...rows].sort((a, b) => a.d - b.d).slice(0, 5).map((r) => `${r.file}: dHash ${r.d}, MAD ${r.mad}`),
  };
}
dh.save();
// the near-blank supplier picture behind most B matches
const blank = full.pixels.find((p) => p.picture.endsWith('floor-lamp-black-drum-linen-uaeow/opt-06334f443d'));
out['the near-blank supplier picture'] = blank ? { picture: blank.picture, file: blank.file, ink: Number(ink(blank.grey).toFixed(2)), dhash_popcount: hamming(blank.dhash, '0'.repeat(64)) } : null;
writeFileSync(OUT!, JSON.stringify(out, null, 1));
for (const [k, v] of Object.entries(out)) console.log(`QA rule ${k}: ${JSON.stringify((v as { files?: number; matched?: unknown }).files !== undefined ? { files: (v as { files: number }).files, truth: (v as { truth: string }).truth, matched: (v as { matched: unknown }).matched } : v)}`);
