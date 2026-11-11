/**
 * S14, QA ת27: the supplier is asked for the very option that was sold. A card with supplier options names a SKU per
 * option (`options.skus`); its product-level `supplier.sku` is the supplier's generic product code, which does not say
 * which option to send. So every variant the build sells from such a card carries one of the card's option SKUs: the
 * option's own, and for options that collapse to one sold row (`:default`, the others excluded) that row's SKU. A set's
 * parts are option SKUs too. tools/build-catalog.ts fails the build on any issue; tools/test/s14-catalog.test.ts checks
 * the rule and the real build.
 *
 * A card without options sells one SKU, its `supplier.sku`. On two CJ cards that is CJ's product-level code too
 * (CJJT1610110, CJYD2389779): the product's one variant has its own SKU (CJJT161011001AZ, CJYD238977901AZ), recorded in
 * the cached CJ product (data/sources/cj/<pid>.json, the sourcing agent's). The build resolves it from there
 * (`singleSku`), and the check refuses a sold variant that still carries a product-level code it knows.
 */
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

export type SkuCard = {
  id: string;
  supplier?: { sku?: string | null } | null;
  options?: { default_sku: string; skus: { id: string }[] } | null;
  /** the supplier's product-level code, when the build knows it (the cached CJ product): never what the supplier is asked for */
  product_level_sku?: string | null;
};
type SkuVariant = { id: string; supplier_sku: string | null; set_skus?: string[] | null; active: boolean; set_part?: boolean; sale_excluded?: string | null };
type SkuProduct = { id: string; card_id?: string; source_path: string; variants_full?: SkuVariant[] };
export type SkuIssue = { product: string; card: string; variant: string; supplier_sku: string | null; why: string };

/** Every sold variant whose supplier SKU is not one of its card's option SKUs (or is missing). */
export function supplierSkuIssues(products: SkuProduct[], cardOf: (p: SkuProduct) => SkuCard | null | undefined): SkuIssue[] {
  const out: SkuIssue[] = [];
  for (const p of products) {
    const card = cardOf(p);
    if (!card) continue;
    const skus = new Set(card.options?.skus.map((s) => s.id) ?? []);
    for (const v of p.variants_full ?? []) {
      // not sold: inactive, excluded, or a part of a set (the server refuses those)
      if (!v.active || v.set_part || v.sale_excluded) continue;
      const add = (why: string) => out.push({ product: p.id, card: card.id, variant: v.id, supplier_sku: v.supplier_sku, why });
      if (!v.supplier_sku) {
        add('no supplier SKU: the supplier cannot be asked for it');
        continue;
      }
      if (!skus.size) {
        // a card without options: its one SKU, which must not be the supplier's product-level code
        if (card.product_level_sku && v.supplier_sku === card.product_level_sku)
          add(`the supplier's product-level code, not its variant's SKU (data/sources/cj: the product's variants carry their own)`);
        continue;
      }
      if (!skus.has(v.supplier_sku))
        add(
          v.supplier_sku === card.supplier?.sku
            ? `the card's product-level SKU, not an option's: the supplier would not know which option to send (one of ${[...skus].slice(0, 4).join(', ')}${skus.size > 4 ? ', …' : ''})`
            : "not one of the card's option SKUs",
        );
      for (const part of v.set_skus ?? []) if (!skus.has(part)) add(`a part of the set (${part}) is not one of the card's option SKUs`);
    }
  }
  return out;
}

/** What the build reads of a cached CJ product (data/sources/cj/<pid>.json): its product-level code and its variants. */
export type CjProduct = { productSku: string | null; variants: { vid: string; variantSku: string }[] };

/** The cached CJ product of a card (by the pid in its product url), or null when there is none. */
export function cjProductOf(repo: string, card: { supplier?: { name?: string; product_url?: string } | null }): CjProduct | null {
  if (!/^CJ/i.test(card.supplier?.name ?? '')) return null;
  const pid = /-p-(\d+)\.html/.exec(card.supplier?.product_url ?? '')?.[1];
  const f = pid ? join(repo, 'data/sources/cj', `${pid}.json`) : null;
  if (!f || !existsSync(f)) return null;
  try {
    const p = (
      JSON.parse(readFileSync(f, 'utf8')) as {
        sections?: { product?: { payload?: { productSku?: string; variants?: { vid?: string; variantSku?: string }[] } } };
      }
    ).sections?.product?.payload;
    if (!p) return null;
    return {
      productSku: p.productSku ?? null,
      variants: (p.variants ?? []).flatMap((v) => (v.vid && v.variantSku ? [{ vid: String(v.vid), variantSku: v.variantSku }] : [])),
    };
  } catch {
    return null;
  }
}

/**
 * The SKU a card without options is sold as: its `supplier.sku`, unless that is the supplier's product-level code of a
 * product with exactly one variant: then that variant's SKU (`resolved`). With more than one variant the code cannot be
 * resolved here: it stays, and the check refuses it (sourcing names the option on the card).
 */
export function singleSku(card: { supplier?: { sku?: string | null } | null }, cj: CjProduct | null): { sku: string | null; resolved: boolean } {
  const sku = card.supplier?.sku ?? null;
  if (!cj || !sku || sku !== cj.productSku || cj.variants.length !== 1) return { sku, resolved: false };
  return { sku: cj.variants[0]!.variantSku, resolved: true };
}
