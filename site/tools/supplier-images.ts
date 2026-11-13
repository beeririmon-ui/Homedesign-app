/**
 * Supplier photos for the product page (FR-I, docs/studio-rules.md ג.0, 2026-10-10): the product page leads with the
 * render from the room, says so, and also shows the supplier's original photo. The photo is the first image of the
 * product card (`images.urls`), one per product (size budget), downloaded once, encoded as WebP 800 px wide and served
 * from our own media (media/products/<public id>/photo.800.webp): the site loads it from our CDN and the Artifact ships it
 * next to the page, never a hot-link to the supplier. The card's `usage_rights` is recorded in the manifest (all
 * "unclear" today: to clear with the suppliers before launch).
 *
 *   tsx tools/supplier-images.ts             part of `npm run prepare:data`, after the catalog
 *   tsx tools/supplier-images.ts --offline   never download: a product without a cached original gets no photo
 *   tsx tools/supplier-images.ts --force     re-encode even when the output is up to date
 *
 * Input:  .generated/catalog.full.json (supplier_image.url per shown product; the public catalog never has the url)
 * Cache:  .cache/supplier-images/<sha256(url)>.bin, gitignored (a second build does not hit the network)
 * Output: web/public/media/products/<public id>/photo.800.webp and .generated/supplier-images.json
 *         ({ products: { <id>: { src: 'products/<id>/supplier.800', width, height, usage_rights } }, missing: [...] }),
 *         and .generated/supplier-images.public.json: S15, the same with only the pictures whose rights are confirmed,
 *         the manifest the public build (HD_PUBLIC=1) reads (tools/lib/image-rights.ts)
 *
 * A download that fails is a warning, not a build failure: the product page then shows the render only.
 *
 * Supplier options (card `options`, studio rules ג 2026-10-11): the picture of each option too, one file per distinct
 * picture (media/products/<id>/opt-<hash>.800.webp), listed per product in `options` (aligned with the product's
 * compact options). The product page swaps the supplier photo for the chosen option's. The Artifact ships only the
 * first ARTIFACT_OPTION_FILES of them (`artifact: true`), so it stays inside its file limit; the others fall back to
 * the product's photo there.
 */
import sharp from 'sharp';
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { join, dirname, relative } from 'node:path';
import { tmpdir } from 'node:os';
import { expandOptions, type FullCatalog, type SupplierImageManifest } from '@hd/shared';
import { GENERATED, MEDIA_OUT, SITE, sitePath } from './lib/paths';
import { publicManifest, withheld, type Rights } from './lib/image-rights';
import { LEDGER_SHOP, sha256, writeLedger, type LedgerEntry } from './lib/rights-content';

const WIDTH = 800;
const OFFLINE = process.argv.includes('--offline');
const FORCE = process.argv.includes('--force');
const CACHE = sitePath('.cache/supplier-images');
const MANIFEST = join(GENERATED, 'supplier-images.json');
const PUBLIC_MANIFEST = join(GENERATED, 'supplier-images.public.json');
const UA = 'homedesign-site-build/1.0';
const MAX_BYTES = 25 * 1024 * 1024;
/** option pictures shipped with the Artifact (200 files at most there; MOCK1: the tour's layers take 76 of them) */
const ARTIFACT_OPTION_FILES = 30;

const catalog = JSON.parse(readFileSync(join(GENERATED, 'catalog.full.json'), 'utf8')) as FullCatalog;
const previous: SupplierImageManifest | null = existsSync(MANIFEST) ? (JSON.parse(readFileSync(MANIFEST, 'utf8')) as SupplierImageManifest) : null;
mkdirSync(CACHE, { recursive: true });

const hashOf = (url: string) => createHash('sha256').update(url).digest('hex').slice(0, 24);

/** The original bytes: from the cache, else downloaded (Node fetch; curl when fetch cannot reach the proxy). */
async function original(url: string): Promise<Buffer | null> {
  const file = join(CACHE, `${hashOf(url)}.bin`);
  if (existsSync(file)) return readFileSync(file);
  if (OFFLINE) return null;
  let buf: Buffer | null = null;
  try {
    const r = await fetch(url, { headers: { 'user-agent': UA, accept: 'image/*,*/*;q=0.8' }, signal: AbortSignal.timeout(45_000), redirect: 'follow' });
    if (r.ok) {
      const ab = await r.arrayBuffer();
      if (ab.byteLength <= MAX_BYTES) buf = Buffer.from(ab);
    } else console.warn(`  ${url}: HTTP ${r.status}`);
  } catch (e) {
    // Node's fetch ignores HTTPS_PROXY unless NODE_USE_ENV_PROXY=1 is set; curl reads it and the CA bundle on its own
    if (process.env.HTTPS_PROXY) {
      try {
        const tmp = join(tmpdir(), `hd-supplier-${hashOf(url)}`);
        execFileSync('curl', ['-sSL', '--fail', '--max-time', '60', '--max-filesize', String(MAX_BYTES), '-A', UA, '-o', tmp, url], { stdio: 'pipe' });
        buf = readFileSync(tmp);
      } catch (e2) {
        console.warn(`  ${url}: ${(e2 as Error).message.split('\n')[0]}`);
      }
    } else console.warn(`  ${url}: ${(e as Error).message}`);
  }
  if (!buf) return null;
  // only a real image goes into the cache (a login page or an error body is not one)
  try {
    const meta = await sharp(buf).metadata();
    if (!meta.width || !meta.height) return null;
  } catch {
    console.warn(`  ${url}: not an image`);
    return null;
  }
  writeFileSync(file, buf);
  return buf;
}

async function main() {
  const t0 = Date.now();
  const manifest: SupplierImageManifest = { generated_at: new Date().toISOString(), width: WIDTH, products: {}, missing: [] };
  let encoded = 0;
  let reused = 0;
  let downloaded = 0;
  // S17 (ת45): every original this run reads, by the product it belongs to (the ledger of the cache)
  const used = new Map<string, string>();
  for (const p of catalog.products) {
    const url = p.supplier_image.url;
    if (url) used.set(url, p.id);
    if (!url) {
      manifest.missing.push({ id: p.id, reason: 'the card has no https image url' });
      continue;
    }
    // the file is named by the encoding width even when a small original stays smaller (withoutEnlargement)
    const src = `products/${p.id}/photo.${WIDTH}`;
    const out = join(MEDIA_OUT, `${src}.webp`);
    const cached = existsSync(join(CACHE, `${hashOf(url)}.bin`));
    const prev = previous?.products[p.id];
    // up to date: same url (its original is cached), output present, dimensions known from the last run
    if (!FORCE && prev && cached && existsSync(out)) {
      manifest.products[p.id] = { src, width: prev.width, height: prev.height, usage_rights: p.supplier_image.usage_rights };
      reused++;
      continue;
    }
    if (!cached && !OFFLINE) downloaded++;
    const buf = await original(url);
    if (!buf) {
      manifest.missing.push({ id: p.id, reason: OFFLINE ? 'not cached (offline build)' : 'download failed' });
      continue;
    }
    mkdirSync(dirname(out), { recursive: true });
    const info = await sharp(buf, { failOn: 'none' }).rotate().resize({ width: WIDTH, withoutEnlargement: true }).webp({ quality: 80, effort: 5 }).toFile(out);
    manifest.products[p.id] = { src, width: info.width, height: info.height, usage_rights: p.supplier_image.usage_rights };
    encoded++;
  }
  // ---- the picture of every supplier option (one file per distinct picture), aligned with options.v ----
  manifest.options = {};
  const prevFiles = new Map<string, { width: number; height: number }>(
    Object.entries(previous?.options ?? {}).flatMap(([pid, o]) => o.files.map((f) => [`products/${pid}/${f.name}.${WIDTH}`, f] as [string, typeof f])),
  );
  let artifactFiles = 0;
  let optEncoded = 0;
  let optMissing = 0;
  let optCount = 0;
  for (const p of catalog.products) {
    if (!p.options) continue;
    const byId = new Map((p.variants_full ?? []).map((v) => [v.id, v]));
    const o = expandOptions(p.id, p.options);
    const files: NonNullable<SupplierImageManifest['options']>[string]['files'] = [];
    const fileOf = new Map<string, number | null>();
    const sku: (number | null)[] = [];
    for (const s of o.skus) {
      const url = byId.get(s.variant_id)?.supplier_image_url ?? null;
      if (!url) {
        sku.push(null);
        continue;
      }
      if (!used.has(url)) used.set(url, p.id);
      if (!fileOf.has(url)) {
        const name = `opt-${hashOf(url).slice(0, 10)}`;
        const src = `products/${p.id}/${name}.${WIDTH}`;
        const out = join(MEDIA_OUT, `${src}.webp`);
        const prev = prevFiles.get(src);
        let dims: { width: number; height: number } | null = null;
        if (!FORCE && prev && existsSync(out) && existsSync(join(CACHE, `${hashOf(url)}.bin`))) dims = prev;
        else {
          const buf = await original(url);
          if (buf) {
            mkdirSync(dirname(out), { recursive: true });
            dims = await sharp(buf, { failOn: 'none' })
              .rotate()
              .resize({ width: WIDTH, withoutEnlargement: true })
              .webp({ quality: 80, effort: 5 })
              .toFile(out);
            optEncoded++;
          } else optMissing++;
        }
        if (dims) {
          const artifact = artifactFiles < ARTIFACT_OPTION_FILES;
          if (artifact) artifactFiles++;
          files.push({ name, width: dims.width, height: dims.height, artifact });
          fileOf.set(url, files.length - 1);
        } else fileOf.set(url, null);
      }
      const i = fileOf.get(url) ?? null;
      sku.push(i);
      if (i !== null) optCount++;
    }
    if (files.length) manifest.options[p.id] = { files, sku };
  }
  writeFileSync(MANIFEST, JSON.stringify(manifest, null, 1));
  // S15: the public build's manifest, without a picture whose rights are not confirmed
  writeFileSync(PUBLIC_MANIFEST, JSON.stringify(publicManifest(manifest), null, 1));
  const out = withheld(manifest);
  // S17 (ת45): the ledger of every file made from a supplier picture, and of every original, by its bytes
  const ledger = shopLedger(manifest, used);
  writeLedger(join(GENERATED, LEDGER_SHOP), { generated_at: manifest.generated_at, source: 'shop+cache', entries: ledger });
  // S7: a folder of a product the catalog no longer names (an old card id with the supplier in it) leaves the media
  const keep = new Set(catalog.products.map((p) => p.id));
  const dir = join(MEDIA_OUT, 'products');
  for (const name of existsSync(dir) ? readdirSync(dir) : []) if (!keep.has(name)) rmSync(join(dir, name), { recursive: true, force: true });
  const n = Object.keys(manifest.products).length;
  const rights = (['confirmed', 'unclear', 'none'] as const).map((r) => `${r} ${Object.values(manifest.products).filter((x) => x.usage_rights === r).length}`);
  console.log(
    `supplier images: ${n}/${catalog.products.length} products (${encoded} encoded, ${reused} up to date, ${downloaded} downloaded) → media/products/<public id>/photo.${WIDTH}.webp` +
      ` · usage rights ${rights.join(', ')} (${((Date.now() - t0) / 1000).toFixed(1)}s)`,
  );
  console.log(
    `option pictures: ${optCount} options, ${Object.values(manifest.options).reduce((n, o) => n + o.files.length, 0)} files (${optEncoded} encoded${optMissing ? `, ${optMissing} failed` : ''}) · artifact: ${artifactFiles} files`,
  );
  console.log(
    `image rights (S15): a public build (HD_PUBLIC=1) withholds the supplier pictures of ${out.products.length}/${n} products ` +
      `(${out.photos} photos, ${out.optionFiles} option pictures; ${Object.entries(out.byRights)
        .map(([r, k]) => `${r} ${k}`)
        .join(', ')}) → ${PUBLIC_MANIFEST}`,
  );
  console.log(
    `rights ledger (S17): ${ledger.length} files by sha256 (shop ${ledger.filter((e) => e.source === 'shop').length}, cached originals ${ledger.filter((e) => e.source === 'cache').length}) → .generated/${LEDGER_SHOP}`,
  );
  for (const m of manifest.missing) console.warn(`  missing: ${m.id}: ${m.reason}`);
}

/**
 * S17, QA ת45: the shop's ledger. Each photo and option picture written under media/products, and each cached original
 * the run read, with its sha256, its product and the card's rights (tools/lib/rights-content.ts).
 */
function shopLedger(manifest: SupplierImageManifest, used: Map<string, string>): LedgerEntry[] {
  const rights = new Map<string, Rights>(catalog.products.map((p) => [p.id, p.supplier_image.usage_rights as Rights]));
  const entries: LedgerEntry[] = [];
  const add = (file: string, product: string, picture: string, source: LedgerEntry['source'], width?: number) => {
    if (!existsSync(file)) return;
    entries.push({
      file: relative(SITE, file).split('\\').join('/'),
      sha256: sha256(readFileSync(file)),
      product,
      rights: rights.get(product) ?? 'none',
      source,
      picture,
      width,
    });
  };
  for (const [id, p] of Object.entries(manifest.products)) add(join(MEDIA_OUT, `${p.src}.webp`), id, p.src.replace(/\.\d+$/, ''), 'shop', p.width);
  for (const [id, o] of Object.entries(manifest.options ?? {}))
    for (const f of o.files) add(join(MEDIA_OUT, `products/${id}/${f.name}.${manifest.width}.webp`), id, `products/${id}/${f.name}`, 'shop', f.width);
  for (const [url, id] of used) {
    const file = join(CACHE, `${hashOf(url)}.bin`);
    add(file, id, relative(SITE, file).split('\\').join('/'), 'cache');
  }
  return entries;
}

await main();
