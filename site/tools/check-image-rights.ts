/**
 * S15, the owner's launch item "supplier image rights" (tools/lib/image-rights.ts): after every build.
 *
 *   HD_PUBLIC=1 (the public build): fails when web/dist holds a supplier picture whose rights are not confirmed, when a
 *               page, script, style or data file of it names one, or when the public manifest lists one.
 *   otherwise (behind the flag): nothing is withheld; it reports what a public build withholds, and fails only if the
 *               public manifest itself lists a picture whose rights are not confirmed.
 *
 *   tsx tools/check-image-rights.ts [--json=<out.json>]
 */
import { existsSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join, relative } from 'node:path';
import type { FullCatalog, PublicCatalog, SupplierImageManifest } from '@hd/shared';
import { GENERATED, sitePath } from './lib/paths';
import { rightsIssues, withheld, type Rights } from './lib/image-rights';

const PUBLIC = process.env.HD_PUBLIC === '1';
const DIST = sitePath('web/dist');
const read = <T>(f: string): T => JSON.parse(readFileSync(f, 'utf8')) as T;
const out = process.argv.find((a) => a.startsWith('--json='))?.slice(7);

const full = read<FullCatalog>(join(GENERATED, 'catalog.full.json'));
const pub = read<PublicCatalog>(join(GENERATED, 'catalog.public.json'));
const manifest = read<SupplierImageManifest>(join(GENERATED, 'supplier-images.json'));
const publicFile = join(GENERATED, 'supplier-images.public.json');
if (!existsSync(publicFile)) {
  console.error('check-image-rights: .generated/supplier-images.public.json is missing: run `npm run assets:supplier` first.');
  process.exit(1);
}
const publicM = read<SupplierImageManifest>(publicFile);
const rights = new Map<string, Rights>(full.products.map((p) => [p.id, p.supplier_image.usage_rights]));
// the render from the room a product page keeps (the scene's layer of the product's option); without one, the neutral tile
const scene = read<{ slots: Record<string, { product: { src: (string | null)[] } | null }> }>(join(GENERATED, 'scene.living-room.nordic.json'));
const rendered = (id: string): boolean =>
  pub.rooms.some((r) => r.slots.some((s) => s.options.some((o) => o.product_id === id && !!scene.slots[s.id]?.product?.src[o.position - 1])));
const w = withheld(manifest);
const shown = pub.products.length;
const lose = pub.products.filter((p) => w.products.includes(p.id));
const summary = {
  build: PUBLIC ? 'public (HD_PUBLIC=1)' : 'behind the flag',
  public_products: shown,
  products_with_a_supplier_picture: Object.keys(manifest.products).length,
  public_products_losing_the_supplier_picture: lose.length,
  withheld_photos: w.photos,
  withheld_option_pictures: w.optionFiles,
  withheld_by_rights: w.byRights,
  shipped_publicly: Object.keys(publicM.products).length,
  // the product page keeps the render from the room; a product without one shows the neutral tile
  public_products_left_without_any_picture: lose.filter((p) => !rendered(p.id)).map((p) => p.id),
};

const issues = rightsIssues(
  [],
  () => '',
  (id) => rights.get(id),
  publicM,
);
if (PUBLIC) {
  if (!existsSync(DIST)) {
    console.error('check-image-rights: web/dist is missing: run the build first.');
    process.exit(1);
  }
  const walk = (d: string): string[] => readdirSync(d).flatMap((n) => (statSync(join(d, n)).isDirectory() ? walk(join(d, n)) : [join(d, n)]));
  const files = walk(DIST).map((f) => relative(DIST, f).split('\\').join('/'));
  issues.push(
    ...rightsIssues(
      files,
      (rel) => readFileSync(join(DIST, rel), 'utf8'),
      (id) => rights.get(id),
    ),
  );
  Object.assign(summary, { dist_files: files.length, dist_supplier_files: files.filter((f) => f.startsWith('media/products/')).length });
}
if (out) writeFileSync(out, JSON.stringify({ ...summary, issues }, null, 1));

console.log(
  `image rights (S15, ${summary.build}): ${lose.length}/${shown} public products lose the supplier's picture in a public build ` +
    `(${w.photos} photos, ${w.optionFiles} option pictures withheld: ${Object.entries(w.byRights)
      .map(([r, k]) => `${r} ${k}`)
      .join(', ')}); shipped publicly: ${summary.shipped_publicly}` +
    (PUBLIC ? `; web/dist: ${(summary as { dist_supplier_files?: number }).dist_supplier_files ?? 0} supplier files` : '; behind the flag nothing is withheld'),
);
if (issues.length) {
  for (const i of issues.slice(0, 30)) console.error(`  ${i.where}: ${i.what}`);
  console.error(`check-image-rights: ${issues.length} supplier picture(s) without confirmed rights would ship in the public build.`);
  process.exit(1);
}
