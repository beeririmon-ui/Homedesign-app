/**
 * Pricing and unit economics. All money is integer minor units: agorot for ILS, cents for USD.
 * The formulas are the studio's (`econCalc` in studio/src/index.html, studio/README.md "רווחיות"), and the same
 * formulas run in the catalog build, the API (order snapshots, admin) and the D1 view `v_product_economics`.
 * Tests keep them in agreement; scripts/economics/no_loss.py checks the site's output against them (--check-site).
 *
 * Per unit sold, retail price R includes VAT, q = sell_qty (supplier units per unit sold):
 *   net            = R / (1 + vat)
 *   freight(q)     = the studio's combined parcel (shipForQty): unit + (q − 1) × max(0, unit − 3.72) USD, or the
 *                    supplier's own quote when it was given for exactly q pieces (shipping_quoted_for_sale)
 *   landed (cogs)  = (supplier cost × q + freight(q)) USD × fx
 *   payment fee    = R × fee_rate + fee_fixed          (fees are charged on the gross amount)
 *   returns        = net × returns_reserve_rate
 *   packaging      = packaging per unit
 *   contribution   = net − landed − payment fee − returns − packaging
 *   margin         = contribution / net
 *   after CAC      = contribution − CAC / items_per_order
 *
 * No product loses (studio rules ה.13, 2026-10-20; SITE1, 2026-11-03): every price the site shows is at least the
 * price at which its own scenario's contribution is zero, rounded up to a price ending in 9 (noLossRetailIls).
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

/** The studio's fixed part of one parcel (USD cents): the second piece in the same parcel saves it (freight-bundles.json). */
export const PARCEL_FIXED_USD_CENTS = 372;

/**
 * Freight for q pieces from one piece's quote, by the studio's combined parcel (studio/build.py shipForQty,
 * scripts/economics/no_loss.py ship_for_qty): unit + (q − 1) × max(0, unit − 3.72). Never a parcel per piece.
 */
export function shipForQtyCents(unitCents: number, q: number): number {
  if (!(q > 1)) return unitCents;
  return Math.round(unitCents + (q - 1) * Math.max(0, unitCents - PARCEL_FIXED_USD_CENTS));
}

/** One piece's freight from a quote for n pieces (the combined parcel inverted; no_loss.py inv_ship_for_qty). */
export function unitShipFromSaleCents(saleCents: number, n: number): number {
  if (!(n > 1)) return saleCents;
  const u = (saleCents + (n - 1) * PARCEL_FIXED_USD_CENTS) / n;
  return Math.round(u >= PARCEL_FIXED_USD_CENTS ? u : saleCents);
}

export type CostInput = {
  cost_usd_cents: number;
  /** freight of ONE piece by the default method; or of the whole sale when shipping_quoted_for_sale is true */
  shipping_usd_cents: number;
  fx_usd_ils: number;
  sell_qty?: number;
  /** the supplier quoted exactly the sale's pieces (freight-<supplier>.json `qty` = sell_qty): taken as it is */
  shipping_quoted_for_sale?: boolean;
};

/** Freight of the sale in USD cents: the quote for the sale when there is one, else the combined parcel for sell_qty. */
export function saleShippingCents(input: Pick<CostInput, 'shipping_usd_cents' | 'sell_qty' | 'shipping_quoted_for_sale'>): number {
  const q = input.sell_qty ?? 1;
  return input.shipping_quoted_for_sale ? input.shipping_usd_cents : shipForQtyCents(input.shipping_usd_cents, q);
}

/** Landed cost of one sale in agorot (the studio's "עלות נחיתה"): (cost × q + freight(q)) × fx. */
export function landedAgorot(input: CostInput): number {
  const q = input.sell_qty ?? 1;
  return Math.round((input.cost_usd_cents * q + saleShippingCents(input)) * input.fx_usd_ils);
}

/** @deprecated kept for callers that pass one piece's freight and a quantity: the combined parcel, not linear. */
export function cogsAgorot(costUsdCents: number, shippingUsdCents: number, fx: number, sellQty = 1, quotedForSale = false): number {
  return landedAgorot({
    cost_usd_cents: costUsdCents,
    shipping_usd_cents: shippingUsdCents,
    fx_usd_ils: fx,
    sell_qty: sellQty,
    shipping_quoted_for_sale: quotedForSale,
  });
}

export function unitEconomics(input: CostInput & { retail_agorot: number }, s: EconomicsSettings): UnitEconomics {
  const R = input.retail_agorot;
  const net = Math.round(R / (1 + s.vat_rate));
  const cogs = landedAgorot(input);
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
  const up = Math.ceil(ils - 1e-9);
  const r = up % 10;
  return r === 9 ? up : up + ((9 - r + 10) % 10);
}

/**
 * The lowest retail price (incl. VAT, rounded to a "…9" price) that reaches the target margin (the studio's
 * "מחיר מומלץ", then charm-rounded). Used for the distance a hand-set product price keeps on its other options
 * (shared/src/options.ts skuRetail), never as a price of its own since SITE1 (2026-11-03).
 * Returns null when the target is unreachable with the given fee/reserve settings.
 */
export function recommendedRetailIls(input: CostInput, s: EconomicsSettings): number | null {
  const landedIls = landedAgorot(input) / 100;
  const denom = (1 - s.returns_reserve_rate - s.target_margin_rate) / (1 + s.vat_rate) - s.payment_fee_rate;
  if (denom <= 0) return null;
  return charmRoundUpIls((landedIls + s.payment_fee_fixed_ils + s.packaging_ils) / denom);
}

/** The (continuous) price whose contribution is exactly zero for a landed cost (no_loss.py break_even_for). */
export function breakEvenIls(landedIls: number, s: EconomicsSettings): number {
  const k = (1 - s.returns_reserve_rate) / (1 + s.vat_rate) - s.payment_fee_rate;
  return (landedIls + s.payment_fee_fixed_ils + s.packaging_ils) / k;
}

/**
 * The no-loss price of one scenario (studio rules ה.13): the lowest price ending in 9 whose contribution is not negative
 * for this landed cost. Every price the site derives (an option, one piece of a set) is floored at its own.
 */
export function noLossRetailIls(landedIls: number, s: EconomicsSettings): number {
  return charmRoundUpIls(breakEvenIls(landedIls, s));
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
