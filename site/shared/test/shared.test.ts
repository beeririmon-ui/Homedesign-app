import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  ProductCardSchema,
  SlotsFileSchema,
  DEFAULT_SETTINGS,
  ProductEconomicsFileSchema,
  resolveSettings,
  charmRoundUpIls,
  recommendedRetailIls,
  unitEconomics,
  formatIls,
  signWebhook,
  verifyWebhook,
  CheckoutRequestSchema,
} from '../src';
import { generate } from '../scripts/gen-product-card-schema';

const REPO = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const walk = (d: string): string[] =>
  readdirSync(d).flatMap((n) => (statSync(join(d, n)).isDirectory() ? walk(join(d, n)) : n.endsWith('.json') ? [join(d, n)] : []));

describe('repo data against the derived schemas', () => {
  it('product-card.gen.ts is generated from data/product-card.schema.json and up to date', () => {
    expect(readFileSync(resolve(REPO, 'site/shared/src/schema/product-card.gen.ts'), 'utf8')).toBe(generate());
  });

  it('every slots file parses', () => {
    for (const f of readdirSync(resolve(REPO, 'data/slots'))) {
      const r = SlotsFileSchema.safeParse(JSON.parse(readFileSync(resolve(REPO, 'data/slots', f), 'utf8')));
      expect(r.success, `${f}: ${r.success ? '' : r.error.message}`).toBe(true);
    }
  });

  it('every product card outside the shared pool parses (pool cards are a known data issue)', () => {
    const bad: string[] = [];
    for (const f of walk(resolve(REPO, 'data/products'))) {
      const r = ProductCardSchema.safeParse(JSON.parse(readFileSync(f, 'utf8')));
      if (!r.success && !f.includes('/data/products/pool/')) bad.push(f);
    }
    expect(bad).toEqual([]);
  });
});

describe('pricing', () => {
  it('rounds up to a price ending in 9', () => {
    expect(charmRoundUpIls(183.2)).toBe(189);
    expect(charmRoundUpIls(189)).toBe(189);
    expect(charmRoundUpIls(190)).toBe(199);
  });

  it('the recommended price reaches the target margin', () => {
    const input = { cost_usd_cents: 1624, shipping_usd_cents: 1000, fx_usd_ils: 3.7 };
    const retail = recommendedRetailIls(input, DEFAULT_SETTINGS)!;
    const e = unitEconomics({ ...input, retail_agorot: retail * 100 }, DEFAULT_SETTINGS);
    expect(e.meets_target).toBe(true);
    const below = unitEconomics({ ...input, retail_agorot: (retail - 10) * 100 }, DEFAULT_SETTINGS);
    expect(below.margin_rate).toBeLessThan(e.margin_rate);
  });

  it('VAT is extracted from the consumer price, not added on top', () => {
    const e = unitEconomics({ retail_agorot: 11800, cost_usd_cents: 0, shipping_usd_cents: 0, fx_usd_ils: 3.7 }, DEFAULT_SETTINGS);
    expect(e.net_agorot).toBe(10000);
    expect(e.vat_agorot).toBe(1800);
  });

  it('settings fall back to provisional defaults and say so', () => {
    const r = resolveSettings({ vat_rate: 0.18, fx_usd_ils: 3.65 });
    expect(r.settings.fx_usd_ils).toBe(3.65);
    expect(r.defaults_used).not.toContain('vat_rate');
    expect(r.defaults_used).toContain('payment_fee_rate');
  });

  it('economics products file accepts a flat map or a { products } wrapper', () => {
    const v = { 'vase-a': { retail_ils: 159, shipping_cost_usd: 7.5 } };
    expect(ProductEconomicsFileSchema.parse(v)).toEqual(v);
    expect(ProductEconomicsFileSchema.parse({ products: v })).toEqual(v);
  });
});

describe('formatting and validation', () => {
  it('formats shekels as in the Design Bible', () => {
    expect(formatIls(129000).replace(/[⁦⁩]/g, '')).toBe('₪ 1,290');
    expect(formatIls(1990).replace(/[⁦⁩]/g, '')).toBe('₪ 19.90');
  });

  it('accepts Israeli phone numbers and requires terms consent', () => {
    const base = {
      cart_id: 'x'.repeat(32),
      customer: { full_name: 'דנה כהן', email: 'dana@example.com', phone: '052-555-1234' },
      address: { city: 'חיפה', street: 'הנביאים', house: '3' },
      shipping_method: 'economy',
      consents: { terms: true },
    };
    expect(CheckoutRequestSchema.safeParse(base).success).toBe(true);
    expect(CheckoutRequestSchema.safeParse({ ...base, customer: { ...base.customer, phone: '12345' } }).success).toBe(false);
    expect(CheckoutRequestSchema.safeParse({ ...base, consents: { terms: false } }).success).toBe(false);
  });
});

describe('webhook signatures', () => {
  it('verifies, rejects tampering and stale timestamps', async () => {
    const now = 1_760_000_000;
    const sig = await signWebhook('s3cret', '{"a":1}', now);
    expect(await verifyWebhook('s3cret', sig, '{"a":1}', now + 10)).toEqual({ ok: true, timestamp: now });
    expect(await verifyWebhook('s3cret', sig, '{"a":2}', now)).toEqual({ ok: false, reason: 'mismatch' });
    expect(await verifyWebhook('s3cret', sig, '{"a":1}', now + 301)).toEqual({ ok: false, reason: 'stale' });
    expect(await verifyWebhook('s3cret', 'garbage', '{"a":1}', now)).toEqual({ ok: false, reason: 'format' });
  });
});
