/**
 * S19, the fixes of QA S17 (briefs/site-s19-qa-fixes-2026-11-12.md), the build's side:
 * - ת50: the near-miss rule (B) only when both 32×32 grey images carry ink (mean of 255 − grey ≥ 4).
 * - ת51: each supplier picture is also hashed mirrored; every picture also with its uniform margins trimmed; a fixed list
 *   of supplier picture domains beside the cards' hosts; a data: URI read as a browser reads it.
 * - QA note ה8: "הדפס במרקם" only when a clause claims the texture with no negation word, and the build lists every one
 *   with the card's text.
 * First on pictures made here (always), then on the real files when this machine has them.
 */
import { describe, expect, it, beforeAll } from 'vitest';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import sharp from 'sharp';
import {
  DhashCache,
  LEDGER_SHOP,
  NEAR_MAX_HAMMING,
  NEAR_MAX_MAD32,
  NEAR_MIN_INK,
  SUPPLIER_IMAGE_DOMAINS,
  dataUris,
  fingerprint,
  fingerprintVariants,
  hamming,
  hostPattern,
  inkOf,
  mad32,
  pictureHosts,
  pixelRule,
  prepare,
  readLedger,
  scanBuild,
  sha256,
  supplierSet,
  trimBox,
  type Fingerprint,
  type Ledger,
} from '../lib/rights-content';
import { NEGATION_WORD, materialHe, textureClaimSources } from '../lib/hebrew';
import { GENERATED, SITE, repoPath, sitePath } from '../lib/paths';

const tmp = (name: string) => mkdtempSync(join(tmpdir(), `hd-s19-${name}-`));
const put = (root: string, rel: string, b: Buffer | string) => {
  mkdirSync(join(root, rel, '..'), { recursive: true });
  writeFileSync(join(root, rel), b);
};
const white = (w: number, h: number) => sharp({ create: { width: w, height: h, channels: 3, background: '#ffffff' } });
/** a product photographed on white: a structured object in the middle of a white frame (margins on every side) */
async function product(seed: number, w = 800, h = 800): Promise<Buffer> {
  let s = seed;
  const rnd = () => ((s = (s * 1103515245 + 12345) % 2 ** 31) / 2 ** 31) * 200;
  const ow = Math.round(w * 0.5);
  const oh = Math.round(h * 0.62);
  const raw = Buffer.alloc(ow * oh * 3);
  const B = 30;
  const cells = Array.from({ length: Math.ceil(ow / B) * Math.ceil(oh / B) }, () => [rnd(), rnd(), rnd()]);
  for (let y = 0; y < oh; y++)
    for (let x = 0; x < ow; x++) {
      const c = cells[Math.floor(y / B) * Math.ceil(ow / B) + Math.floor(x / B)]!;
      raw.set([c[0]!, c[1]!, c[2]!], (y * ow + x) * 3);
    }
  const obj = await sharp(raw, { raw: { width: ow, height: oh, channels: 3 } })
    .blur(2)
    .png()
    .toBuffer();
  return white(w, h)
    .composite([{ input: obj, left: Math.round((w - ow) / 2), top: Math.round((h - oh) * 0.45) }])
    .png()
    .toBuffer();
}
/** QA's near-blank supplier picture: a thin floor lamp on white (its mean ink 2.2 of 255) */
async function thinLamp(): Promise<Buffer> {
  const stem = await sharp({ create: { width: 6, height: 560, channels: 3, background: '#2a2a2a' } })
    .png()
    .toBuffer();
  const shade = await sharp({ create: { width: 70, height: 50, channels: 3, background: '#d8d0c4' } })
    .png()
    .toBuffer();
  // as the supplier's JPEG has it: the compression's noise round the stem is what puts it 25–48 bits from a blank
  return white(800, 800)
    .composite([
      { input: stem, left: 397, top: 160 },
      { input: shade, left: 365, top: 120 },
    ])
    .jpeg({ quality: 60 })
    .toBuffer();
}
const prep = (f: Fingerprint | null | undefined) => prepare(f!);

/** a site with one withheld supplier picture (and its ledger), and a scan of a public build made by `mutate` */
async function siteWith(supplier: Buffer, product = 'holder-x', o: { asIs?: boolean } = {}) {
  const site = tmp('site');
  const file = `web/public/media/products/${product}/opt-0123456789.800.${o.asIs ? 'jpg' : 'webp'}`;
  const bytes = o.asIs ? supplier : await sharp(supplier).webp({ quality: 82 }).toBuffer();
  put(site, file, bytes);
  const ledgers: Ledger[] = [
    {
      generated_at: 'now',
      source: 'shop+cache',
      entries: [{ file, sha256: sha256(bytes), product, rights: 'unclear', source: 'shop', picture: `products/${product}/opt-0123456789`, width: 800 }],
    },
  ];
  const scan = async (mutate: (dist: string) => Promise<void> | void, hosts: string[] = ['ae01.alicdn.com']) => {
    const dist = tmp('dist');
    put(dist, 'index.html', '<!doctype html><html lang="he"><head><title>x</title></head><body></body></html>');
    await mutate(dist);
    const dh = new DhashCache();
    const set = await supplierSet({ site, ledgers, cacheDir: join(site, '.cache/supplier-images'), hosts, dhashes: dh });
    const r = await scanBuild(dist, set, dh);
    rmSync(dist, { recursive: true, force: true });
    return r.findings;
  };
  return { site, bytes, scan };
}

// ---------------------------------------------------------------- ת50
describe('ת50: the near miss only when both pictures carry ink', () => {
  it('the rule on fingerprints: a near miss with ink on both sides is B; with a near-blank side it is nothing', () => {
    const grey = (v: number) => Buffer.alloc(1024, v);
    const bits = (n: number) => {
      const b = Buffer.alloc(32);
      for (let i = 0; i < n; i++) b[i >> 3]! |= 1 << (7 - (i & 7));
      return b.toString('hex');
    };
    const a = prepare({ dhash: bits(0), grey: grey(250) }); // ink 5
    const b = prepare({ dhash: bits(30), grey: grey(251) }); // ink 4, 30 bits away, MAD 1
    const blank = prepare({ dhash: bits(30), grey: grey(254) }); // ink 1
    expect([a.ink, b.ink, blank.ink]).toEqual([5, 4, 1]);
    expect(pixelRule(a, b)).toMatchObject({ d: 30, m: 1, rule: 'B' });
    expect(pixelRule(a, blank)).toMatchObject({ d: 30, rule: null });
    expect(pixelRule(blank, a)).toMatchObject({ rule: null });
    // A is unchanged: within 24 bits it matches whatever the ink
    expect(pixelRule(prepare({ dhash: bits(0), grey: grey(255) }), prepare({ dhash: bits(20), grey: grey(255) }))).toMatchObject({ rule: 'A' });
    // beyond 48 bits there is no near miss at all
    expect(pixelRule(a, prepare({ dhash: bits(NEAR_MAX_HAMMING + 1), grey: grey(250) }))).toMatchObject({ m: null, rule: null });
    expect(NEAR_MIN_INK).toBe(4);
    // a mirrored or trimmed form (`inkForA`): A too needs ink on both sides
    expect(pixelRule(prepare({ dhash: bits(0), grey: grey(255) }), prepare({ dhash: bits(20), grey: grey(254) }), 24, { inkForA: true })).toMatchObject({
      rule: null,
    });
    expect(pixelRule(a, prepare({ dhash: bits(20), grey: grey(250) }), 24, { inkForA: true })).toMatchObject({ rule: 'A' });
  });

  it('QA’s near-blank pictures against a thin lamp on white: white, transparent, a dot and a mostly transparent layer find nothing (the S17 rule matched them)', async () => {
    const lamp = await thinLamp();
    // the supplier's own JPEG, as the cache holds it
    const { scan } = await siteWith(lamp, 'floor-lamp-thin', { asIs: true });
    const lampFp = prep(await fingerprint(lamp));
    expect(lampFp.ink).toBeLessThan(NEAR_MIN_INK);
    const blanks: Record<string, Buffer> = {
      'white.png': await white(1000, 1000).png().toBuffer(),
      'transparent.png': await sharp({ create: { width: 1000, height: 1000, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } })
        .png()
        .toBuffer(),
      'dot.png': await white(800, 800)
        .composite([
          {
            input: await sharp({ create: { width: 40, height: 40, channels: 3, background: '#333333' } })
              .png()
              .toBuffer(),
            left: 380,
            top: 380,
          },
        ])
        .png()
        .toBuffer(),
      // a house layer: a small product on a transparent canvas, as media/house/…/1.product.1920.webp is
      'layer.webp': await sharp({ create: { width: 1920, height: 1080, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } })
        .composite([
          {
            input: await sharp({ create: { width: 60, height: 90, channels: 4, background: { r: 60, g: 50, b: 40, alpha: 1 } } })
              .png()
              .toBuffer(),
            left: 1400,
            top: 700,
          },
        ])
        .webp({ quality: 82, alphaQuality: 90 })
        .toBuffer(),
    };
    let s17Matches = 0;
    for (const b of Object.values(blanks)) {
      const f = prep(await fingerprint(b));
      const d = hamming(f.dhash, lampFp.dhash);
      if (d > 24 && d <= NEAR_MAX_HAMMING && mad32(f.grey, lampFp.grey) <= NEAR_MAX_MAD32) s17Matches++;
    }
    // the S17 rule (no ink guard) matched most of them; QA saw white, transparent and the dot match by B
    expect(s17Matches).toBeGreaterThanOrEqual(3);
    const found = await scan((d) => {
      for (const [n, b] of Object.entries(blanks)) put(d, `media/house/living-room/warm-modern/M0/slots/x/${n}`, b);
    });
    expect(found).toEqual([]);
  });

  it('a copy that carries ink is still caught: a 96 px copy inlined in a script, a half-size JPEG', async () => {
    const photo = await product(11);
    const { scan } = await siteWith(photo);
    const found = await scan(async (d) => {
      put(
        d,
        'assets/index-abc.js',
        `export const t="data:image/webp;base64,${(await sharp(photo).resize(96).webp({ quality: 60 }).toBuffer()).toString('base64')}";`,
      );
      put(d, 'media/og/look-7.jpg', await sharp(photo).resize(400).jpeg({ quality: 60 }).toBuffer());
    });
    expect(found.map((x) => x.how).sort()).toEqual(['data-uri pixels', 'pixels']);
  });

  const LAYERS = repoPath('assets/renders/living-room/warm-modern/phase2-2026-11-10/layers');
  const DEMO = [
    'accent-sconces/accent-sconces-cj-travertine-block-updown-8x16-r5.png',
    'accent-sconces/accent-sconces-cj-travertine-block-updown-8x16-r5-shadow.png',
    'bowl/bowl-cj-matte-black-bowl-20.png',
    'bowl/bowl-cj-matte-black-bowl-20-shadow.png',
  ];
  const REAL = existsSync(join(GENERATED, LEDGER_SHOP)) && DEMO.every((f) => existsSync(join(LAYERS, f)));
  it.skipIf(!REAL)('QA’s gate demo on the real set: our four phase-2 layers as house layers in a public build find nothing', { timeout: 240_000 }, async () => {
    const dh = new DhashCache(sitePath('.cache/rights-dhash.json'));
    const set = await supplierSet({
      site: SITE,
      ledgers: [readLedger(join(GENERATED, LEDGER_SHOP))!],
      cacheDir: sitePath('.cache/supplier-images'),
      hosts: [],
      dhashes: dh,
    });
    // the supplier picture behind QA's 124 false matches is near blank
    const lamp = set.pixels.find((p) => p.picture === 'products/floor-lamp-black-drum-linen-uaeow/opt-06334f443d' && p.variant === 'plain');
    if (lamp) expect(lamp.ink).toBeLessThan(NEAR_MIN_INK);
    const d = tmp('demo');
    for (const [i, f] of DEMO.entries())
      put(
        d,
        `media/house/living-room/warm-modern/M0/slots/s${i}/1.${f.includes('shadow') ? 'shadow' : 'product'}.1920.webp`,
        await sharp(join(LAYERS, f)).resize(1920).webp({ quality: 82, alphaQuality: 90 }).toBuffer(),
      );
    const r = await scanBuild(d, set, dh);
    dh.save();
    rmSync(d, { recursive: true, force: true });
    expect(r.findings).toEqual([]);
    expect(r.stats.rasters).toBe(4);
  });
});

// ---------------------------------------------------------------- ת51
describe('ת51: mirrored, trimmed, the fixed domains, and a data: URI read as a browser reads it', () => {
  let photo: Buffer = Buffer.alloc(0);
  let scan: Awaited<ReturnType<typeof siteWith>>['scan'];
  beforeAll(async () => {
    photo = await product(23);
    ({ scan } = await siteWith(photo));
  });

  it('the trim: a frame of one colour, then the white inside it; nothing on a picture without margins; nothing left of a blank', () => {
    const W = 100;
    const g = new Uint8Array(W * W).fill(200); // a grey border …
    for (let y = 5; y < 95; y++) for (let x = 5; x < 95; x++) g[y * W + x] = 255; // … white inside it …
    for (let y = 30; y < 70; y++) for (let x = 40; x < 60; x++) g[y * W + x] = 40; // … and the product
    expect(trimBox(g, W, W)).toEqual({ left: 40, top: 30, width: 20, height: 40 });
    expect(
      trimBox(
        new Uint8Array(W * W).map((_, i) => i % 251),
        W,
        W,
      ),
    ).toBeNull();
    expect(trimBox(new Uint8Array(W * W).fill(255), W, W)).toBeNull();
  });

  it('the variants of a picture: the mirror of a picture is the mirrored variant; a picture without margins has no trimmed one', async () => {
    const v = await fingerprintVariants(photo, ['plain', 'mirrored', 'trimmed', 'trimmed-mirrored']);
    const flopped = (await fingerprint(await sharp(photo).flop().png().toBuffer()))!;
    expect(hamming(flopped.dhash, v.mirrored!.dhash)).toBeLessThanOrEqual(4);
    expect(hamming(flopped.dhash, v.plain!.dhash)).toBeGreaterThan(24);
    expect(v.trimmed).not.toBeNull();
    expect(inkOf(v.trimmed!.grey)).toBeGreaterThan(inkOf(v.plain!.grey));
    const full = await sharp(photo).extract({ left: 200, top: 150, width: 400, height: 496 }).png().toBuffer();
    expect((await fingerprintVariants(full, ['trimmed'])).trimmed).toBeNull();
  });

  it('QA’s R9 (flipped), padding onto white 4:3, a grey 3% border, and a crop that cuts only margin: each found', async () => {
    const cases: Record<string, Buffer> = {
      'flip.webp': await sharp(photo).flop().webp().toBuffer(),
      'pad.webp': await sharp(photo).extend({ left: 230, right: 230, top: 30, bottom: 30, background: '#ffffff' }).webp().toBuffer(),
      'border.webp': await sharp(photo).extend({ left: 24, right: 24, top: 24, bottom: 24, background: '#c8c8c8' }).webp().toBuffer(),
      'crop.webp': await sharp(photo).extract({ left: 80, top: 80, width: 640, height: 640 }).webp().toBuffer(),
      'flip-pad.webp': await sharp(photo).flop().extend({ left: 120, right: 120, top: 0, bottom: 0, background: '#ffffff' }).webp().toBuffer(),
    };
    for (const [n, b] of Object.entries(cases)) {
      const f = await scan((d) => put(d, `media/journal/${n}`, b));
      expect(
        f.map((x) => x.how),
        n,
      ).toEqual(['pixels']);
    }
    // a crop into the product itself is still the limit of a dHash: not claimed here
  });

  it('the fixed supplier domains: a hotlink to ae-pic-a1.aliexpress-media.com is found though no card names it (QA’s R14)', async () => {
    expect([...SUPPLIER_IMAGE_DOMAINS]).toEqual(['alicdn.com', 'aliexpress-media.com', 'aliexpress.com', 'cjdropshipping.com', 'zendrop.com']);
    const hosts = pictureHosts([{ images: { urls: ['https://www.rihut-express.co.il/a.jpg'] } }]);
    expect(hosts).toContain('www.rihut-express.co.il');
    const re = hostPattern(hosts)!;
    const text =
      'https://ae-pic-a1.aliexpress-media.com/kf/S1.jpg //ae04.alicdn.com/x.jpg https://www.aliexpress.com/item/1.html cf.cjdropshipping.com file.zendrop.com';
    expect(text.match(re)).toEqual(['ae-pic-a1.aliexpress-media.com', 'ae04.alicdn.com', 'www.aliexpress.com', 'cf.cjdropshipping.com', 'file.zendrop.com']);
    expect('https://example.com/aliexpressmedia.com /media/rooms/a.webp'.match(re)).toBeNull();
    const f = await scan(
      (d) => put(d, 'p/x/index.html', '<!doctype html><head><meta property="og:image" content="https://ae-pic-a1.aliexpress-media.com/kf/S1e.jpg"></head>'),
      pictureHosts([]),
    );
    expect(f.map((x) => [x.where, x.how])).toEqual([['p/x/index.html', 'host']]);
  });

  it('QA’s R15: a data: URI in CSS broken by escaped line breaks is decoded and found; so are whitespace, percent escapes and references inside one', async () => {
    const b64 = (await sharp(photo).resize(300).jpeg({ quality: 70 }).toBuffer()).toString('base64');
    const css = `.qa-hero{background-image:url("data:image/jpeg;base64,${b64.replace(/(.{76})/g, '$1\\\n')}")}`;
    expect(dataUris(css).map((d) => d.b64)).toContain(b64);
    const html = `<img src="data:image/jpeg;base64,${b64
      .replace(/(.{60})/g, '$1\n  ')
      .replace(/\+/g, '%2B')
      .replace(/\//g, '&#47;')}" alt="">`;
    expect(dataUris(html).map((d) => d.b64)).toContain(b64);
    // a word after the URI (srcset's "1x") does not spoil it: the strict run is kept too
    const srcset = `srcset="data:image/jpeg;base64,${b64} 1x"`;
    expect(dataUris(srcset).map((d) => d.b64)).toContain(b64);
    for (const [n, text] of [
      ['assets/a.css', css],
      ['p/y/index.html', html],
    ]) {
      const f = await scan((d) => put(d, n!, text!));
      expect(
        f.map((x) => x.how),
        n,
      ).toEqual(['data-uri pixels']);
    }
  });
});

// ---------------------------------------------------------------- ה8
describe('ה8: "הדפס במרקם" only when a clause claims the texture with no negation word', () => {
  /** QA's phrasings (qa/reports/2026-11-12-site-track-qa-s17/tools/negation-probe.ts) */
  const DENY = [
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
  const CLAIM = [
    'printed embossed film',
    'textured print, no gloss',
    'embossed print, not framed',
    'print with raised texture, no frame',
    'non-slip backing, textured print',
    'textured canvas print (not glossy)',
    "printed embossed film / 'texture painting' panel (supplier: 'Painting material: embossed film')",
  ];
  it('QA’s 16 denials are a print; the 6 claims and the card’s own text stay "הדפס במרקם"', () => {
    expect(DENY.filter((s) => materialHe(s) !== 'הדפס')).toEqual([]);
    expect(CLAIM.filter((s) => materialHe(s) !== 'הדפס במרקם')).toEqual([]);
  });
  it('the negation words, in English and Hebrew; a clause that claims and denies says the less', () => {
    for (const w of ['no', 'not', 'non-slip', 'none', 'neither', 'nor', 'without', 'lacks', 'free', "isn't", 'doesn’t', 'ללא', 'בלי', 'לא'])
      expect(NEGATION_WORD.test(`x ${w} y`), w).toBe(true);
    for (const w of ['note', 'nonce', 'notebook', 'nordic', 'freely', 'לאה']) expect(NEGATION_WORD.test(`x ${w} y`), w).toBe(false);
    expect(materialHe('non-slip textured print')).toBe('הדפס');
    expect(textureClaimSources(['cotton', 'textured print, no gloss', 'print, no texture'])).toEqual(['textured print, no gloss']);
  });

  const LIST = join(GENERATED, 'catalog.texture-claims.json');
  it.skipIf(!existsSync(LIST))('the build lists every "הדפס במרקם" of the catalog with the card’s text it was read from', () => {
    const list = JSON.parse(readFileSync(LIST, 'utf8')) as { claims: { product: string; from: string[] }[] };
    const full = JSON.parse(readFileSync(join(GENERATED, 'catalog.full.json'), 'utf8')) as { products: { id: string; materials_he: string[] }[] };
    expect(list.claims.map((c) => c.product).sort()).toEqual(
      full.products
        .filter((p) => p.materials_he.includes('הדפס במרקם'))
        .map((p) => p.id)
        .sort(),
    );
    for (const c of list.claims) {
      expect(c.from.length, c.product).toBeGreaterThan(0);
      for (const t of c.from) expect(materialHe(t), t).toBe('הדפס במרקם');
    }
  });
});
