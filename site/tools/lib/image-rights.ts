/**
 * S15 (designer §5, the owner's launch item "supplier image rights"): the public build (HD_PUBLIC=1) ships no supplier
 * picture whose rights are not confirmed. A card states its pictures' rights once (`images.usage_rights`: confirmed,
 * unclear or none); the option pictures come from the same listing, so they carry the same rights.
 *
 * - **The data:** tools/supplier-images.ts writes `.generated/supplier-images.public.json`, the manifest with only the
 *   pictures that may ship. The public build reads it in place of the full one (web/vite.config.ts), so no page, script
 *   or JSON-LD of it names a withheld picture, and it removes every other file from dist/media/products.
 * - **In its place:** the product page keeps the render from the room; where the supplier's picture was the only one
 *   (an order line, a product with no render), a neutral tile.
 * - **The check:** tools/check-image-rights.ts, after every build. In a public build it fails when a withheld picture
 *   is a file of the build or is named by one; behind the flag it reports what a public build withholds.
 * - **Behind the flag nothing changes.** The Artifact preview (a private page) keeps its pictures, as before.
 */
import type { SupplierImageManifest } from '@hd/shared';

export type Rights = 'confirmed' | 'unclear' | 'none';

/** the only rights a supplier picture ships with on the public site */
export const shipsPublicly = (r: Rights | undefined | null): boolean => r === 'confirmed';

/** The manifest the public build reads: only the pictures, and option pictures, of products whose rights are confirmed. */
export function publicManifest(m: SupplierImageManifest): SupplierImageManifest {
  const products = Object.fromEntries(Object.entries(m.products).filter(([, p]) => shipsPublicly(p.usage_rights)));
  const options = Object.fromEntries(Object.entries(m.options ?? {}).filter(([id]) => id in products));
  return { ...m, products, options, missing: m.missing };
}

/** Every media file a manifest names, as its path under media/ (products/<id>/<name>.<width>.webp). */
export function manifestFiles(m: SupplierImageManifest): string[] {
  return [
    ...Object.values(m.products).map((p) => `${p.src}.webp`),
    ...Object.entries(m.options ?? {}).flatMap(([id, o]) => o.files.map((f) => `products/${id}/${f.name}.${m.width}.webp`)),
  ];
}

/** What the rule withholds from a public build: the products, and the pictures (product photos and option pictures). */
export function withheld(m: SupplierImageManifest): { products: string[]; photos: number; optionFiles: number; byRights: Record<string, number> } {
  const out = Object.entries(m.products).filter(([, p]) => !shipsPublicly(p.usage_rights));
  const ids = new Set(out.map(([id]) => id));
  const byRights: Record<string, number> = {};
  for (const [, p] of out) byRights[p.usage_rights] = (byRights[p.usage_rights] ?? 0) + 1;
  // a product with option pictures but no main photo is withheld by its card's rights too (none today)
  for (const id of Object.keys(m.options ?? {})) if (!(id in m.products)) ids.add(id);
  return {
    products: [...ids].sort(),
    photos: out.length,
    optionFiles: Object.entries(m.options ?? {})
      .filter(([id]) => ids.has(id))
      .reduce((n, [, o]) => n + o.files.length, 0),
    byRights,
  };
}

export type RightsIssue = { where: string; what: string };

/** a supplier picture's path anywhere in a file: products/<public id>/<photo or opt-hash>.<width>.webp */
const PICTURE = /products\/([a-z0-9-]+)\/((?:photo|opt-[0-9a-f]{10})\.\d+\.webp)/g;

/**
 * The public build's check: no file under media/products of a product whose rights are not confirmed, no text file
 * that names one, and a public manifest without one. `files` are the build's paths (relative to dist), `text` reads a
 * text file, `rightsOf` gives a product's rights (undefined: not a product the shop knows, which is not shipped either).
 */
export function rightsIssues(
  files: string[],
  text: (rel: string) => string,
  rightsOf: (id: string) => Rights | undefined,
  manifest?: SupplierImageManifest,
): RightsIssue[] {
  const issues: RightsIssue[] = [];
  for (const f of files) {
    const m = /^media\/products\/([^/]+)\//.exec(f);
    if (m && !shipsPublicly(rightsOf(m[1]!))) issues.push({ where: f, what: `a file of ${m[1]} (rights: ${rightsOf(m[1]!) ?? 'unknown'})` });
  }
  for (const f of files.filter((x) => /\.(html|js|mjs|css|json|xml|txt|webmanifest)$/.test(x))) {
    for (const m of text(f).matchAll(PICTURE)) {
      if (!shipsPublicly(rightsOf(m[1]!))) issues.push({ where: f, what: `names ${m[0]} (rights: ${rightsOf(m[1]!) ?? 'unknown'})` });
    }
  }
  if (manifest)
    for (const [id, p] of Object.entries(manifest.products))
      if (!shipsPublicly(p.usage_rights)) issues.push({ where: 'supplier-images.public.json', what: `${id} (rights: ${p.usage_rights})` });
  return issues;
}
