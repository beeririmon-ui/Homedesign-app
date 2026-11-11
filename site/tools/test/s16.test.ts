/**
 * S16, the fixes of QA S13–S14 on the build side (briefs/site-s16-qa-fixes-2026-11-11.md):
 * - ת41: the public `_redirects` carries no old address that names a supplier (the real catalog).
 * - ת43: the warm-modern poster's WebP fallback is lossy q95 (QA's ruling), its weight; the inlined placeholder (ה1).
 * - ת44: "no lazy page in the room's entry" by content (the chunk graph), QA's mutation caught.
 * - ה7: a deploy cannot skip the deploy check; the exclusions file points to the test that checks it.
 */
import { describe, expect, it } from 'vitest';
import { existsSync, readFileSync, statSync } from 'node:fs';
import sharp from 'sharp';
import { cardRedirects, namesSupplier } from '@hd/shared/product-url';
import { lazyPagesInEntry, lazyPagesMissing, readGraph, staticClosure, type BundleGraph } from '../lib/bundle-graph';
import { repoPath, sitePath } from '../lib/paths';

describe('ת41: the public _redirects names no supplier', () => {
  it('a card id with a supplier, a marketplace or a listing number is recognised; a neutral one is not', () => {
    expect(namesSupplier('vase-aliexpress-vintage-distressed-clay-vase-589009')).toBe(true);
    expect(namesSupplier('cushion-cj-linen-cover')).toBe(true);
    expect(namesSupplier('throw-zendrop-muslin')).toBe(true);
    expect(namesSupplier('lamp-travertine-1005006123456')).toBe(true);
    expect(namesSupplier('cushion-linen-cover-beige')).toBe(false);
    // a word that merely contains a supplier's letters is not one ("cjk", "aerial")
    expect(namesSupplier('print-cjk-aerial-view')).toBe(false);
  });

  const full = sitePath('.generated/catalog.full.json');
  it.runIf(existsSync(full))('the real catalog: behind the flag every old address moves; the public build keeps none that names a supplier', () => {
    const products = (JSON.parse(readFileSync(full, 'utf8')) as { products: { id: string; card_id?: string }[] }).products;
    const flagged = cardRedirects(products, { public: false });
    const pub = cardRedirects(products, { public: true });
    const SUPPLIER = /(?:^|[-/])(cj|cjdropshipping|aliexpress|ae|zendrop|temu|alibaba|amazon|etsy|spocket|dsers)(?=[-/])|[a-z]-\d{6,}(?=[-/])/i;
    // QA counted 39 such addresses in the public build of a8104956
    expect(flagged.filter((l) => SUPPLIER.test(l.split(' ')[0]!)).length).toBeGreaterThanOrEqual(39);
    expect(pub.filter((l) => SUPPLIER.test(l.split(' ')[0]!))).toEqual([]);
    for (const l of [...flagged, ...pub]) expect(l).toMatch(/^\/p\/[^ ]+\/ \/p\/[^ ]+\/ 301$/);
  });
});

describe('ת43 and ה1: the warm-modern poster', () => {
  const dir = sitePath('web/public/media/house/living-room/warm-modern/M0/poster');
  const house = sitePath('.generated/house.living-room.warm-modern.json');
  /** a WebP's first image chunk: 'VP8 ' is lossy, 'VP8L' lossless (near-lossless included) */
  const kind = (f: string) => {
    const b = readFileSync(f);
    const at = b.toString('latin1', 12, 16) === 'VP8X' ? b.indexOf('VP8', 30, 'latin1') : 12;
    return b.toString('latin1', at, at + 4);
  };
  it.runIf(existsSync(dir))('the WebP fallback is lossy (q95, QA’s ruling), about 669 KB at 2720 and 157 KB at 1280; the AVIF is unchanged', async () => {
    for (const [w, maxKb] of [
      [2720, 800],
      [1280, 220],
    ] as const) {
      const f = `${dir}/default.${w}.webp`;
      expect(kind(f), `${w}`).toBe('VP8 ');
      expect(statSync(f).size / 1024, `${w}`).toBeLessThan(maxKb);
      expect((await sharp(f).metadata()).width).toBe(w);
      expect(existsSync(`${dir}/default.${w}.avif`)).toBe(true);
    }
  });
  it.runIf(existsSync(house))('the inlined placeholder: the same composition at 48 × 27, a few hundred bytes', async () => {
    const p = (JSON.parse(readFileSync(house, 'utf8')) as { scene: { poster?: { placeholder?: string } } }).scene.poster?.placeholder ?? '';
    expect(p).toMatch(/^data:image\/webp;base64,[A-Za-z0-9+/=]+$/);
    expect(p.length).toBeLessThan(2048);
    const img = sharp(Buffer.from(p.split(',')[1]!, 'base64'));
    expect(await img.metadata()).toMatchObject({ width: 48, height: 27 });
    // it is the room, light, not a dark stage
    const { channels } = await img.stats();
    expect(channels.slice(0, 3).reduce((s, c) => s + c.mean, 0) / 3).toBeGreaterThan(90);
  });
});

describe('ת44: no lazy page in the room’s entry, by content', () => {
  const page = (p: string) => `src/pages/${p}.tsx`;
  const graph = (chunks: BundleGraph['chunks']): BundleGraph => ({ chunks });
  const lazy = {
    'assets/Order-a.js': { isEntry: false, imports: [], dynamicImports: [], modules: [page('Order')] },
    'assets/Cart-a.js': { isEntry: false, imports: [], dynamicImports: [], modules: [page('Cart')] },
    'assets/Checkout-a.js': { isEntry: false, imports: [], dynamicImports: [], modules: [page('Checkout')] },
    'assets/Product-a.js': { isEntry: false, imports: [], dynamicImports: [], modules: [page('Product')] },
    'assets/Legal-a.js': { isEntry: false, imports: [], dynamicImports: [], modules: [page('Legal')] },
    'assets/MockPay-a.js': { isEntry: false, imports: [], dynamicImports: [], modules: [page('MockPay')] },
  };
  it('a split build passes: the pages are reached only by dynamic imports', () => {
    const g = graph({
      'assets/main-x.js': {
        isEntry: true,
        imports: ['assets/shared-y.js'],
        dynamicImports: Object.keys(lazy),
        modules: ['src/main.tsx', 'src/pages/Room.tsx'],
      },
      'assets/shared-y.js': { isEntry: false, imports: [], dynamicImports: [], modules: ['src/state/cart.ts'] },
      ...lazy,
    });
    expect(lazyPagesInEntry(g, ['assets/main-x.js'])).toEqual([]);
    expect(lazyPagesMissing(g)).toEqual([]);
    expect([...staticClosure(g, ['assets/main-x.js'])].sort()).toEqual(['assets/main-x.js', 'assets/shared-y.js']);
  });
  it('QA’s mutation: the order page imported statically, so its code sits in the entry under the entry’s own name: caught', () => {
    const { ['assets/Order-a.js']: _gone, ...rest } = lazy;
    const g = graph({
      'assets/main-x.js': { isEntry: true, imports: [], dynamicImports: Object.keys(rest), modules: ['src/main.tsx', page('Order')] },
      ...rest,
    });
    expect(lazyPagesInEntry(g, ['assets/main-x.js'])).toEqual(['Order (in assets/main-x.js)']);
  });
  it('a page bundled into a shared chunk the entry imports statically, under any name: caught', () => {
    const g = graph({
      'assets/main-x.js': { isEntry: true, imports: ['assets/index-z.js'], dynamicImports: [], modules: ['src/main.tsx'] },
      'assets/index-z.js': { isEntry: false, imports: [], dynamicImports: [], modules: ['src/components/Media.tsx', page('Checkout')] },
      ...lazy,
    });
    expect(lazyPagesInEntry(g, ['assets/main-x.js'])).toEqual(['Checkout (in assets/index-z.js)']);
  });
  const real = readGraph();
  it.runIf(!!real)('the last real build: the entry index.html loads carries none of them, and each has its code somewhere', () => {
    const html = sitePath('web/dist/index.html');
    if (!existsSync(html)) return;
    const entry = [...readFileSync(html, 'utf8').matchAll(/\/(assets\/[^"' ]+\.js)/g)].map((m) => m[1]!);
    expect(entry.length).toBeGreaterThan(0);
    expect(lazyPagesInEntry(real!, entry)).toEqual([]);
    expect(lazyPagesMissing(real!)).toEqual([]);
  });
});

describe('ה7: the deploy check cannot be skipped; the exclusions point to their real test', () => {
  it('every wrangler deploy runs check-config first, and `npm run deploy` does too; CI runs it on its own line', () => {
    const wrangler = readFileSync(sitePath('api/wrangler.jsonc'), 'utf8');
    expect(wrangler).toMatch(/"build":\s*\{\s*"command":\s*"npx tsx scripts\/check-config\.ts"/);
    const api = JSON.parse(readFileSync(sitePath('api/package.json'), 'utf8')) as { scripts: Record<string, string> };
    expect(api.scripts.deploy).toMatch(/^tsx scripts\/check-config\.ts && wrangler deploy/);
    expect(api.scripts.build).toMatch(/^tsx scripts\/check-config\.ts && /);
    expect(readFileSync(repoPath('.github/workflows/site-ci.yml'), 'utf8')).toContain('npm run check:config -w @hd/api');
    const runbook = readFileSync(repoPath('docs/ops/deploy-runbook.md'), 'utf8');
    expect(runbook).toContain('npm run deploy -w @hd/api');
    expect(runbook).not.toMatch(/`npx wrangler deploy --env preview` מ-`site\/api`/);
    expect(runbook).toContain('SameSite');
  });
  it('the sale exclusions name test files that exist', () => {
    const rule = (JSON.parse(readFileSync(repoPath('data/catalog/sale-exclusions.json'), 'utf8')) as { rule: string }).rule;
    const named = [...rule.matchAll(/site\/[\w/.-]+\.test\.ts/g)].map((m) => m[0]);
    expect(named.length).toBeGreaterThan(0);
    for (const f of named) expect(existsSync(repoPath(f)), f).toBe(true);
  });
});
