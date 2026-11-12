/**
 * S17, QA ת45: the image-rights gate by content (tools/lib/rights-content.ts, tools/check-image-rights.ts).
 *
 * QA's mutations of a public build (qa/reports/2026-11-11-site-track-qa-s15-s16/tools/mut-rights.sh), each of which the
 * S15 gate passed (R2–R4, R6) and each of which must now fail it:
 *   R1  the picture at its own path                    (the path rule, and now its bytes)
 *   R2  the same bytes under another name, as og:image (bytes)
 *   R3  og:image hotlinked to the supplier's CDN       (host)
 *   R4  the picture inlined as a data: URI              (data-URI bytes; re-encoded: data-URI pixels)
 *   R6  the story's own copies of supplier pictures    (bytes by the story's ledger; without it, pixels alone)
 * First on pictures made here (always), then on the real supplier pictures and the real CLI, when the build's ledger
 * and the cache are on this machine (a fresh checkout before `npm run prepare:data` has neither).
 */
import { describe, expect, it, beforeAll } from 'vitest';
import { spawnSync } from 'node:child_process';
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, relative } from 'node:path';
import sharp from 'sharp';
import {
  DhashCache,
  LEDGER_SHOP,
  LEDGER_STORY,
  PIXEL_MAX_HAMMING,
  cardPictureHosts,
  dhash,
  hamming,
  hostPattern,
  readCards,
  readLedger,
  registrableDomain,
  scanBuild,
  sha256,
  supplierSet,
  type Ledger,
} from '../lib/rights-content';
import { GENERATED, SITE, repoPath, sitePath } from '../lib/paths';

/** a picture with structure (blocks of grey at random), as a supplier photo or a render would have */
async function picture(seed: number, w = 640, h = 640): Promise<Buffer> {
  let s = seed;
  const rnd = () => ((s = (s * 1103515245 + 12345) % 2 ** 31) / 2 ** 31) * 255;
  const raw = Buffer.alloc(w * h * 3);
  const B = 40;
  const cells = Array.from({ length: Math.ceil(w / B) * Math.ceil(h / B) }, () => [rnd(), rnd(), rnd()]);
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      const c = cells[Math.floor(y / B) * Math.ceil(w / B) + Math.floor(x / B)]!;
      raw.set([c[0]!, c[1]!, c[2]!], (y * w + x) * 3);
    }
  return sharp(raw, { raw: { width: w, height: h, channels: 3 } })
    .blur(3)
    .png()
    .toBuffer();
}
const webp = (b: Buffer, w: number, q = 80) => sharp(b).resize({ width: w }).webp({ quality: q }).toBuffer();

const tmp = (name: string) => mkdtempSync(join(tmpdir(), `hd-s17-${name}-`));
const put = (root: string, rel: string, b: Buffer | string) => {
  mkdirSync(join(root, rel, '..'), { recursive: true });
  writeFileSync(join(root, rel), b);
};
const PAGE = '<!doctype html><html lang="he"><head><title>מחזיק</title></head><body><main><h1>מחזיק</h1></main></body></html>';
const withHead = (html: string, tag: string) => html.replace('</head>', `${tag}</head>`);
const withBody = (html: string, tag: string) => html.replace('</body>', `${tag}</body>`);

describe('ת45: the pieces', () => {
  it('dHash: one picture at any width and quality is within the threshold; two pictures are far apart', async () => {
    const a = await picture(1);
    const b = await picture(2);
    const ha = (await dhash(a))!;
    expect(ha).toMatch(/^[0-9a-f]{64}$/);
    for (const w of [160, 480, 800]) expect(hamming(ha, (await dhash(await webp(a, w, 60)))!)).toBeLessThanOrEqual(PIXEL_MAX_HAMMING);
    expect(hamming(ha, (await dhash(b))!)).toBeGreaterThan(PIXEL_MAX_HAMMING * 2);
    expect(await dhash(Buffer.from('not a picture'))).toBeNull();
  });
  it('the hosts of the cards’ pictures, and their domains (a sibling CDN host is caught too)', () => {
    const cards = [
      { images: { urls: ['https://ae01.alicdn.com/kf/a.jpg'] }, supplier: { product_url: 'https://www.aliexpress.com/item/1.html' } },
      { options: { skus: [{ image: 'https://oss-cf.cjdropshipping.com/x.png' }] }, certificates: [{ url: 'https://example.org/c.pdf' }] },
    ];
    const hosts = cardPictureHosts(cards);
    expect(hosts).toEqual(['ae01.alicdn.com', 'oss-cf.cjdropshipping.com']);
    expect(registrableDomain('www.rihut-express.co.il')).toBe('rihut-express.co.il');
    const re = hostPattern(hosts)!;
    expect('<img src="https://ae04.alicdn.com/kf/b.jpg">'.match(re)).toEqual(['ae04.alicdn.com']);
    expect('//cf.cjdropshipping.com/y.jpg'.match(re)).toEqual(['cf.cjdropshipping.com']);
    expect('https://notalicdn.com/x https://alicdn.com.example.org/'.match(re)).toEqual(['alicdn.com']);
    expect('https://fonts.gstatic.com/s/x.woff2 /media/rooms/a.webp'.match(re)).toBeNull();
  });
});

describe('ת45: QA’s mutations on pictures made here', () => {
  let site = '';
  let supplier: Buffer = Buffer.alloc(0);
  let story480: Buffer = Buffer.alloc(0);
  let render: Buffer = Buffer.alloc(0);
  let ledgers: Ledger[] = [];
  const hosts = ['ae01.alicdn.com'];
  beforeAll(async () => {
    site = tmp('site');
    const original = await picture(7, 900, 900);
    supplier = await webp(original, 800);
    story480 = await webp(original, 480, 78);
    render = await webp(await picture(99, 1280, 720), 1280);
    put(site, '.cache/supplier-images/aaaaaaaaaaaaaaaaaaaaaaaa.bin', original);
    put(site, 'web/public/media/products/holder-x/opt-0123456789.800.webp', supplier);
    put(site, 'web/public/media/story/products/holder-x/0123456789.480.webp', story480);
    const confirmed = await webp(await picture(5), 800);
    put(site, 'web/public/media/products/vase-ok/photo.800.webp', confirmed);
    const e = (
      file: string,
      b: Buffer,
      rights: 'unclear' | 'confirmed',
      source: 'shop' | 'story' | 'cache',
      picture: string,
      product = 'holder-x',
      width?: number,
    ) => ({
      file,
      sha256: sha256(b),
      product,
      rights,
      source,
      picture,
      width,
    });
    ledgers = [
      {
        generated_at: 'now',
        source: 'shop+cache',
        entries: [
          e('web/public/media/products/holder-x/opt-0123456789.800.webp', supplier, 'unclear', 'shop', 'products/holder-x/opt-0123456789', 'holder-x', 800),
          e('.cache/supplier-images/aaaaaaaaaaaaaaaaaaaaaaaa.bin', original, 'unclear', 'cache', '.cache/supplier-images/aaaaaaaaaaaaaaaaaaaaaaaa.bin'),
          e('web/public/media/products/vase-ok/photo.800.webp', confirmed, 'confirmed', 'shop', 'products/vase-ok/photo', 'vase-ok', 800),
        ],
      },
      {
        generated_at: 'now',
        source: 'story',
        entries: [
          e(
            'web/public/media/story/products/holder-x/0123456789.480.webp',
            story480,
            'unclear',
            'story',
            'story/products/holder-x/0123456789',
            'holder-x',
            480,
          ),
        ],
      },
    ];
  });
  /** a public build: a page, a render, and the one mutation */
  async function run(mutate: (dist: string) => Promise<void> | void, o: { story?: boolean } = {}) {
    const dist = tmp('dist');
    put(dist, 'p/holder-x/index.html', PAGE);
    put(dist, 'media/rooms/living-room/nordic/base.1280.webp', render);
    await mutate(dist);
    const dh = new DhashCache();
    const set = await supplierSet({
      site,
      ledgers: o.story === false ? [ledgers[0]!] : ledgers,
      cacheDir: join(site, '.cache/supplier-images'),
      hosts,
      dhashes: dh,
    });
    const r = await scanBuild(dist, set, dh);
    rmSync(dist, { recursive: true, force: true });
    return r.findings;
  }
  const page = (dist: string) => join(dist, 'p/holder-x/index.html');

  it('R0, the clean build: a render and a page find nothing', async () => {
    expect(await run(() => undefined)).toEqual([]);
  });
  it('R1, the picture at its own path: found by its bytes', async () => {
    const f = await run((d) => put(d, 'media/products/holder-x/opt-0123456789.800.webp', supplier));
    expect(f.map((x) => [x.where, x.how])).toEqual([['media/products/holder-x/opt-0123456789.800.webp', 'bytes']]);
  });
  it('R2, the same bytes under another name, as og:image: found by its bytes', async () => {
    const f = await run((d) => {
      put(d, 'media/og/look-1.webp', supplier);
      writeFileSync(page(d), withHead(PAGE, '<meta property="og:image" content="https://example.co.il/media/og/look-1.webp">'));
    });
    expect(f.map((x) => [x.where, x.how])).toEqual([['media/og/look-1.webp', 'bytes']]);
  });
  it('R2b, the original from the cache under a picture’s name: its bytes', async () => {
    const f = await run((d) => put(d, 'media/og/look-2.jpg', readFileSync(join(site, '.cache/supplier-images/aaaaaaaaaaaaaaaaaaaaaaaa.bin'))));
    expect(f.map((x) => x.how)).toEqual(['bytes']);
  });
  it('R3, og:image hotlinked to the supplier’s CDN (and a sibling host of it): found by host', async () => {
    const f = await run((d) =>
      writeFileSync(
        page(d),
        withHead(PAGE, '<meta property="og:image" content="https://ae01.alicdn.com/kf/S1e343.jpg"><link rel="preload" href="//ae04.alicdn.com/kf/x.jpg">'),
      ),
    );
    expect(f.map((x) => [x.where, x.how])).toEqual([
      ['p/holder-x/index.html', 'host'],
      ['p/holder-x/index.html', 'host'],
    ]);
  });
  it('R4, the picture inlined as a data: URI: its bytes; re-encoded smaller, its pixels', async () => {
    const f = await run((d) => writeFileSync(page(d), withBody(PAGE, `<img alt="" src="data:image/webp;base64,${supplier.toString('base64')}">`)));
    expect(f.map((x) => x.how)).toEqual(['data-uri bytes']);
    const small = await webp(supplier, 96, 50);
    const g = await run((d) => put(d, 'assets/index-abc.js', `const a="data:image/webp;base64,${small.toString('base64')}";`));
    expect(g.map((x) => x.how)).toEqual(['data-uri pixels']);
    expect(g[0]!.hamming).toBeLessThanOrEqual(PIXEL_MAX_HAMMING);
  });
  it('R6, the story’s own copies: by the story’s ledger; and without any ledger of them, by pixels at every width', async () => {
    const f = await run((d) => put(d, 'media/story/products/holder-x/0123456789.480.webp', story480));
    expect(f.map((x) => x.how)).toEqual(['bytes']);
    const g = await run(
      async (d) => {
        for (const w of [160, 480, 800]) put(d, `media/story/products/holder-x/k.${w}.webp`, await webp(supplier, w, 78));
        // a renamed copy, re-encoded under another type (a crop or a mirror is not covered: the limit of a dHash)
        put(d, 'media/look/a.png', await sharp(supplier).resize({ width: 700 }).png().toBuffer());
      },
      { story: false },
    );
    expect(g.map((x) => [x.where, x.how])).toEqual([
      ['media/look/a.png', 'pixels'],
      ['media/story/products/holder-x/k.160.webp', 'pixels'],
      ['media/story/products/holder-x/k.480.webp', 'pixels'],
      ['media/story/products/holder-x/k.800.webp', 'pixels'],
    ]);
  });
  it('a picture whose rights are confirmed may ship, under any name', async () => {
    const ok = readFileSync(join(site, 'web/public/media/products/vase-ok/photo.800.webp'));
    expect(await run((d) => put(d, 'media/og/vase.webp', ok))).toEqual([]);
  });
  it('a cached original no ledger names may not ship (its rights are unknown)', async () => {
    const stray = await picture(31);
    put(site, '.cache/supplier-images/bbbbbbbbbbbbbbbbbbbbbbbb.bin', stray);
    const f = await run((d) => put(d, 'media/og/stray.webp', stray));
    rmSync(join(site, '.cache/supplier-images/bbbbbbbbbbbbbbbbbbbbbbbb.bin'));
    expect(f.map((x) => [x.how, x.what.includes('rights: unknown')])).toEqual([['bytes', true]]);
  });
  it('a picture inside an inlined SVG, and a hotlink inside one', async () => {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg"><image href="data:image/webp;base64,${supplier.toString('base64')}"/><image href="https://ae01.alicdn.com/kf/z.jpg"/></svg>`;
    const f = await run((d) => put(d, 'assets/a.css', `.x{background:url("data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}")}`));
    expect(f.map((x) => x.how).sort()).toEqual(['data-uri bytes', 'host']);
  });
});

// ---------------------------------------------------------------- the real pictures and the real CLI
const REAL = existsSync(join(GENERATED, LEDGER_SHOP)) && existsSync(sitePath('.cache/supplier-images'));
const STORY_DIR = sitePath('web/public/media/story/products');
const tsx = sitePath('node_modules/tsx/dist/cli.mjs');

describe.skipIf(!REAL)('ת45: QA’s mutations on the real supplier pictures (the build’s ledgers and cache)', () => {
  const shop = REAL ? readLedger(join(GENERATED, LEDGER_SHOP))! : null;
  /** QA's picture: an option picture of a withheld product */
  const pick = () => shop!.entries.find((e) => e.source === 'shop' && e.rights !== 'confirmed' && /\/opt-/.test(e.file) && existsSync(join(SITE, e.file)))!;
  const cardUrl = () => {
    const urls = readCards(repoPath('data/products')).flatMap((c) => (c as { images?: { urls?: string[] } }).images?.urls ?? []);
    return urls.find((u) => /ae01\.alicdn\.com/.test(u))!;
  };
  /** the CLI as the build runs it (HD_PUBLIC=1), on a copy instead of web/dist */
  function cli(dist: string, extra: Record<string, string> = {}) {
    const r = spawnSync(process.execPath, [tsx, 'tools/check-image-rights.ts', `--dist=${dist}`], {
      cwd: SITE,
      env: { ...process.env, HD_PUBLIC: '1', ...extra },
      encoding: 'utf8',
      timeout: 170_000,
    });
    return { code: r.status, out: `${r.stdout}${r.stderr}` };
  }
  function dist(mutate: (d: string) => void) {
    const d = tmp('real');
    put(d, 'index.html', PAGE);
    put(d, 'p/holder/index.html', PAGE);
    mutate(d);
    return d;
  }

  it('R0 clean, R1, R2, R3, R4 and R6 through the real check: only the clean copy passes', { timeout: 180_000 }, () => {
    const e = pick();
    const bytes = readFileSync(join(SITE, e.file));
    const cases: [string, (d: string) => void, RegExp | null][] = [
      ['R0', () => undefined, null],
      ['R1', (d) => put(d, `media/products/${e.product}/${e.file.split('/').pop()}`, bytes), /by path|a file of|by bytes/],
      [
        'R2',
        (d) => {
          put(d, 'media/og/look-1.webp', bytes);
          writeFileSync(join(d, 'p/holder/index.html'), withHead(PAGE, '<meta property="og:image" content="https://example.co.il/media/og/look-1.webp">'));
        },
        /media\/og\/look-1\.webp: by bytes/,
      ],
      [
        'R3',
        (d) => writeFileSync(join(d, 'p/holder/index.html'), withHead(PAGE, `<meta property="og:image" content="${cardUrl()}">`)),
        /by host: a URL on a supplier picture host: ae01\.alicdn\.com/,
      ],
      [
        'R4',
        (d) => writeFileSync(join(d, 'p/holder/index.html'), withBody(PAGE, `<img alt="" src="data:image/webp;base64,${bytes.toString('base64')}">`)),
        /by data-uri bytes/,
      ],
    ];
    if (existsSync(STORY_DIR))
      cases.push(['R6', (d) => cpSync(STORY_DIR, join(d, 'media/story/products'), { recursive: true }), /media\/story\/products\/.*by bytes/]);
    for (const [name, mutate, expected] of cases) {
      const d = dist(mutate);
      const r = cli(d);
      rmSync(d, { recursive: true, force: true });
      if (expected) {
        expect(r.code, `${name}: ${r.out.slice(-600)}`).toBe(1);
        expect(r.out, name).toMatch(expected);
      } else expect(r.code, `${name}: ${r.out.slice(-600)}`).toBe(0);
    }
  });

  it.skipIf(!existsSync(STORY_DIR))('R6 by pixels alone: every copy the story made is found without the story’s ledger', { timeout: 180_000 }, async () => {
    const dh = new DhashCache(sitePath('.cache/rights-dhash.json'));
    const set = await supplierSet({
      site: SITE,
      ledgers: [shop!],
      cacheDir: sitePath('.cache/supplier-images'),
      hosts: [],
      dhashes: dh,
    });
    const d = tmp('r6');
    cpSync(STORY_DIR, join(d, 'media/story/products'), { recursive: true });
    const walk = (x: string): string[] => readdirSync(x, { withFileTypes: true }).flatMap((n) => (n.isDirectory() ? walk(join(x, n.name)) : [join(x, n.name)]));
    const copies = walk(d).map((f) => relative(d, f));
    const r = await scanBuild(d, set, dh);
    rmSync(d, { recursive: true, force: true });
    const found = new Set(r.findings.map((f) => f.where));
    const story = readLedger(join(GENERATED, LEDGER_STORY));
    expect(copies.length).toBe(story?.entries.length ?? copies.length);
    expect(copies.filter((c) => !found.has(c))).toEqual([]);
    expect(r.findings.every((f) => f.how === 'pixels' || f.how === 'bytes')).toBe(true);
  });
});
