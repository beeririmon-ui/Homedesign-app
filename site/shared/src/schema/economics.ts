/**
 * Economics inputs. The studio back-office (studio/) edits them, and studio/apply_edits.py syncs them to:
 *   data/economics/settings.json  · { economics: {usd_ils, vat_pct, card_pct, ...}, budget, storefront? }
 *   data/economics/products.json  · { products: { <id>: {shipping_cost_usd, retail_ils, compare_at_ils, sell_qty?, unit_retail_ils?, fulfillment_source?, sku_retail_ils?} } }
 *   data/economics/freight-<supplier>.json · freight quotes per product (cj, zendrop, aliexpress)
 * All files are optional for the build. Missing settings fall back to DEFAULT_SETTINGS (the studio's defaults), and every
 * fallback is reported in `defaults_used` so nothing provisional reaches production silently.
 *
 * Shipping (SITE1, 2026-11-03, economics parity with studio/build.py load_economics): the studio's manual figure, then the
 * supplier's own freight file, then any freight file that has the product, then the room SKU's shipping_il in the card,
 * then the cached supplier answer for the room SKU (what the no-loss audit priced from), then (only for a card without a
 * pricing row) the final-round record. A product with no line at all is NOT given a default: it is reported and not sold
 * (resolveShipping returns ok: false). The method is the default one we ship with
 * (scripts/economics/no_loss.py default_quote): the cheapest standard line; a product whose only lines are express is
 * "express only" (not sold, decision NL2).
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
});

export const SettingsFileSchema = z.looseObject({
  economics: StudioEconomicsSchema.nullable().optional(),
  storefront: StorefrontInputSchema.nullable().optional(),
});
export type SettingsFile = z.infer<typeof SettingsFileSchema>;

export const FULFILLMENT_SOURCES = ['dropship_cj', 'il_3pl'] as const;
export type FulfillmentSource = (typeof FULFILLMENT_SOURCES)[number];

/** The pricing team's Israeli comparables (data/economics/products.json il_value). */
export const IlValueSchema = z.looseObject({
  low: z.number().optional(),
  typical: z.number().optional(),
  high: z.number().optional(),
  comps: z.array(z.looseObject({ price: z.number().nullable().optional(), title: z.string().nullable().optional() })).optional(),
});

export const ProductEconomicsSchema = z.looseObject({
  shipping_cost_usd: NonNeg.nullable().optional(),
  /** part of shipping_cost_usd that is really product cost (older rows); unfolded when sale_cost_usd is set */
  shipping_includes_usd: NonNeg.nullable().optional(),
  retail_ils: NonNeg.nullable().optional(),
  /** where the price came from: "studio" = the owner set it by hand; "initial-..." = a starting price, not approved */
  retail_src: z.string().nullable().optional(),
  compare_at_ils: NonNeg.nullable().optional(),
  /** Supplier units shipped per unit sold (e.g. a "set of 2" bought as two singles). Default 1. */
  sell_qty: z.number().int().min(1).max(50).nullable().optional(),
  /**
   * The cost of the whole sale in USD when it is not sell_qty x the card's cost (2026-10-18): a shade with its certified
   * suspension set, a pitcher with its jar. It replaces the card's cost; shipping_cost_usd is then shipping only.
   */
  sale_cost_usd: NonNeg.nullable().optional(),
  /** Price of one piece when a set (sell_qty > 1) is also sold singly (P1). Without it the site shows an estimate. */
  unit_retail_ils: NonNeg.nullable().optional(),
  fulfillment_source: z.enum(FULFILLMENT_SOURCES).nullable().optional(),
  /**
   * The studio's own price for supplier options other than the room's (card `options`, 2026-10-11), by supplier SKU id.
   * Without it the site prices an option by the economics (provisional); a strict build sells only priced options.
   */
  sku_retail_ils: z.record(z.string(), NonNeg).nullable().optional(),
  /** the Israeli comparables the price was set against (ה.10); the highest one drives NL2 */
  il_value: IlValueSchema.nullable().optional(),
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

const Quote = z.looseObject({ name: z.string().nullable().optional(), days: z.string().nullable().optional(), usd: z.number() });
export const FreightEntrySchema = z.looseObject({
  options: z.array(Quote).optional(),
  cheapest: Quote.nullable().optional(),
  cheapest_under_20d: Quote.nullable().optional(),
  checked_at: z.string().optional(),
  status: z.string().nullable().optional(),
  /** the quote is for this many pieces (a set of pegs sold as one unit); absent = one piece */
  qty: z.number().optional(),
});
export type FreightEntry = z.infer<typeof FreightEntrySchema>;
export const FreightFileSchema = z.looseObject({
  updated: z.string().optional(),
  products: z.record(z.string(), FreightEntrySchema),
});
export type FreightFile = z.infer<typeof FreightFileSchema>;

export const FREIGHT_SOURCES = ['cj', 'zendrop', 'aliexpress'] as const;
export type FreightSource = (typeof FREIGHT_SOURCES)[number];
export type FreightFiles = Partial<Record<FreightSource, FreightFile>>;

export type EconomicsSettings = {
  fx_usd_ils: number;
  /** which quote feeds landed cost when there is no manual shipping cost (the studio's setting; the site ships by the default line) */
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
  /** customer-facing shipping (storefront) */
  shipping_fee_economy_ils: number;
  shipping_fee_express_ils: number;
  /** economy shipping is free at or above this subtotal (incl. VAT); null = never free */
  free_shipping_threshold_ils: number | null;
};

/**
 * Provisional defaults. The economics values are the studio's defaults (studio/README.md, "רווחיות"): the conservative
 * assumptions the user chose in decision FR-C (2026-10-10: rate 3.3, returns reserve 8%, CAC ₪100); VAT 18% was
 * stated by the user. The target margin is the 40% floor of decision VR1 (2026-10-11; it was 35%). The storefront
 * values follow the fulfillment research (₪10–30 shipping, free over ₪199–349) and are not approved: decision E1 is open.
 * There is no default shipping cost any more (SITE1): a product without a shipping line is not priced.
 */
export const DEFAULT_SETTINGS: EconomicsSettings = {
  fx_usd_ils: 3.3,
  freight_method: 'cheapest',
  vat_rate: 0.18,
  payment_fee_rate: 0.02,
  payment_fee_fixed_ils: 1.2,
  returns_reserve_rate: 0.08,
  cac_ils: 100,
  packaging_ils: 0,
  target_margin_rate: 0.4,
  items_per_order: 1.4,
  bundle_factor: 1,
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

// ---------- the shipping line of a product (studio/build.py load_economics; no_loss.py default_quote) ----------

/** An express line: DHL, UPS, FedEx, TNT, EMS, Aramex, "Premium", CJ To Door, "...Express" (not AliExpress itself). */
export const EXPRESS_LINE = /\bDHL\b|fedex|\bUPS\b|\bTNT\b|\bEMS\b|aramex|premium|to\s*door|(?<!ali)express/i;
export const isExpressLine = (name: string | null | undefined): boolean => EXPRESS_LINE.test(name ?? '');

/** '6-15', '14' → [6, 15]; null when there is no number. */
export function daysPair(v: string | number | null | undefined): [number, number] | null {
  if (typeof v === 'number' && Number.isFinite(v)) return [v, v];
  if (typeof v !== 'string') return null;
  const ns = (v.match(/\d+/g) ?? []).map(Number);
  return ns.length ? [Math.min(...ns), Math.max(...ns)] : null;
}

export type ShippingLine = { usd: number; name: string | null; days: string | null };

/**
 * The method we ship with by default (no_loss.py default_quote, correction rule 1 of 2026-10-20): the cheapest standard
 * line; an express line only when it is the only kind. null when there is no line with a price.
 */
export function defaultLine(lines: (ShippingLine | null | undefined)[]): { line: ShippingLine; express_only: boolean } | null {
  const ok = lines.filter((l): l is ShippingLine => !!l && typeof l.usd === 'number' && Number.isFinite(l.usd));
  if (!ok.length) return null;
  const std = ok.filter((l) => !isExpressLine(l.name));
  const pool = std.length ? std : ok;
  const line = pool.reduce((a, b) => (b.usd < a.usd ? b : a));
  return { line, express_only: std.length === 0 };
}

/** The supplier family of a card (studio/build.py supplier_key): which freight file is its own. */
export function supplierKey(name: string | null | undefined, url: string | null | undefined, currency?: string | null): FreightSource | 'il' | 'other' {
  const n = (name ?? '').toLowerCase();
  const host = (/^https?:\/\/([^/]+)/.exec(url ?? '')?.[1] ?? '').toLowerCase();
  if (/\bcj\b|cjdropshipping/.test(n) || host.includes('cjdropshipping')) return 'cj';
  if (n.includes('zendrop') || host.includes('zendrop')) return 'zendrop';
  if (n.includes('aliexpress') || host.includes('aliexpress')) return 'aliexpress';
  if ((currency ?? '').toUpperCase() === 'ILS' || host.endsWith('.co.il') || /[֐-׿]/.test(name ?? '')) return 'il';
  return 'other';
}

export type ShippingSource = 'manual' | FreightSource | 'card' | 'cache' | 'leads';
export type ShippingResolution =
  | {
      ok: true;
      /** USD cents of one piece, or of the whole sale when quoted_for_sale */
      usd_cents: number;
      /** the supplier quoted exactly the sale's pieces (sell_qty): taken as it is, not the combined parcel */
      quoted_for_sale: boolean;
      quoted_qty: number | null;
      source: ShippingSource;
      /** the line's name and days, for the record ("CJPacket Eub 12-50") */
      line: string;
      days: [number, number] | null;
      /** the supplier's only lines are express: not sold (NL2) */
      express_only: boolean;
    }
  | { ok: false; reason: 'no_route' | 'no_line'; source: ShippingSource | null };

/** The final-round record of a card (data/leads/final-2026-10-13/results, studio/build.py lead_records). */
export type LeadRecord = { rec: Record<string, unknown>; file: string; date: string };

type CardForShipping = {
  supplier: { name: string; product_url: string };
  price: { currency: string };
  options?: { default_sku: string; skus: { id: string; shipping_il?: { amount: number; currency: string; days?: string | null } }[] } | null;
};

const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);

/** The sale's units from a final-round record: qty_in_sale / qty when ≥ 1 (studio/build.py lead_freight). */
export function leadQty(rec: Record<string, unknown>): number | null {
  for (const k of ['qty_in_sale', 'qty']) {
    const q = num(rec[k]);
    if (q !== null && Number.isInteger(q) && q >= 1) return q;
  }
  return null;
}

/**
 * The shipping line of a product, in the studio's order (load_economics): the manual figure, the supplier's own freight
 * file, then any freight file with the product, then the room SKU's shipping_il in the card, then (a card without a
 * pricing row only) its final-round record. Never a default figure: ok: false says why there is none.
 */
export function resolveShipping(a: {
  id: string;
  card: CardForShipping;
  row: ProductEconomics | undefined;
  freights: FreightFiles;
  /** the cached supplier answer for the room SKU (tools/lib/freight-cache.ts), the no-loss audit's source when the studio has none */
  cache?: { lines: ShippingLine[]; label: string } | null;
  lead: LeadRecord | null;
  sellQty: number;
}): ShippingResolution {
  const row = a.row;
  if (row && typeof row.shipping_cost_usd === 'number') {
    let usd = row.shipping_cost_usd;
    // an older row that folds part of the sale's cost into the shipping while it also has sale_cost_usd: shipping only
    const inc = row.shipping_includes_usd;
    if (typeof row.sale_cost_usd === 'number' && row.sale_cost_usd > 0 && typeof inc === 'number' && inc > 0 && inc <= usd)
      usd = Math.round((usd - inc) * 10000) / 10000;
    return {
      ok: true,
      usd_cents: Math.round(usd * 100),
      quoted_for_sale: false,
      quoted_qty: null,
      source: 'manual',
      line: 'ידני (הסטודיו)',
      days: null,
      express_only: false,
    };
  }
  const own = supplierKey(a.card.supplier.name, a.card.supplier.product_url, a.card.price.currency);
  const order: FreightSource[] = [...(own === 'cj' || own === 'zendrop' || own === 'aliexpress' ? [own] : []), ...FREIGHT_SOURCES.filter((s) => s !== own)];
  for (const src of order) {
    const entry = a.freights[src]?.products[a.id];
    if (!entry) continue;
    if (entry.status === 'no_route') return { ok: false, reason: 'no_route', source: src };
    const lines: (ShippingLine | null | undefined)[] = entry.options?.length
      ? entry.options.map((o) => ({ usd: o.usd, name: o.name ?? null, days: o.days ?? null }))
      : [entry.cheapest, entry.cheapest_under_20d].map((o) => (o ? { usd: o.usd, name: o.name ?? null, days: o.days ?? null } : null));
    const d = defaultLine(lines);
    if (!d) return { ok: false, reason: 'no_route', source: src };
    const quotedQty = typeof entry.qty === 'number' && entry.qty > 1 ? Math.round(entry.qty) : null;
    return {
      ok: true,
      usd_cents: Math.round(d.line.usd * 100),
      quoted_for_sale: quotedQty !== null && quotedQty === a.sellQty,
      quoted_qty: quotedQty,
      source: src,
      line: `${d.line.name ?? ''} ${d.line.days ?? ''}`.trim(),
      days: daysPair(d.line.days),
      express_only: d.express_only,
    };
  }
  const sku = a.card.options?.skus.find((s) => s.id === a.card.options?.default_sku);
  const si = sku?.shipping_il;
  if (si && typeof si.amount === 'number' && si.currency.toUpperCase() === 'USD') {
    return {
      ok: true,
      usd_cents: Math.round(si.amount * 100),
      quoted_for_sale: false,
      quoted_qty: null,
      source: 'card',
      line: 'המק"ט שבחדר',
      days: daysPair(si.days),
      express_only: false,
    };
  }
  if (a.cache) {
    const d = defaultLine(a.cache.lines);
    if (d) {
      return {
        ok: true,
        usd_cents: Math.round(d.line.usd * 100),
        quoted_for_sale: false,
        quoted_qty: null,
        source: 'cache',
        line: `${a.cache.label}: ${d.line.name ?? ''} ${d.line.days ?? ''}`.trim(),
        days: daysPair(d.line.days),
        express_only: d.express_only,
      };
    }
  }
  if (!row && a.lead) {
    const rec = a.lead.rec;
    const ship = num(rec.ship_usd);
    if (ship !== null && ship >= 0) {
      const q = leadQty(rec) ?? a.sellQty;
      const text = `${String(rec.why_he ?? '')} ${String(rec.price_basis_he ?? '')}`;
      return {
        ok: true,
        usd_cents: Math.round(ship * 100),
        quoted_for_sale: q > 1 && q === a.sellQty,
        quoted_qty: q > 1 ? q : null,
        source: 'leads',
        line: `מהליקוט (${a.lead.file})`,
        days: daysPair(typeof rec.ship_days === 'string' ? rec.ship_days : null),
        express_only: isExpressLine(text) && /to\s*door/i.test(text),
      };
    }
  }
  return { ok: false, reason: 'no_line', source: null };
}

export type InitialPrice = { retail_ils: number; source: 'studio' | 'owner' | 'initial-card' | 'initial-leads' };

/**
 * The product's starting price, as the studio reads it (build.py card_economics): the pricing row (retail_src "studio"
 * = the owner set it), else the card's own retail_ils / suggested_retail, else the final-round record's price. null:
 * no price at all (not sold). Nothing here is computed from a margin target (SITE1: no 40% provisional price).
 */
export function initialPrice(
  card: { price: { currency: string; suggested_retail?: number | null } & Record<string, unknown> },
  row: ProductEconomics | undefined,
  lead: LeadRecord | null,
): InitialPrice | null {
  if (row && typeof row.retail_ils === 'number' && row.retail_ils > 0)
    return { retail_ils: row.retail_ils, source: row.retail_src === 'studio' ? 'owner' : 'studio' };
  const cur = (card.price.currency || 'USD').toUpperCase();
  if (cur === 'USD' || cur === 'ILS') {
    for (const k of ['retail_ils', 'suggested_retail']) {
      const v = num(card.price[k]);
      if (v !== null && v > 0) return { retail_ils: v, source: 'initial-card' };
    }
  }
  const lp = lead ? num(lead.rec.price_ils) : null;
  if (lp !== null && lp > 0) return { retail_ils: lp, source: 'initial-leads' };
  return null;
}

/** The highest Israeli comparable of a pricing row (il_value.high, else the dearest comp), for NL2. */
export function highestComparableIls(row: ProductEconomics | undefined): number | null {
  const iv = row?.il_value;
  if (!iv) return null;
  if (typeof iv.high === 'number' && iv.high > 0) return iv.high;
  const prices = (iv.comps ?? []).map((c) => c.price).filter((p): p is number => typeof p === 'number' && p > 0);
  return prices.length ? Math.max(...prices) : null;
}
