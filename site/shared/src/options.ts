/**
 * Supplier options (studio rules ג, 2026-10-11, "כל האפשרויות של הספק בדף המוצר"): every SKU the supplier sells for a
 * product, on the axes the product page offers (data/product-card.schema.json `options`). The room shows one of them,
 * `default_sku` (in_room); the card's top-level price is that SKU's price, and the product's main retail price stays
 * what it is today. The other SKUs are priced by the same economics (recommendedRetailIls, the same "…9" rounding).
 *
 *   skuCostCents      supplier cost of a SKU in the card's own terms (a card priced as a set of k keeps the factor)
 *   skuShippingCents  the product's resolved shipping, moved by the supplier's per-SKU difference when both quotes exist
 *   skuRetail         retail of one SKU: the room's SKU = the product price; a studio override; else the economics
 *   optionIssues      the cross-field rules a JSON schema cannot say (also in scripts/sourcing/options.py `validate`)
 *   availableValues / pickSku  the product page's picker logic (pure, unit-tested)
 */
import { z } from 'zod';
import type { ProductCard } from './schema/product-card.gen';
import type { EconomicsSettings } from './schema/economics';
import { ilsToAgorot, recommendedRetailIls, usdToCents } from './pricing';

export const AXIS_IDS = ['size', 'length', 'width', 'color', 'pattern', 'finish', 'style', 'set', 'other'] as const;
export type AxisId = (typeof AXIS_IDS)[number];
export type CardOptions = NonNullable<ProductCard['options']>;

/**
 * The options in the public catalog, compact (the catalog is in the JS bundle: 80 KB budget): per SKU the index of its
 * value on each axis, its price, and a few exceptions. The variant id is derived, never shipped: optionVariantId.
 * The web expands it once (expandOptions) into the shape the components use.
 */
export const PublicOptionsSchema = z.object({
  /** values as [id, label_he, hex | null] */
  axes: z
    .array(z.object({ id: z.enum(AXIS_IDS), name_he: z.string(), values: z.array(z.tuple([z.string(), z.string(), z.string().nullable()])).min(1) }))
    .min(1),
  /** per SKU, the index of its value on each axis, in the axes' order */
  v: z.array(z.array(z.number().int().min(0))).min(2),
  /** price per SKU, agorot incl. VAT */
  p: z.array(z.number().int().positive()),
  /** index of the room's SKU (default_sku): the default selection */
  room: z.number().int().min(0),
  /** SKUs out of stock at the supplier */
  off: z.array(z.number().int().min(0)),
  /** provisional price: the flag of every SKU, and the SKUs that are the other way */
  pv: z.boolean(),
  px: z.array(z.number().int().min(0)),
  /** one piece of a set, per SKU (P1); null when the product is not a set sold singly */
  u: z.array(z.number().int().positive()).nullable(),
  /** a SKU's own shipping days where they differ from the product's; null when none differ */
  d: z.array(z.tuple([z.number(), z.number()]).nullable()).nullable(),
});
export type PublicOptions = z.infer<typeof PublicOptionsSchema>;

/** Our variant id for a supplier option: the product and its value ids ("<product id>:beige+45x45"). */
export const optionVariantId = (productId: string, valueIds: string[]): string => `${productId}:${valueIds.join('+')}`;

export type OptionSku = {
  variant_id: string;
  values: Record<string, string>;
  price_agorot: number;
  price_provisional: boolean;
  unit_price_agorot: number | null;
  /** null: the product's shipping days */
  shipping_days: [number, number] | null;
  available: boolean;
  in_room: boolean;
};
export type ExpandedOptions = {
  axes: { id: AxisId; name_he: string; values: { id: string; label_he: string; hex: string | null }[] }[];
  skus: OptionSku[];
  default_variant: string;
};

export function expandOptions(productId: string, o: PublicOptions): ExpandedOptions {
  const axes = o.axes.map((a) => ({ id: a.id, name_he: a.name_he, values: a.values.map(([id, label_he, hex]) => ({ id, label_he, hex })) }));
  const off = new Set(o.off);
  const px = new Set(o.px);
  const skus = o.v.map((ix, i) => {
    const ids = ix.map((k, j) => axes[j]!.values[k]!.id);
    return {
      variant_id: optionVariantId(productId, ids),
      values: Object.fromEntries(axes.map((a, j) => [a.id, ids[j]!])),
      price_agorot: o.p[i]!,
      price_provisional: px.has(i) ? !o.pv : o.pv,
      unit_price_agorot: o.u?.[i] ?? null,
      shipping_days: o.d?.[i] ?? null,
      available: !off.has(i),
      in_room: i === o.room,
    };
  });
  return { axes, skus, default_variant: skus[o.room]!.variant_id };
}
export type CardSku = CardOptions['skus'][number];

/** Problems the schema cannot catch: references between axes and SKUs, duplicates, the room's SKU. */
export function optionIssues(o: CardOptions): string[] {
  const issues: string[] = [];
  const values = new Map<string, Set<string>>();
  for (const a of o.axes) {
    if (values.has(a.id)) issues.push(`axis ${a.id} twice`);
    const ids = new Set<string>();
    for (const v of a.values) {
      if (ids.has(v.id)) issues.push(`axis ${a.id}: value ${v.id} twice`);
      ids.add(v.id);
    }
    values.set(a.id, ids);
  }
  const skuIds = new Set<string>();
  const combos = new Map<string, string>();
  for (const s of o.skus) {
    if (skuIds.has(s.id)) issues.push(`sku ${s.id} twice`);
    skuIds.add(s.id);
    for (const [axis, ids] of values) {
      const v = s.values[axis as AxisId];
      if (v === undefined) issues.push(`sku ${s.id}: no value for ${axis}`);
      else if (!ids.has(v)) issues.push(`sku ${s.id}: ${axis}=${v} is not a value of the axis`);
    }
    for (const k of Object.keys(s.values)) if (!values.has(k)) issues.push(`sku ${s.id}: no axis ${k}`);
    const combo = o.axes.map((a) => s.values[a.id] ?? '').join('|');
    if (combos.has(combo)) issues.push(`sku ${s.id}: same values as ${combos.get(combo)}`);
    combos.set(combo, s.id);
    if (s.in_room && s.id !== o.default_sku) issues.push(`sku ${s.id}: in_room but not default_sku`);
  }
  if (!skuIds.has(o.default_sku)) issues.push(`default_sku ${o.default_sku} is not a SKU`);
  return issues;
}

/**
 * The SKU's supplier cost in the card's own terms (USD cents). The room's SKU costs exactly the card's price. When the
 * card is priced as a set of k pieces of the room's SKU (card = k × SKU), every SKU keeps that factor; when prices
 * moved since the card was written, the card's price stays and the others keep the supplier's difference.
 */
export function skuCostCents(cardCents: number, defaultSkuCents: number, skuCents: number): number {
  if (!(defaultSkuCents > 0)) return skuCents;
  if (Math.abs(cardCents - defaultSkuCents) <= Math.max(1, cardCents * 0.005)) return skuCents;
  const ratio = cardCents / defaultSkuCents;
  const k = Math.round(ratio);
  if (k >= 2 && Math.abs(ratio - k) <= 0.02 * k) return skuCents * k;
  return Math.max(0, cardCents + (skuCents - defaultSkuCents));
}

type ShipQuote = { amount: number; currency: string } | null | undefined;

/** Shipping per SKU (USD cents): the product's resolved shipping, plus the supplier's difference to the room's SKU. */
export function skuShippingCents(productShipCents: number, defaultQuote: ShipQuote, skuQuote: ShipQuote): number {
  if (!defaultQuote || !skuQuote || defaultQuote.currency !== 'USD' || skuQuote.currency !== 'USD') return productShipCents;
  return Math.max(0, productShipCents + usdToCents(skuQuote.amount) - usdToCents(defaultQuote.amount));
}

export type SkuRetailInput = {
  /** the room's SKU (default_sku): it is the product, and costs the product's price */
  is_default: boolean;
  product_retail_agorot: number;
  product_price_provisional: boolean;
  /** the studio's retail_ils for the product (the room's SKU), null when the price is the economics' recommendation */
  studio_retail_ils: number | null;
  /** the studio's own price for this SKU (products.json `sku_retail_ils`), when set */
  sku_override_ils: number | null;
  cost_usd_cents: number;
  shipping_usd_cents: number;
  default_cost_usd_cents: number;
  default_shipping_usd_cents: number;
  fx_usd_ils: number;
  sell_qty: number;
  /** production rule: only prices the studio set are sold */
  strict: boolean;
};

/**
 * Retail (agorot, incl. VAT) of one SKU, by the same economics as the product's main price: recommendedRetailIls on the
 * SKU's own cost and shipping, rounded up to "…9". When the studio set the product's price by hand, the other SKUs keep
 * the studio's distance from the recommendation. null: not sold (strict build without a studio price, or no margin).
 */
export function skuRetail(i: SkuRetailInput, s: EconomicsSettings): { retail_agorot: number; provisional: boolean } | null {
  if (i.is_default) return { retail_agorot: i.product_retail_agorot, provisional: i.product_price_provisional };
  if (typeof i.sku_override_ils === 'number' && i.sku_override_ils > 0) return { retail_agorot: ilsToAgorot(i.sku_override_ils), provisional: false };
  if (i.strict) return null;
  const rec = recommendedRetailIls(
    { cost_usd_cents: i.cost_usd_cents, shipping_usd_cents: i.shipping_usd_cents, fx_usd_ils: i.fx_usd_ils, sell_qty: i.sell_qty },
    s,
  );
  if (rec === null) return null;
  if (i.studio_retail_ils !== null) {
    const recDefault = recommendedRetailIls(
      { cost_usd_cents: i.default_cost_usd_cents, shipping_usd_cents: i.default_shipping_usd_cents, fx_usd_ils: i.fx_usd_ils, sell_qty: i.sell_qty },
      s,
    );
    const shifted = recDefault === null ? rec : rec + (i.studio_retail_ils - recDefault);
    return { retail_agorot: ilsToAgorot(shifted > 0 ? shifted : rec), provisional: true };
  }
  return { retail_agorot: ilsToAgorot(rec), provisional: true };
}

// ---------- the picker (product page) ----------

export type PickerSku = { variant_id: string; values: Partial<Record<string, string>>; available: boolean };
export type PickerAxis = { id: string; values: { id: string }[] };

/** SKUs that match the chosen values on the first `upTo` axes. */
function matching<T extends PickerSku>(skus: T[], sel: Record<string, string>, axes: PickerAxis[], upTo: number): T[] {
  return skus.filter((s) => axes.slice(0, upTo).every((a) => s.values[a.id] === sel[a.id]));
}

/**
 * Which values of axis `index` can be chosen, given the choices on the axes before it (a cascade: the first axis is
 * free, each next one offers only what exists with the ones above, so a customer can always reach every SKU).
 * A value whose SKUs are all out of stock is not available either.
 */
export function availableValues(axes: PickerAxis[], skus: PickerSku[], sel: Record<string, string>, index: number): Set<string> {
  const pool = matching(skus, sel, axes, index);
  return new Set(pool.filter((s) => s.available).map((s) => s.values[axes[index]!.id]!));
}

/**
 * The selection after the customer chose `value` on axis `index`: the axes after it keep their value when it still
 * exists, else take the first available one. Returns the selection and the SKU it names (null if none exists).
 */
export function pickSku<T extends PickerSku>(
  axes: PickerAxis[],
  skus: T[],
  sel: Record<string, string>,
  index: number,
  value: string,
): { sel: Record<string, string>; sku: T | null } {
  const next = { ...sel, [axes[index]!.id]: value };
  for (let j = index + 1; j < axes.length; j++) {
    const ok = availableValues(axes, skus, next, j);
    const id = axes[j]!.id;
    if (!ok.has(next[id]!)) {
      const first = axes[j]!.values.find((v) => ok.has(v.id)) ?? axes[j]!.values.find((v) => matching(skus, next, axes, j).some((s) => s.values[id] === v.id));
      if (first) next[id] = first.id;
    }
  }
  const sku = skus.find((s) => axes.every((a) => s.values[a.id] === next[a.id])) ?? null;
  return { sel: next, sku };
}

/** The selection that names a SKU (the default selection is the room's SKU). */
export function selectionOf(axes: PickerAxis[], sku: PickerSku): Record<string, string> {
  return Object.fromEntries(axes.map((a) => [a.id, sku.values[a.id]!]));
}
