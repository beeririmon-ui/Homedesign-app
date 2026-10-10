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
  CartItemInputSchema,
  charmRoundDownIls,
  unitPriceEstimateIls,
  sellQtyDefault,
  publicSafety,
  safetyLinesHe,
  packLabelHe,
} from '../src';
import { existsSync } from 'node:fs';
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
      const raw = JSON.parse(readFileSync(resolve(REPO, 'data/slots', f), 'utf8')) as Record<string, unknown>;
      // data/slots also holds lists about the slots (e.g. filler-replacements.json); only room files have `slots`
      if (!Array.isArray(raw.slots)) continue;
      const r = SlotsFileSchema.safeParse(raw);
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
    // the studio's settings.json format: percent values are whole numbers
    const r = resolveSettings({ economics: { vat_pct: 18, usd_ils: 3.65, card_pct: 2.5 } });
    expect(r.settings.fx_usd_ils).toBe(3.65);
    expect(r.settings.payment_fee_rate).toBe(0.025);
    expect(r.defaults_used).not.toContain('vat_rate');
    expect(r.defaults_used).toContain('returns_reserve_rate');
    expect(r.defaults_used).toContain('free_shipping_threshold_ils');
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

describe('set or single piece (P1)', () => {
  it('rounds down to a price ending in 9', () => {
    expect([115, 109, 189, 190, 200, 9, 19].map(charmRoundDownIls)).toEqual([109, 109, 189, 189, 199, 9, 19]);
  });

  it('estimates one piece at ceil(set / N × 1.15) rounded down to …9, never under the set per piece', () => {
    expect(unitPriceEstimateIls(349, 2)).toBe(199); // 200.7 → 201 → 199
    expect(unitPriceEstimateIls(299, 4)).toBe(79); // 85.96 → 86 → 79 (≥ 75)
    expect(unitPriceEstimateIls(1290, 3)).toBe(489); // 494.5 → 495 → 489
    // small prices: rounding down would undercut the set's own per-piece price, so it rounds up to …9 instead
    expect(unitPriceEstimateIls(39, 2)).toBe(29); // 22.4 → 23 → 19 < 20 → 29
    for (const [set, n] of [
      [49, 2],
      [129, 3],
      [349, 2],
      [699, 6],
    ] as const) {
      const u = unitPriceEstimateIls(set, n);
      expect(u % 10).toBe(9);
      expect(u).toBeGreaterThanOrEqual(Math.ceil(set / n));
      expect(u).toBeLessThan(set);
    }
    expect(() => unitPriceEstimateIls(100, 1)).toThrow();
  });

  it('labels and the cart input default to the set', () => {
    expect(packLabelHe('set', 2)).toBe('סט של 2');
    expect(packLabelHe('unit', 2)).toBe('יחידה אחת');
    expect(CartItemInputSchema.parse({ variant_id: 'x:default', qty: 1 }).pack).toBe('set');
    expect(CartItemInputSchema.safeParse({ variant_id: 'x:default', qty: 1, pack: 'pair' }).success).toBe(false);
  });

  it('default sell quantity follows the studio rule', () => {
    expect(sellQtyDefault({ name: 'Pillar holder', notes: 'מוצע כסט של 2 יחידות (המחיר בשדה cost הוא ליחידה)' }, null)).toMatchObject({ qty: 2, sure: true });
    expect(sellQtyDefault({ name: 'Wall lamp', notes: 'price is per lamp' }, 2)).toMatchObject({ qty: 2, sure: true, set_of: 2 });
    expect(sellQtyDefault({ name: 'Wall lamp pair', notes: 'price is for the pair' }, 2)).toMatchObject({ qty: 1, sure: true });
    expect(sellQtyDefault({ name: 'Cushion', notes: '' }, 4)).toMatchObject({ qty: 1, sure: false, set_of: 4 });
    expect(sellQtyDefault({ name: 'Vase', notes: '' }, null)).toEqual({ qty: 1, sure: true, set_of: null, reason: null });
  });

  // the studio's own output (studio/dist/data.json, built locally by studio/build.py) agrees on every real card
  const studioData = resolve(REPO, 'studio/dist/data.json');
  it.skipIf(!existsSync(studioData))('agrees with studio/build.py on the real cards', () => {
    const data = JSON.parse(readFileSync(studioData, 'utf8')) as {
      products: {
        id: string;
        name: string;
        notes: string | null;
        slot_key: string | null;
        shared_in: string[];
        sell_qty_default: { qty: number; sure: boolean };
      }[];
    };
    const setOf = (key: string): number | null => {
      const [room, slot] = key.split('/');
      const f = resolve(REPO, `data/slots/${room}.json`);
      if (!existsSync(f)) return null;
      const s = (JSON.parse(readFileSync(f, 'utf8')) as { slots: { id: string; set_of?: number }[] }).slots.find((x) => x.id === slot);
      return s?.set_of ?? null;
    };
    const checked = data.products.filter((p) => p.slot_key && !p.shared_in?.length);
    expect(checked.length).toBeGreaterThan(20);
    for (const p of checked) {
      const got = sellQtyDefault(p, setOf(p.slot_key!));
      expect({ id: p.id, qty: got.qty, sure: got.sure }).toEqual({ id: p.id, qty: p.sell_qty_default.qty, sure: p.sell_qty_default.sure });
    }
  });
});

describe('standards and safety (D9)', () => {
  it('shows only what the card states, in Hebrew', () => {
    expect(safetyLinesHe(publicSafety({ toy_standard: ['EN71', 'SI-562'], ce: true }))).toEqual([{ text: 'תקן צעצועים EN 71 / ת"י 562' }, { text: 'CE' }]);
    expect(safetyLinesHe(publicSafety({ ip_rating: 'ip44', power: 'wired' })).map((l) => l.text)).toEqual([
      'IP44, מתאים לחדר רחצה',
      'דורשת התקנה על ידי חשמלאי',
    ]);
    expect(safetyLinesHe(publicSafety({ ip_rating: 'IP20' })).map((l) => l.text)).toEqual(['דרגת אטימות IP20']);
    expect(safetyLinesHe(publicSafety({ toy_standard: ['EN13613'] })).map((l) => l.text)).toEqual(['תקן סקייטבורד EN 13613']);
    expect(safetyLinesHe(publicSafety({ power: 'plug', plug_type: 'IL', voltage: '220-240V' })).map((l) => l.text)).toEqual([
      'מתחברת לשקע, תקע IL',
      'מתח 220-240V',
    ]);
  });

  it('no block, nulls, false and empty lists claim nothing', () => {
    expect(publicSafety(undefined)).toBeNull();
    expect(publicSafety(null)).toBeNull();
    expect(publicSafety({ ce: null, ip_rating: null, toy_standard: [], power: null, certificates: [], source: 'CJ API' })).toBeNull();
    // CE false is not a claim to show (and certainly not "CE")
    expect(publicSafety({ ce: false, power: 'none' })).toBeNull();
  });

  it('keeps the source internal and links a certificate only once it is verified', () => {
    const s = publicSafety({
      source: 'supplier listing',
      certificates: [
        { name: 'CE DoC', url: 'https://example.com/ce.pdf', verified: true },
        { name: 'EN 71-3', url: 'https://example.com/en71.pdf', verified: false },
      ],
    })!;
    expect(JSON.stringify(s)).not.toContain('supplier listing');
    expect(safetyLinesHe(s)).toEqual([
      { text: 'תעודה: CE DoC', href: 'https://example.com/ce.pdf' },
      { text: 'תעודה: EN 71-3 (לפי הספק, לא אומתה)', href: undefined },
    ]);
  });
});
