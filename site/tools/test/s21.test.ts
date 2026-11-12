/**
 * S21, the fixes of QA S19 (briefs/site-s21-qa-fixes-2026-11-12.md), the build's side:
 * - ת66: rule A only when d ≤ (popcount a + popcount b) / 2 (QA’s P3, on every pair of forms). A flat picture never
 *   matches an inked one by A, whatever supplier picture comes; true copies still do; the margin printed every build
 *   counts only the pairs A may judge.
 * - QA note ה14: eleven more ways a card denies a texture ("w/o", "texture-less", "Texture: N/A", "Smooth", "flat",
 *   "Embossed: N", "Textured: False", "isnt", "doesnt", "(texture? no)") read as a print, and the claims stay.
 * - QA note ה15: the gate says what it does not catch.
 * The proof on the real files (321/321 story copies, 12/12 references, the margin) is QA's own scan, run on this tree:
 * qa/reports/2026-11-07-site-track/s21/data/fp-scan.log.
 */
import { describe, expect, it } from 'vitest';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import sharp from 'sharp';
import {
  DhashCache,
  PIXEL_MAX_HAMMING,
  fingerprint,
  hammingBytes,
  nearestPicture,
  pixelRule,
  popcount,
  prepare,
  scanBuild,
  sha256,
  supplierSet,
  type Fingerprint,
  type Ledger,
  type SupplierPicture,
} from '../lib/rights-content';
import { materialHe } from '../lib/hebrew';
import { sitePath } from '../lib/paths';

const tmp = (name: string) => mkdtempSync(join(tmpdir(), `hd-s21-${name}-`));
const put = (root: string, rel: string, b: Buffer | string) => {
  mkdirSync(join(root, rel, '..'), { recursive: true });
  writeFileSync(join(root, rel), b);
};
const white = (w: number, h: number) => sharp({ create: { width: w, height: h, channels: 3, background: '#ffffff' } });
const prep = (f: Fingerprint | null | undefined) => prepare(f!);
/** a hash with `n` set bits from bit `from` */
const run = (from: number, n: number) => {
  const b = Buffer.alloc(32);
  for (let i = from; i < from + n; i++) b[i >> 3]! |= 1 << (7 - (i & 7));
  return b.toString('hex');
};
const grey = (v: number) => Buffer.alloc(1024, v);

// ---------------------------------------------------------------- ת66
describe('ת66: rule A judges a pair only when its hashes share their set bits (QA’s P3)', () => {
  it('the rule on fingerprints: QA’s margin pair, a supplier picture with few set bits, two flat pictures, a true copy', () => {
    // QA's nearest of ours: a shadow layer (popcount 3, ink 0.1) 27 bits from a vase (popcount 30): never A, at any threshold
    const shadow = prepare({ dhash: run(0, 3), grey: grey(255) });
    const vase = prepare({ dhash: run(0, 30), grey: grey(160) });
    expect([shadow.pop, vase.pop, hammingBytes(shadow.bits, vase.bits)]).toEqual([3, 30, 27]);
    expect(pixelRule(shadow, vase, 40)).toMatchObject({ d: 27, rule: null, aEligible: false });
    // QA's worry: a supplier picture with popcount ≤ 24 would have matched every flat layer by A (S19: d = 20 ≤ 24)
    const flat = prepare({ dhash: run(0, 0), grey: grey(255) });
    const sparse = prepare({ dhash: run(40, 20), grey: grey(200) });
    expect(hammingBytes(flat.bits, sparse.bits)).toBeLessThanOrEqual(PIXEL_MAX_HAMMING);
    expect(pixelRule(flat, sparse)).toMatchObject({ d: 20, rule: null });
    expect(pixelRule(sparse, flat)).toMatchObject({ rule: null });
    // two flat pictures still match each other when their greys agree (harmless: nothing of a supplier's is in either);
    // when they do not, they are no likeness (a white layer and a dark box)
    expect(pixelRule(flat, prepare({ dhash: run(0, 0), grey: grey(250) }))).toMatchObject({ d: 0, rule: 'A' });
    expect(pixelRule(flat, prepare({ dhash: run(0, 0), grey: grey(40) }))).toMatchObject({ d: 0, rule: null });
    // a true copy shares its set bits: A as before, ink or none
    expect(pixelRule(prepare({ dhash: run(0, 30), grey: grey(255) }), prepare({ dhash: run(4, 30), grey: grey(255) }))).toMatchObject({ d: 8, rule: 'A' });
    // the bound itself: d = (pa + pb) / 2 is in, one more bit is out
    expect(pixelRule(prepare({ dhash: run(0, 20), grey: grey(200) }), prepare({ dhash: run(10, 20), grey: grey(150) }))).toMatchObject({ d: 20, rule: 'A' });
    expect(pixelRule(prepare({ dhash: run(0, 20), grey: grey(200) }), prepare({ dhash: run(10, 21), grey: grey(150) }))).toMatchObject({ d: 21, rule: null });
    // on a mirrored or trimmed form too (S21: a flat canvas with a little ink passed the ink guard there)
    expect(pixelRule(prepare({ dhash: run(0, 0), grey: grey(250) }), prepare({ dhash: run(0, 20), grey: grey(200) }), 24, { inkForA: true })).toMatchObject({
      d: 20,
      rule: null,
    });
    // B is unchanged (both inked, grey within 3)
    expect(pixelRule(prepare({ dhash: run(0, 0), grey: grey(250) }), prepare({ dhash: run(0, 30), grey: grey(251) }))).toMatchObject({ rule: 'B' });
    expect(popcount(Uint8Array.from(Buffer.from(run(0, 256), 'hex')))).toBe(256);
  });

  it('the margin: without a match, "the nearest" is the nearest pair rule A may judge, not a sparse or flat one', () => {
    const mine = { plain: prepare({ dhash: run(0, 30), grey: grey(180) }), trimmed: null };
    const pic = (dhash: string, name: string): SupplierPicture =>
      ({ ...prepare({ dhash, grey: grey(200) }), picture: name, product: name, rights: 'unclear', variant: 'plain' }) as unknown as SupplierPicture;
    const sparse = pic(run(0, 4), 'sparse'); // 26 bits away, but 2 × 26 > 30 + 4: no step towards A
    const likeness = pic(run(14, 30), 'likeness'); // 28 bits away, 2 × 28 ≤ 30 + 30
    const { best } = nearestPicture(mine, [sparse, likeness]);
    expect(best).toMatchObject({ rule: null, d: 28, aEligible: true });
    expect(best!.p.picture).toBe('likeness');
    // with no eligible pair at all, the nearest of all is still reported (and kept off the printed margin by scanBuild)
    expect(nearestPicture(mine, [sparse]).best).toMatchObject({ d: 26, aEligible: false });
  });

  it('on pictures: flat layers within the threshold of a supplier picture (S19: matched by A) find nothing now; a copy of it is found', async () => {
    // a dark bar on white: few set bits (64 of 256). QA's case is a supplier picture whose popcount is within the
    // threshold of rule A; the same situation here is the threshold raised above the bar's popcount (70)
    const MAX = 70;
    const bar = await white(816, 768)
      .composite([
        {
          input: await sharp({ create: { width: 48, height: 768, channels: 3, background: '#202020' } })
            .png()
            .toBuffer(),
          left: 576,
          top: 0,
        },
      ])
      .jpeg({ quality: 90 })
      .toBuffer();
    const barFp = prep(await fingerprint(bar));
    expect(barFp.pop).toBeLessThanOrEqual(MAX);
    const site = tmp('site');
    const product = 'bar-x';
    const file = `web/public/media/products/${product}/opt-0123456789.800.jpg`;
    put(site, file, bar);
    const ledgers: Ledger[] = [
      {
        generated_at: 'now',
        source: 'shop+cache',
        entries: [{ file, sha256: sha256(bar), product, rights: 'unclear', source: 'shop', picture: `products/${product}/opt-0123456789`, width: 800 }],
      },
    ];
    const flats: Record<string, Buffer> = {
      'white.png': await white(1000, 1000).png().toBuffer(),
      'transparent.png': await sharp({ create: { width: 1000, height: 800, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } })
        .png()
        .toBuffer(),
      'canvas-near-white.png': await sharp({ create: { width: 900, height: 600, channels: 3, background: '#fafafa' } })
        .png()
        .toBuffer(),
    };
    for (const [name, b] of Object.entries(flats)) {
      const f = prep(await fingerprint(b));
      // without the guard, rule A at this threshold would match it: it sits popcount(bar) bits from the bar
      expect(hammingBytes(f.bits, barFp.bits), name).toBeLessThanOrEqual(MAX);
      expect(pixelRule(f, barFp, MAX).rule, name).toBeNull();
    }
    const scan = async (files: Record<string, Buffer>) => {
      const dist = tmp('dist');
      for (const [k, b] of Object.entries(files)) put(dist, k, b);
      const dh = new DhashCache();
      const set = await supplierSet({ site, ledgers, cacheDir: join(site, '.cache/supplier-images'), hosts: [], dhashes: dh });
      const r = await scanBuild(dist, set, dh, { maxHamming: MAX });
      rmSync(dist, { recursive: true, force: true });
      return r;
    };
    const none = await scan(Object.fromEntries(Object.entries(flats).map(([k, b]) => [`media/house/${k}`, b])));
    expect(none.findings.filter((f) => f.how === 'pixels')).toEqual([]);
    // the margin printed lists no flat layer as a step towards rule A
    expect(none.stats.nearest.map((n) => n.where)).toEqual([]);
    const copy = await sharp(bar).resize(408).webp({ quality: 70 }).toBuffer();
    const found = await scan({ 'media/x/copy.webp': copy });
    expect(found.findings.map((f) => [f.where, f.how, f.rule])).toEqual([['media/x/copy.webp', 'pixels', 'A']]);
    // what P3 alone left (found here; S21 question 1): a flat inked canvas against the bar's TRIMMED form, itself flat
    // (the dark bar alone): d 0, both inked, greys 174 apart. Two flat hashes now also need their greys to agree
    const beige = await sharp({ create: { width: 900, height: 600, channels: 3, background: '#d9cdb8' } })
      .png()
      .toBuffer();
    expect((await scan({ 'media/house/canvas-beige.png': beige })).findings).toEqual([]);
    // and a flat copy of a flat picture (the bar's own dark, re-encoded) still matches it
    const dark = await sharp({ create: { width: 400, height: 700, channels: 3, background: '#212121' } })
      .jpeg({ quality: 80 })
      .toBuffer();
    expect((await scan({ 'media/x/dark.jpg': dark })).findings.map((f) => [f.rule, f.variant])).toEqual([['A', 'this vs the picture trimmed']]);
    rmSync(site, { recursive: true, force: true });
  });
});

// ---------------------------------------------------------------- ה14
describe('QA note ה14: more ways a card denies a texture', () => {
  const T = 'הדפס במרקם';
  it('QA’s 20 new denials (the 11 it found missed, and the 9 already read) are a print', () => {
    const denials = [
      'print w/o texture',
      'printed canvas w/o embossing',
      'print, texture-less',
      'print, texture: N/A',
      'printed poster, Texture: Smooth',
      'print, texture: flat',
      'Printed: Yes; Embossed: N',
      'print, Textured: False',
      'print, isnt textured',
      'print, doesnt have texture',
      'printed poster (texture? no)',
      'print, isn’t textured',
      'print ‒ not textured',
      'PRINT, NOT TEXTURED',
      'print; non‑textured',
      'printed canvas: untextured',
      'print with zero texture',
      'print – no embossing',
      'הדפס, ללא מרקם (printed, texture: none)',
      'print, embossing: none',
      // a few more of the same kinds
      'textureless print',
      'print, dont have embossing',
      'print (Embossed: No)',
      'print, Texture = 0',
      'print, texture: n/a, frame: none',
    ];
    const missed = denials.filter((s) => materialHe(s) === T);
    expect(missed).toEqual([]);
    for (const s of denials) expect(materialHe(s), s).not.toBeNull();
  });

  it('S17’s 16 denials stay a print; the 12 claims stay "הדפס במרקם"; the 4 the clause rule gives up stay given up', () => {
    const deny17 = [
      'non-textured print',
      'smooth print (no texture)',
      'nontextured printed canvas',
      'printed poster, not embossed',
      'print without any texture',
      'Print, NO TEXTURE',
      'print with no embossed texture',
      'printed, no raised or embossed texture',
      'print; neither textured nor embossed',
      "print (isn't textured)",
      'flat print, texture: none',
      'texture-free print',
      'print, no 3D texture',
      'print with no visible texture',
      'printed panel, lacks texture',
      'print without embossed or textured finish',
    ];
    for (const s of deny17) expect(materialHe(s), s).not.toBe(T);
    const claims = [
      'printed embossed film',
      'textured print, no gloss',
      'embossed print, not framed',
      'print with raised texture, no frame',
      'non-slip backing, textured print',
      'textured canvas print (not glossy)',
      'textured canvas print',
      '3D embossed print',
      'unframed embossed print',
      'printed embossed film / texture painting',
      'Painting material: embossed film, printed',
      'frameless textured print',
      // a texture given a value that claims it is a claim
      'print, Texture: embossed',
      'print, Embossed: Yes',
      'print, texture: raised oil strokes',
    ];
    for (const s of claims) expect(materialHe(s), s).toBe(T);
    for (const s of ['non-fading embossed print', 'textured print that is not glossy', 'embossed print without frame', 'non-slip textured print'])
      expect(materialHe(s), s).not.toBe(T);
  });
});

// ---------------------------------------------------------------- ה15
describe('QA note ה15: the gate says what it does not catch', () => {
  it('the gate’s header and the check’s own words name the five known limits', () => {
    const header = readFileSync(sitePath('tools/lib/rights-content.ts'), 'utf8').split('*/')[0]!;
    const check = readFileSync(sitePath('tools/check-image-rights.ts'), 'utf8');
    for (const limit of [
      /crop into the picture/,
      /rotation/,
      /upside-down/,
      /flip combined with a change of colour|flip with a change of colour/,
      /tile of a collage/,
    ]) {
      expect(header, String(limit)).toMatch(limit);
      expect(check, String(limit)).toMatch(limit);
    }
    expect(header).toMatch(/R9c/);
    expect(header).toMatch(/R21/);
  });
});
