/**
 * Supplier photos for the product page (FR-I, docs/studio-rules.md ג.0, 2026-10-10): the product page leads with the
 * render from the room, says so, and also shows the supplier's original photo. The photo is the first image of the
 * product card (`images.urls`), one per product (size budget), downloaded once, encoded as WebP 800 px wide and served
 * from our own media (media/products/<id>/supplier.800.webp): the site loads it from our CDN and the Artifact ships it
 * next to the page, never a hot-link to the supplier. The card's `usage_rights` is recorded in the manifest (all
 * "unclear" today: to clear with the suppliers before launch).
 *
 *   tsx tools/supplier-images.ts             part of `npm run prepare:data`, after the catalog
 *   tsx tools/supplier-images.ts --offline   never download: a product without a cached original gets no photo
 *   tsx tools/supplier-images.ts --force     re-encode even when the output is up to date
 *
 * Input:  .generated/catalog.full.json (supplier_image.url per shown product; the public catalog never has the url)
 * Cache:  .cache/supplier-images/<sha256(url)>.bin, gitignored (a second build does not hit the network)
 * Output: web/public/media/products/<id>/supplier.800.webp and .generated/supplier-images.json
 *         ({ products: { <id>: { src, width, height, usage_rights } }, missing: [...] })
 *
 * A download that fails is a warning, not a build failure: the product page then shows the render only.
 */
import sharp from 'sharp';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { join, dirname } from 'node:path';
import { tmpdir } from 'node:os';
import type { FullCatalog, SupplierImageManifest } from '@hd/shared';
import { GENERATED, MEDIA_OUT, sitePath } from './lib/paths';

const WIDTH = 800;
const OFFLINE = process.argv.includes('--offline');
const FORCE = process.argv.includes('--force');
const CACHE = sitePath('.cache/supplier-images');
const MANIFEST = join(GENERATED, 'supplier-images.json');
const UA = 'Mozilla/5.0 (X11; Linux x86_64) homedesign-site-build/1.0';
const MAX_BYTES = 25 * 1024 * 1024;

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
  for (const p of catalog.products) {
    const url = p.supplier_image.url;
    if (!url) {
      manifest.missing.push({ id: p.id, reason: 'the card has no https image url' });
      continue;
    }
    const src = `products/${p.id}/supplier`;
    const out = join(MEDIA_OUT, `${src}.${WIDTH}.webp`);
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
  writeFileSync(MANIFEST, JSON.stringify(manifest, null, 1));
  const n = Object.keys(manifest.products).length;
  const rights = (['confirmed', 'unclear', 'none'] as const).map((r) => `${r} ${Object.values(manifest.products).filter((x) => x.usage_rights === r).length}`);
  console.log(
    `supplier images: ${n}/${catalog.products.length} products (${encoded} encoded, ${reused} up to date, ${downloaded} downloaded) → media/products/<id>/supplier.${WIDTH}.webp` +
      ` · usage rights ${rights.join(', ')} (${((Date.now() - t0) / 1000).toFixed(1)}s)`,
  );
  for (const m of manifest.missing) console.warn(`  missing: ${m.id}: ${m.reason}`);
}

await main();
