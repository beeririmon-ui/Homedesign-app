/** Supplier options (studio rules ג, 2026-10-11): per-SKU retail, the picker cascade, and the repo's option data. */
import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  DEFAULT_SETTINGS,
  ProductCardSchema,
  availableValues,
  optionIssues,
  pickSku,
  recommendedRetailIls,
  selectionOf,
  skuCostCents,
  skuRetail,
  skuShippingCents,
  type SkuRetailInput,
} from '../src';

const S = DEFAULT_SETTINGS;
const base: SkuRetailInput = {
  is_default: false,
  product_retail_agorot: 18900,
  product_price_provisional: true,
  studio_retail_ils: null,
  sku_override_ils: null,
  cost_usd_cents: 1117,
  shipping_usd_cents: 199,
  default_cost_usd_cents: 1117,
  default_shipping_usd_cents: 199,
  fx_usd_ils: S.fx_usd_ils,
  sell_qty: 1,
  strict: false,
};

describe('retail per SKU: the same economics as the main price', () => {
  it("the room's SKU is the product: its price and its provisional flag", () => {
    expect(skuRetail({ ...base, is_default: true }, S)).toEqual({ retail_agorot: 18900, provisional: true });
    expect(skuRetail({ ...base, is_default: true, product_price_provisional: false }, S)).toEqual({ retail_agorot: 18900, provisional: false });
  });

  it('another SKU: recommendedRetailIls on its own cost and shipping, rounded to …9 the same way', () => {
    const r = skuRetail({ ...base, cost_usd_cents: 1599 }, S)!;
    const rec = recommendedRetailIls({ cost_usd_cents: 1599, shipping_usd_cents: 199, fx_usd_ils: S.fx_usd_ils, sell_qty: 1 }, S)!;
    expect(r).toEqual({ retail_agorot: rec * 100, provisional: true });
    expect(rec % 10).toBe(9);
    // a dearer SKU never costs less than a cheaper one
    expect(skuRetail({ ...base, cost_usd_cents: 2599 }, S)!.retail_agorot).toBeGreaterThanOrEqual(r.retail_agorot);
    // a set multiplies every SKU alike (sell_qty)
    const pair = skuRetail({ ...base, cost_usd_cents: 1599, sell_qty: 2 }, S)!;
    expect(pair.retail_agorot).toBe(recommendedRetailIls({ cost_usd_cents: 1599, shipping_usd_cents: 199, fx_usd_ils: S.fx_usd_ils, sell_qty: 2 }, S)! * 100);
  });

  it("keeps the studio's distance from the recommendation when the studio priced the product by hand", () => {
    const recDefault = recommendedRetailIls({ cost_usd_cents: 1117, shipping_usd_cents: 199, fx_usd_ils: S.fx_usd_ils, sell_qty: 1 }, S)!;
    const recSku = recommendedRetailIls({ cost_usd_cents: 1599, shipping_usd_cents: 199, fx_usd_ils: S.fx_usd_ils, sell_qty: 1 }, S)!;
    const r = skuRetail({ ...base, cost_usd_cents: 1599, studio_retail_ils: recDefault + 20 }, S)!;
    expect(r.retail_agorot).toBe((recSku + 20) * 100);
  });

  it('a studio price per SKU wins; a strict build sells only priced SKUs', () => {
    expect(skuRetail({ ...base, sku_override_ils: 249 }, S)).toEqual({ retail_agorot: 24900, provisional: false });
    expect(skuRetail({ ...base, strict: true }, S)).toBeNull();
    expect(skuRetail({ ...base, strict: true, is_default: true }, S)).toEqual({ retail_agorot: 18900, provisional: true });
  });

  it('cost and shipping per SKU in the card terms', () => {
    expect(skuCostCents(1117, 1117, 1599)).toBe(1599); // card = the room's SKU
    expect(skuCostCents(200, 50, 66)).toBe(264); // card priced as a set of 4 of the room's SKU
    expect(skuCostCents(1720, 2170, 2500)).toBe(2050); // prices moved: the card's price, the supplier's difference
    expect(skuShippingCents(1444, { amount: 1.99, currency: 'USD' }, { amount: 3.49, currency: 'USD' })).toBe(1594);
    expect(skuShippingCents(1444, null, { amount: 3.49, currency: 'USD' })).toBe(1444);
  });
});

describe('the picker: a cascade that never traps the customer', () => {
  const axes = [
    { id: 'color', values: [{ id: 'beige' }, { id: 'black' }, { id: 'green' }] },
    { id: 'size', values: [{ id: '45x45' }, { id: '50x50' }, { id: '60x60' }] },
  ];
  const skus = [
    { variant_id: 'a', values: { color: 'beige', size: '45x45' }, available: true },
    { variant_id: 'b', values: { color: 'beige', size: '60x60' }, available: true },
    { variant_id: 'c', values: { color: 'black', size: '50x50' }, available: true },
    { variant_id: 'd', values: { color: 'green', size: '50x50' }, available: false }, // out of stock
  ];

  it('offers on each axis only what exists with the choices above it', () => {
    const sel = selectionOf(axes, skus[0]!);
    expect([...availableValues(axes, skus, sel, 0)].sort()).toEqual(['beige', 'black']); // green is out of stock
    expect([...availableValues(axes, skus, sel, 1)].sort()).toEqual(['45x45', '60x60']); // no beige 50×50
  });

  it('choosing a value moves the axes below it to a SKU that exists', () => {
    const sel = selectionOf(axes, skus[0]!);
    const r = pickSku(axes, skus, sel, 0, 'black');
    expect(r.sel).toEqual({ color: 'black', size: '50x50' });
    expect(r.sku?.variant_id).toBe('c');
    const back = pickSku(axes, skus, r.sel, 0, 'beige');
    expect(back.sku?.variant_id).toBe('a'); // 50×50 does not exist in beige: the first size that does
    expect(pickSku(axes, skus, selectionOf(axes, skus[0]!), 1, '60x60').sku?.variant_id).toBe('b');
  });
});

describe('repo data: every card with options', () => {
  const REPO = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
  const walk = (d: string): string[] =>
    readdirSync(d).flatMap((n) => (statSync(join(d, n)).isDirectory() ? walk(join(d, n)) : n.endsWith('.json') ? [join(d, n)] : []));

  it('parses, names a SKU for the room, and passes the cross-field rules', () => {
    const bad: string[] = [];
    let n = 0;
    for (const f of walk(resolve(REPO, 'data/products'))) {
      const raw = JSON.parse(readFileSync(f, 'utf8')) as { options?: unknown };
      if (!raw.options) continue;
      n++;
      const r = ProductCardSchema.shape.options.safeParse(raw.options);
      if (!r.success || !r.data) bad.push(`${f}: ${r.success ? 'empty' : r.error.issues[0]?.message}`);
      else if (optionIssues(r.data).length) bad.push(`${f}: ${optionIssues(r.data).join('; ')}`);
    }
    expect(n).toBeGreaterThan(0);
    expect(bad).toEqual([]);
  });
});
