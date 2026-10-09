/**
 * Pricing and unit economics. All money is integer minor units: agorot for ILS, cents for USD.
 * The same formulas run in the catalog build, the API (order snapshots, admin) and the D1 view
 * `v_product_economics` (api/migrations), and the tests keep them in agreement.
 *
 * Per unit, retail price R includes VAT:
 *   net            = R / (1 + vat)
 *   vat            = R - net
 *   cogs           = (supplier cost + shipping) in USD × fx
 *   payment fee    = R × fee_rate + fee_fixed          (fees are charged on the gross amount)
 *   returns        = net × returns_reserve_rate
 *   contribution   = net - cogs - payment fee - returns
 *   margin         = contribution / net
 *   after CAC      = contribution - CAC                (CAC is per order; shown per single-item order)
 */
import type { EconomicsSettings } from './schema/economics';

export type UnitEconomics = {
  retail_agorot: number;
  net_agorot: number;
  vat_agorot: number;
  cogs_agorot: number;
  payment_fee_agorot: number;
  returns_reserve_agorot: number;
  contribution_agorot: number;
  margin_rate: number;
  contribution_after_cac_agorot: number;
  meets_target: boolean;
};

export const usdToCents = (usd: number): number => Math.round(usd * 100);
export const ilsToAgorot = (ils: number): number => Math.round(ils * 100);

export function cogsAgorot(costUsdCents: number, shippingUsdCents: number, fx: number): number {
  return Math.round((costUsdCents + shippingUsdCents) * fx);
}

export function unitEconomics(
  input: { retail_agorot: number; cost_usd_cents: number; shipping_usd_cents: number; fx_usd_ils: number },
  s: EconomicsSettings,
): UnitEconomics {
  const R = input.retail_agorot;
  const net = Math.round(R / (1 + s.vat_rate));
  const cogs = cogsAgorot(input.cost_usd_cents, input.shipping_usd_cents, input.fx_usd_ils);
  const fee = Math.round(R * s.payment_fee_rate + s.payment_fee_fixed_ils * 100);
  const reserve = Math.round(net * s.returns_reserve_rate);
  const contribution = net - cogs - fee - reserve;
  const margin = net > 0 ? contribution / net : 0;
  return {
    retail_agorot: R,
    net_agorot: net,
    vat_agorot: R - net,
    cogs_agorot: cogs,
    payment_fee_agorot: fee,
    returns_reserve_agorot: reserve,
    contribution_agorot: contribution,
    margin_rate: Math.round(margin * 10000) / 10000,
    contribution_after_cac_agorot: contribution - Math.round(s.cac_ils * 100),
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
 * The lowest retail price (incl. VAT, rounded to a "…9" price) that reaches the target margin.
 * Used only for provisional prices in development and preview builds. Returns null when the target is
 * unreachable with the given fee/reserve settings.
 */
export function recommendedRetailIls(
  input: { cost_usd_cents: number; shipping_usd_cents: number; fx_usd_ils: number },
  s: EconomicsSettings,
): number | null {
  const cogsIls = cogsAgorot(input.cost_usd_cents, input.shipping_usd_cents, input.fx_usd_ils) / 100;
  const denom = (1 - s.returns_reserve_rate - s.target_margin_rate) / (1 + s.vat_rate) - s.payment_fee_rate;
  if (denom <= 0) return null;
  return charmRoundUpIls((cogsIls + s.payment_fee_fixed_ils) / denom);
}
