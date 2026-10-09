/**
 * Pricing and unit economics. All money is integer minor units: agorot for ILS, cents for USD.
 * The formulas are the studio's (`econCalc` in studio/src/index.html, studio/README.md "רווחיות"), and the same
 * formulas run in the catalog build, the API (order snapshots, admin) and the D1 view `v_product_economics`.
 * Tests keep them in agreement.
 *
 * Per unit sold, retail price R includes VAT, q = sell_qty (supplier units per unit sold):
 *   net            = R / (1 + vat)
 *   landed (cogs)  = (supplier cost + shipping) in USD × q × fx
 *   payment fee    = R × fee_rate + fee_fixed          (fees are charged on the gross amount)
 *   returns        = net × returns_reserve_rate
 *   packaging      = packaging per unit
 *   contribution   = net − landed − payment fee − returns − packaging
 *   margin         = contribution / net
 *   after CAC      = contribution − CAC / items_per_order
 */
import type { EconomicsSettings } from './schema/economics';

export type UnitEconomics = {
  retail_agorot: number;
  net_agorot: number;
  vat_agorot: number;
  cogs_agorot: number;
  payment_fee_agorot: number;
  returns_reserve_agorot: number;
  packaging_agorot: number;
  contribution_agorot: number;
  margin_rate: number;
  contribution_after_cac_agorot: number;
  meets_target: boolean;
};

export const usdToCents = (usd: number): number => Math.round(usd * 100);
export const ilsToAgorot = (ils: number): number => Math.round(ils * 100);

export type CostInput = { cost_usd_cents: number; shipping_usd_cents: number; fx_usd_ils: number; sell_qty?: number };

export function cogsAgorot(costUsdCents: number, shippingUsdCents: number, fx: number, sellQty = 1): number {
  return Math.round((costUsdCents + shippingUsdCents) * sellQty * fx);
}

export function unitEconomics(input: CostInput & { retail_agorot: number }, s: EconomicsSettings): UnitEconomics {
  const R = input.retail_agorot;
  const net = Math.round(R / (1 + s.vat_rate));
  const cogs = cogsAgorot(input.cost_usd_cents, input.shipping_usd_cents, input.fx_usd_ils, input.sell_qty ?? 1);
  const fee = Math.round(R * s.payment_fee_rate + s.payment_fee_fixed_ils * 100);
  const reserve = Math.round(net * s.returns_reserve_rate);
  const pack = Math.round(s.packaging_ils * 100);
  const contribution = net - cogs - fee - reserve - pack;
  const margin = net > 0 ? contribution / net : 0;
  const cacPerItem = Math.round((s.cac_ils * 100) / (s.items_per_order > 0 ? s.items_per_order : 1));
  return {
    retail_agorot: R,
    net_agorot: net,
    vat_agorot: R - net,
    cogs_agorot: cogs,
    payment_fee_agorot: fee,
    returns_reserve_agorot: reserve,
    packaging_agorot: pack,
    contribution_agorot: contribution,
    margin_rate: Math.round(margin * 10000) / 10000,
    contribution_after_cac_agorot: contribution - cacPerItem,
    meets_target: margin >= s.target_margin_rate,
  };
}

/** Rounds a shekel amount up to the next whole price that ends in 9 (e.g. 183.2 → 189, 190 → 199). */
export function charmRoundUpIls(ils: number): number {
  const up = Math.ceil(ils);
  const r = up % 10;
  return r === 9 ? up : up + ((9 - r + 10) % 10);
}

/**
 * The lowest retail price (incl. VAT, rounded to a "…9" price) that reaches the target margin (the studio's
 * "מחיר מומלץ", then charm-rounded). Used only for provisional prices in development and preview builds.
 * Returns null when the target is unreachable with the given fee/reserve settings.
 */
export function recommendedRetailIls(input: CostInput, s: EconomicsSettings): number | null {
  const landedIls = cogsAgorot(input.cost_usd_cents, input.shipping_usd_cents, input.fx_usd_ils, input.sell_qty ?? 1) / 100;
  const denom = (1 - s.returns_reserve_rate - s.target_margin_rate) / (1 + s.vat_rate) - s.payment_fee_rate;
  if (denom <= 0) return null;
  return charmRoundUpIls((landedIls + s.payment_fee_fixed_ils + s.packaging_ils) / denom);
}

export type ShippingMethod = 'economy' | 'express';

/** What the customer pays for shipping. Economy is free at or above the threshold; express is always charged. */
export function customerShippingAgorot(
  method: ShippingMethod,
  subtotalAgorot: number,
  s: Pick<EconomicsSettings, 'shipping_fee_economy_ils' | 'shipping_fee_express_ils' | 'free_shipping_threshold_ils'>,
): number {
  if (method === 'express') return ilsToAgorot(s.shipping_fee_express_ils);
  if (s.free_shipping_threshold_ils !== null && subtotalAgorot >= ilsToAgorot(s.free_shipping_threshold_ils)) return 0;
  return ilsToAgorot(s.shipping_fee_economy_ils);
}
