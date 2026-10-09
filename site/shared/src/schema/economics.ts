/**
 * Economics inputs synced by the manager from the studio patches:
 *   data/economics/settings.json  · global settings (FX, VAT, fees, reserve, CAC, target margin)
 *   data/economics/products.json  · per product id: shipping_cost_usd, retail_ils, compare_at_ils
 * Both files are optional for the build. Missing values fall back to DEFAULT_SETTINGS, and every fallback is
 * reported in `defaults_used` so nothing provisional reaches production silently.
 */
import { z } from 'zod';

const Rate = z.number().min(0).max(1);
const NonNeg = z.number().min(0);

export const EconomicsSettingsInputSchema = z.looseObject({
  fx_usd_ils: NonNeg.optional(),
  vat_rate: Rate.optional(),
  payment_fee_rate: Rate.optional(),
  payment_fee_fixed_ils: NonNeg.optional(),
  returns_reserve_rate: Rate.optional(),
  cac_ils: NonNeg.optional(),
  target_margin_rate: Rate.optional(),
  default_shipping_usd: NonNeg.optional(),
  updated_at: z.string().optional(),
});

export const ProductEconomicsSchema = z.looseObject({
  shipping_cost_usd: NonNeg.nullable().optional(),
  retail_ils: NonNeg.nullable().optional(),
  compare_at_ils: NonNeg.nullable().optional(),
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

export type EconomicsSettings = {
  fx_usd_ils: number;
  vat_rate: number;
  payment_fee_rate: number;
  payment_fee_fixed_ils: number;
  returns_reserve_rate: number;
  cac_ils: number;
  target_margin_rate: number;
  default_shipping_usd: number;
};

/**
 * Provisional defaults (not verified, not approved). VAT 18% is the Israeli rate stated by the user (2026-10-09);
 * everything else is a placeholder until data/economics/settings.json exists.
 */
export const DEFAULT_SETTINGS: EconomicsSettings = {
  fx_usd_ils: 3.7,
  vat_rate: 0.18,
  payment_fee_rate: 0.02,
  payment_fee_fixed_ils: 0,
  returns_reserve_rate: 0.05,
  cac_ils: 40,
  target_margin_rate: 0.35,
  default_shipping_usd: 10,
};

export function resolveSettings(input: z.infer<typeof EconomicsSettingsInputSchema> | null): {
  settings: EconomicsSettings;
  defaults_used: (keyof EconomicsSettings)[];
} {
  const settings = { ...DEFAULT_SETTINGS };
  const defaults_used: (keyof EconomicsSettings)[] = [];
  for (const key of Object.keys(DEFAULT_SETTINGS) as (keyof EconomicsSettings)[]) {
    const v = input?.[key];
    if (typeof v === 'number') settings[key] = v;
    else defaults_used.push(key);
  }
  return { settings, defaults_used };
}
