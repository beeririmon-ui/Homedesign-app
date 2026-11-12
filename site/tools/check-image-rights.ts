/**
 * S15, the owner's launch item "supplier image rights" (tools/lib/image-rights.ts): after every build.
 *
 *   HD_PUBLIC=1 (the public build): fails when web/dist holds a supplier picture whose rights are not confirmed, when a
 *               page, script, style or data file of it names one, or when the public manifest lists one.
 *   otherwise (behind the flag): nothing is withheld; it reports what a public build withholds, and fails only if the
 *               public manifest itself lists a picture whose rights are not confirmed.
 *
 * S17, QA ת45: by content, not only by path (tools/lib/rights-content.ts). In a public build every file is checked:
 *   bytes      the sha256 of a file, or of a data: URI, equals a supplier-derived file's (the shop's and the story's
 *              ledgers, every width) or a cached original's;
 *   pixels     a raster, or an image in a data: URI, within 24 of 256 bits (dHash 16×16) of a supplier picture, or a
 *              near miss (≤ 48) whose 32×32 grey image differs from it by ≤ 3 on average;
 *   hosts      a URL on a host the cards' pictures come from (alicdn.com, cjdropshipping.com, zendrop.com…).
 * S19, QA S17: the near miss only when both pictures carry ink (ת50); each supplier picture mirrored as well, every
 *   picture with its uniform margins trimmed as well, a fixed list of supplier picture domains beside the cards', and a
 *   data: URI read as a browser reads it (ת51). The nearest picture outside the supplier folders is printed every build.
 * S21, QA S19: rule A between two plain forms only when d ≤ (popcount a + popcount b) / 2 (ת66, QA's P3: a flat picture
 *   never matches an inked one by A); the margin printed counts only the pairs A may judge. Not caught (the known
 *   limits, launch checklist 1.5, tools/lib/rights-content.ts): a crop into the picture, a rotation, a flip upside-down,
 *   a flip with a change of colour, one tile of a collage.
 * Behind the flag the same scan runs as the control: it reports what it finds (the shop's and the story's copies, which
 * the flag build ships) and anything found elsewhere, without failing.
 *
 *   tsx tools/check-image-rights.ts [--json=<out.json>] [--dist=<a build to check instead of web/dist>]
 */
import { existsSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
import type { FullCatalog, PublicCatalog, SupplierImageManifest } from '@hd/shared';
import { GENERATED, SITE, repoPath, sitePath } from './lib/paths';
import { rightsIssues, withheld, type Rights } from './lib/image-rights';
import {
  DhashCache,
  LEDGER_SHOP,
  LEDGER_STORY,
  NEAR_MAX_HAMMING,
  NEAR_MAX_MAD32,
  NEAR_MIN_INK,
  PIXEL_MAX_HAMMING,
  SUPPLIER_IMAGE_DOMAINS,
  cardPictureHosts,
  pictureHosts,
  readCards,
  readLedger,
  registrableDomain,
  scanBuild,
  supplierSet,
  type ContentFinding,
} from './lib/rights-content';

const PUBLIC = process.env.HD_PUBLIC === '1';
const distArg = process.argv.find((a) => a.startsWith('--dist='))?.slice(7);
const DIST = distArg ? resolve(distArg) : sitePath('web/dist');
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
if (!existsSync(DIST)) {
  console.error('check-image-rights: web/dist is missing: run the build first.');
  process.exit(1);
}
const walk = (d: string): string[] => readdirSync(d).flatMap((n) => (statSync(join(d, n)).isDirectory() ? walk(join(d, n)) : [join(d, n)]));
const files = walk(DIST).map((f) => relative(DIST, f).split('\\').join('/'));
if (PUBLIC) {
  issues.push(
    ...rightsIssues(
      files,
      (rel) => readFileSync(join(DIST, rel), 'utf8'),
      (id) => rights.get(id),
    ),
  );
  Object.assign(summary, { dist_files: files.length, dist_supplier_files: files.filter((f) => f.startsWith('media/products/')).length });
}

// ---- S17, QA ת45: by content
const t0 = Date.now();
const ledgers = [readLedger(join(GENERATED, LEDGER_SHOP)), readLedger(join(GENERATED, LEDGER_STORY))];
if (!ledgers[0]) {
  console.error(`check-image-rights: .generated/${LEDGER_SHOP} is missing: run \`npm run assets:supplier\` first.`);
  process.exit(1);
}
const cards = readCards(repoPath('data/products'));
const hosts = pictureHosts(cards);
const dhashes = new DhashCache(sitePath('.cache/rights-dhash.json'));
const set = await supplierSet({ site: SITE, ledgers: ledgers.filter((l) => l !== null), cacheDir: sitePath('.cache/supplier-images'), hosts, dhashes });
/** behind the flag the shop's and the story's copies ship by design; anything else the scan finds is said */
const SUPPLIER_FOLDERS = /^media\/(?:products|story\/products)\//;
const scan = await scanBuild(DIST, set, dhashes, { files, elsewhere: (where) => PUBLIC || !SUPPLIER_FOLDERS.test(where) });
dhashes.save();
const byHow = (f: ContentFinding[]) =>
  Object.fromEntries(['bytes', 'pixels', 'data-uri bytes', 'data-uri pixels', 'host'].map((h) => [h, f.filter((x) => x.how === h).length]));
const elsewhere = scan.findings.filter((f) => !SUPPLIER_FOLDERS.test(f.where));
const content = {
  supplier_set: {
    ...set.stats,
    card_picture_hosts: cardPictureHosts(cards),
    fixed_domains: SUPPLIER_IMAGE_DOMAINS,
    domains: [...new Set(hosts.map(registrableDomain))].sort(),
    story_ledger: !!ledgers[1],
  },
  pixel_threshold: `dHash 16×16, Hamming ≤ ${PIXEL_MAX_HAMMING} of 256 and ≤ half the set bits of the two (or ≤ ${NEAR_MAX_HAMMING} with a 32×32 grey difference ≤ ${NEAR_MAX_MAD32} when both carry ink ≥ ${NEAR_MIN_INK}); plain and mirrored, and trimmed of margins`,
  not_caught: 'a crop into the picture, a rotation, a flip upside-down, a flip with a change of colour, one tile of a collage (launch checklist 1.5)',
  scanned: { files: scan.stats.files, rasters: scan.stats.rasters, data_uris: scan.stats.data_uris, text_files: scan.stats.text_files },
  found: byHow(scan.findings),
  found_outside_supplier_folders: byHow(elsewhere),
  nearest: scan.stats.nearest,
  nearest_by_grey: scan.stats.nearest_by_grey,
  nearest_outside_supplier_folders: scan.stats.nearest_elsewhere,
  nearest_by_grey_outside_supplier_folders: scan.stats.nearest_by_grey_elsewhere,
  seconds: Number(((Date.now() - t0) / 1000).toFixed(1)),
};
Object.assign(summary, { by_content: content });
if (PUBLIC) for (const f of scan.findings) issues.push({ where: f.where, what: `by ${f.how}: ${f.what}` });
if (out) writeFileSync(out, JSON.stringify({ ...summary, issues, findings: scan.findings.slice(0, 2000) }, null, 1));

console.log(
  `image rights (S15, ${summary.build}): ${lose.length}/${shown} public products lose the supplier's picture in a public build ` +
    `(${w.photos} photos, ${w.optionFiles} option pictures withheld: ${Object.entries(w.byRights)
      .map(([r, k]) => `${r} ${k}`)
      .join(', ')}); shipped publicly: ${summary.shipped_publicly}` +
    (PUBLIC ? `; web/dist: ${(summary as { dist_supplier_files?: number }).dist_supplier_files ?? 0} supplier files` : '; behind the flag nothing is withheld'),
);
const said = (o: Record<string, number>) =>
  Object.entries(o)
    .map(([k, v]) => `${k} ${v}`)
    .join(', ');
console.log(
  `image rights by content (S17): ${scan.stats.files} files, ${scan.stats.rasters} pictures (${scan.stats.data_uris} data: URIs) against ` +
    `${set.stats.withheld_files} supplier files by sha256 and ${set.stats.pictures} pictures (${set.stats.fingerprints} fingerprints) by pixels (${content.pixel_threshold}), hosts ${content.supplier_set.domains.join(', ')} ` +
    `(${content.seconds}s): ` +
    (PUBLIC
      ? `found ${scan.findings.length} (${said(content.found)})`
      : `behind the flag, the control: found ${scan.findings.length} (${said(content.found)}), ${elsewhere.length} outside media/products and media/story/products`),
);
// S19 (QA S17, ת50): the margin, every build: the nearest picture that is not a supplier copy by design
const n0 = scan.stats.nearest_elsewhere[0];
const g0 = scan.stats.nearest_by_grey_elsewhere[0];
console.log(
  `  nearest outside the supplier folders: ${n0 ? `${n0.where} dHash ${n0.hamming}/256 from ${n0.picture}${n0.variant ? ` (${n0.variant})` : ''} (rule A at ${PIXEL_MAX_HAMMING}, among the pairs it may judge)` : 'none'}; ` +
    `by grey: ${g0 ? `${g0.where} ${g0.mad32} (rule B at ${NEAR_MAX_MAD32}, with ink)` : 'none'}`,
);
if (!PUBLIC) for (const f of elsewhere.slice(0, 10)) console.warn(`  behind the flag, outside the supplier folders: ${f.where}: by ${f.how}: ${f.what}`);
if (issues.length) {
  for (const i of issues.slice(0, 30)) console.error(`  ${i.where}: ${i.what}`);
  console.error(`check-image-rights: ${issues.length} supplier picture(s) without confirmed rights would ship in the public build.`);
  process.exit(1);
}
