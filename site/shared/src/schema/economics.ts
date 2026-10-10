/**
 * Economics inputs. The studio back-office (studio/) edits them, and studio/apply_edits.py syncs them to:
 *   data/economics/settings.json  · { economics: {usd_ils, vat_pct, card_pct, ...}, budget, storefront? }
 *   data/economics/products.json  · { products: { <id>: {shipping_cost_usd, retail_ils, compare_at_ils, sell_qty?, unit_retail_ils?, fulfillment_source?} } }
 *   data/economics/freight-cj.json · CJ freight quotes per product (fallback when there is no manual shipping cost)
 * All files are optional for the build. Missing values fall back to DEFAULT_SETTINGS (the studio's defaults), and every
 * fallback is reported in `defaults_used` so nothing provisional reaches production silently.
 */
import { z } from 'zod';

const NonNeg = z.number().min(0);

/** The studio's `settings/economics` document (percent values are whole numbers: 18 = 18%). */
export const StudioEconomicsSchema = z.looseObject({
  usd_ils: NonNeg.optional(),
  shipping_method: z.enum(['cheapest', 'under20']).optional(),
  vat_pct: z.number().min(0).max(100).optional(),
  card_pct: z.number().min(0).max(100).optional(),
  card_fixed_ils: NonNeg.optional(),
  returns_pct: z.number().min(0).max(100).optional(),
  cac_ils: NonNeg.optional(),
  packaging_ils: NonNeg.optional(),
  target_margin_pct: z.number().min(0).max(100).optional(),
  items_per_order: z.number().positive().optional(),
  bundle_factor: z.number().positive().optional(),
});

/** Storefront settings (customer-facing shipping fees). Not in the studio yet: an optional `storefront` block. */
export const StorefrontInputSchema = z.looseObject({
  shipping_fee_economy_ils: NonNeg.optional(),
  shipping_fee_express_ils: NonNeg.optional(),
  free_shipping_threshold_ils: NonNeg.nullable().optional(),
  default_shipping_usd: NonNeg.optional(),
});

export const SettingsFileSchema = z.looseObject({
  economics: StudioEconomicsSchema.nullable().optional(),
  storefront: StorefrontInputSchema.nullable().optional(),
});
export type SettingsFile = z.infer<typeof SettingsFileSchema>;

export const FULFILLMENT_SOURCES = ['dropship_cj', 'il_3pl'] as const;
export type FulfillmentSource = (typeof FULFILLMENT_SOURCES)[number];

export const ProductEconomicsSchema = z.looseObject({
  shipping_cost_usd: NonNeg.nullable().optional(),
  retail_ils: NonNeg.nullable().optional(),
  compare_at_ils: NonNeg.nullable().optional(),
  /** Supplier units shipped per unit sold (e.g. a "set of 2" bought as two singles). Default 1. */
  sell_qty: z.number().int().min(1).max(50).nullable().optional(),
  /** Price of one piece when a set (sell_qty > 1) is also sold singly (P1). Without it the site shows an estimate. */
  unit_retail_ils: NonNeg.nullable().optional(),
  fulfillment_source: z.enum(FULFILLMENT_SOURCES).nullable().optional(),
});
export type ProductEconomics = z.infer<typeof ProductEconomicsSchema>;

/** Accepts either `{ "<id>": {...} }` or `{ "products": { "<id>": {...} } }`. */
export const ProductEconomicsFileSchema = z.preprocess(
  (raw) =>
    raw && typeof raw === 'object' && 'products' in raw && typeof (raw as { products: unknown }).products === 'object'
      ? (raw as { products: unknown }).products
      : raw,
  z.record(z.string(), ProductEconomicsSchema),
);

const Quote = z.looseObject({ name: z.string(), days: z.string().optional(), usd: z.number() });
export const FreightFileSchema = z.looseObject({
  updated: z.string().optional(),
  products: z.record(
    z.string(),
    z.looseObject({
      cheapest: Quote.nullable().optional(),
      cheapest_under_20d: Quote.nullable().optional(),
      checked_at: z.string().optional(),
      status: z.string().optional(),
    }),
  ),
});
export type FreightFile = z.infer<typeof FreightFileSchema>;

export type EconomicsSettings = {
  fx_usd_ils: number;
  /** which CJ quote feeds landed cost when there is no manual shipping cost */
  freight_method: 'cheapest' | 'under20';
  vat_rate: number;
  payment_fee_rate: number;
  payment_fee_fixed_ils: number;
  returns_reserve_rate: number;
  cac_ils: number;
  packaging_ils: number;
  target_margin_rate: number;
  items_per_order: number;
  bundle_factor: number;
  /** last resort when neither a manual cost nor a CJ quote exists */
  default_shipping_usd: number;
  /** customer-facing shipping (storefront) */
  shipping_fee_economy_ils: number;
  shipping_fee_express_ils: number;
  /** economy shipping is free at or above this subtotal (incl. VAT); null = never free */
  free_shipping_threshold_ils: number | null;
};

/**
 * Provisional defaults. The economics values are the studio's defaults (studio/README.md, "רווחיות"); VAT 18% was
 * stated by the user. The storefront values follow the fulfillment research (₪10–30 shipping, free over ₪199–349)
 * and are not approved: decision E1 is open.
 */
export const DEFAULT_SETTINGS: EconomicsSettings = {
  fx_usd_ils: 3.7,
  freight_method: 'cheapest',
  vat_rate: 0.18,
  payment_fee_rate: 0.02,
  payment_fee_fixed_ils: 1.2,
  returns_reserve_rate: 0.05,
  cac_ils: 40,
  packaging_ils: 0,
  target_margin_rate: 0.35,
  items_per_order: 1.4,
  bundle_factor: 1,
  default_shipping_usd: 17,
  shipping_fee_economy_ils: 29,
  shipping_fee_express_ils: 59,
  free_shipping_threshold_ils: 299,
};

const pct = (v: number | undefined) => (typeof v === 'number' ? Math.round(v * 10) / 1000 : undefined);

export function resolveSettings(file: SettingsFile | null): {
  settings: EconomicsSettings;
  defaults_used: (keyof EconomicsSettings)[];
} {
  const e = file?.economics ?? {};
  const sf = file?.storefront ?? {};
  const given: Partial<Record<keyof EconomicsSettings, unknown>> = {
    fx_usd_ils: e.usd_ils,
    freight_method: e.shipping_method,
    vat_rate: pct(e.vat_pct),
    payment_fee_rate: pct(e.card_pct),
    payment_fee_fixed_ils: e.card_fixed_ils,
    returns_reserve_rate: pct(e.returns_pct),
    cac_ils: e.cac_ils,
    packaging_ils: e.packaging_ils,
    target_margin_rate: pct(e.target_margin_pct),
    items_per_order: e.items_per_order,
    bundle_factor: e.bundle_factor,
    default_shipping_usd: sf.default_shipping_usd,
    shipping_fee_economy_ils: sf.shipping_fee_economy_ils,
    shipping_fee_express_ils: sf.shipping_fee_express_ils,
    free_shipping_threshold_ils: sf.free_shipping_threshold_ils,
  };
  const settings = { ...DEFAULT_SETTINGS } as Record<keyof EconomicsSettings, unknown>;
  const defaults_used: (keyof EconomicsSettings)[] = [];
  for (const key of Object.keys(DEFAULT_SETTINGS) as (keyof EconomicsSettings)[]) {
    const v = given[key];
    const present = key === 'free_shipping_threshold_ils' ? v !== undefined : v !== undefined && v !== null;
    if (present) settings[key] = v;
    else defaults_used.push(key);
  }
  return { settings: settings as EconomicsSettings, defaults_used };
}

/** Shipping cost per unit sold, in USD: manual (studio) → CJ quote for the chosen method → default. */
export function resolveShippingUsd(
  id: string,
  manual: number | null | undefined,
  freight: FreightFile | null,
  s: EconomicsSettings,
): { usd: number; source: 'manual' | 'cj' | 'default'; checked_at: string | null } {
  if (typeof manual === 'number') return { usd: manual, source: 'manual', checked_at: null };
  const f = freight?.products[id];
  const q = s.freight_method === 'under20' ? f?.cheapest_under_20d : f?.cheapest;
  if (q && typeof q.usd === 'number') return { usd: q.usd, source: 'cj', checked_at: f?.checked_at ?? null };
  return { usd: s.default_shipping_usd, source: 'default', checked_at: null };
}
