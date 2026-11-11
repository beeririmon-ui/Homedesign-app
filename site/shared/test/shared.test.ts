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
  CARD_ROOMS,
  cardRoom,
  roomFromPath,
  isDraftCard,
  onlyDraftIssues,
  shipForQtyCents,
  unitShipFromSaleCents,
  landedAgorot,
  noLossRetailIls,
  breakEvenIls,
  defaultLine,
  resolveShipping,
  initialPrice,
  supplierKey,
  ORDER_STATUS_HE,
  orderStep,
} from '../src';
import { loadLeadRecords } from '../../tools/lib/leads';
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

  it('every product card outside the shared pool parses, or is a DS-API draft whose only gaps are its unfilled draft fields', () => {
    // pool cards are a known data issue; a draft card (shared/src/card-draft.ts) is unfinished sourcing work, listed by name
    const bad: string[] = [];
    const drafts: string[] = [];
    for (const f of walk(resolve(REPO, 'data/products'))) {
      const raw = JSON.parse(readFileSync(f, 'utf8')) as Record<string, unknown>;
      const r = ProductCardSchema.safeParse(raw);
      if (r.success || f.includes('/data/products/pool/')) continue;
      const paths = r.error.issues.map((i) => i.path.join('.'));
      if (isDraftCard(raw) && onlyDraftIssues(paths)) drafts.push(f.replace(`${REPO}/`, ''));
      else bad.push(`${f}: ${paths.join(', ')}`);
    }
    expect(bad).toEqual([]);
    // the drafts are not hidden: the count is asserted so a change is a visible, deliberate one (sourcing-agent fills them)
    console.info(`draft cards (DS API, colors / visual_weight unfilled): ${drafts.length}`);
    expect(drafts.length).toBeLessThanOrEqual(68);
  });

  it('the card room enum is exactly the rooms of data/slots (schema 1.1)', () => {
    const ids = readdirSync(resolve(REPO, 'data/slots')).flatMap((f) => {
      const raw = JSON.parse(readFileSync(resolve(REPO, 'data/slots', f), 'utf8')) as { room?: string; slots?: unknown };
      if (!Array.isArray(raw.slots)) return [];
      expect(raw.room, f).toBe(f.replace(/\.json$/, ''));
      return [raw.room];
    });
    expect([...ids].sort()).toEqual([...CARD_ROOMS].sort());
  });

  it('every card with a room folder names that room, and room + slot is one slot in data/slots', () => {
    const slotIds = new Map<string, Set<string>>();
    const idsOf = (room: string): Set<string> => {
      if (!slotIds.has(room)) {
        const raw = JSON.parse(readFileSync(resolve(REPO, 'data/slots', `${room}.json`), 'utf8')) as { slots: { id: string }[] };
        slotIds.set(room, new Set(raw.slots.map((s) => s.id)));
      }
      return slotIds.get(room)!;
    };
    const bad: string[] = [];
    for (const f of walk(resolve(REPO, 'data/products'))) {
      const card = JSON.parse(readFileSync(f, 'utf8')) as { room?: string; slot?: string | null };
      const folder = roomFromPath(f);
      if (card.room === undefined) {
        if (folder !== null) bad.push(`${f}: no room`);
        continue;
      }
      if (folder !== null && folder !== card.room) bad.push(`${f}: room ${card.room}, folder ${folder}`);
      if (!(CARD_ROOMS as readonly string[]).includes(card.room) || !idsOf(card.room).has(card.slot ?? ''))
        bad.push(`${f}: ${card.room}/${card.slot} is not a slot`);
    }
    expect(bad).toEqual([]);
  });

  it("cardRoom: the card's room first, its folder as the fallback", () => {
    expect(cardRoom({ room: 'hall' }, 'data/products/vase/x.json')).toBe('hall');
    expect(cardRoom({}, 'data/products/vase/x.json')).toBe('living-room');
    expect(cardRoom({}, '/repo/data/products/entrance/key-tray/x.json')).toBe('hall');
    expect(cardRoom({}, 'data/products/dining/bowl/x.json')).toBe('dining-room');
    expect(cardRoom({}, 'data/products/kids/rug/x.json')).toBe('kids');
    expect(cardRoom({}, 'data/products/pool/vase/x.json')).toBeNull();
    expect(cardRoom({}, 'data/products/leads/x.json')).toBeNull();
    expect(cardRoom({ room: 'bedroom' }, 'data/products/master/rug/x.json')).toBe('master');
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

  it("freight of a sale is the studio's combined parcel, not a parcel per piece (SITE1)", () => {
    expect(shipForQtyCents(877, 3)).toBe(877 + 2 * (877 - 372));
    expect(shipForQtyCents(199, 4)).toBe(199);
    expect(unitShipFromSaleCents(shipForQtyCents(877, 3), 3)).toBe(877);
    // landed = (cost × q + freight(q)) × fx; a quote for exactly the sale is taken as it is
    expect(landedAgorot({ cost_usd_cents: 1000, shipping_usd_cents: 877, fx_usd_ils: 3.3, sell_qty: 3 })).toBe(Math.round((3000 + 877 + 2 * 505) * 3.3));
    expect(landedAgorot({ cost_usd_cents: 1000, shipping_usd_cents: 2000, fx_usd_ils: 3.3, sell_qty: 3, shipping_quoted_for_sale: true })).toBe(
      Math.round(5000 * 3.3),
    );
    const linear = unitEconomics({ retail_agorot: 29900, cost_usd_cents: 1000, shipping_usd_cents: 877, fx_usd_ils: 3.3, sell_qty: 3 }, DEFAULT_SETTINGS);
    expect(linear.cogs_agorot).toBe(Math.round((3000 + 877 + 2 * 505) * 3.3));
  });

  it('the no-loss price: the lowest …9 price whose contribution is not negative (ה.13), the same as no_loss.py', () => {
    // no_loss.py check(): break_even_for(50) = (50 + 1.2) / ((1 − 0.08) / 1.18 − 0.02)
    expect(breakEvenIls(50, DEFAULT_SETTINGS)).toBeCloseTo((50 + 1.2) / ((1 - 0.08) / 1.18 - 0.02), 9);
    const floor = noLossRetailIls(49.93, DEFAULT_SETTINGS); // the wabi-sabi cushion's headline landed cost: ₪69 (no_loss_room_sku_ils)
    expect(floor).toBe(69);
    const at = unitEconomics({ retail_agorot: floor * 100, cost_usd_cents: 0, shipping_usd_cents: 4993, fx_usd_ils: 1 }, DEFAULT_SETTINGS);
    expect(at.contribution_agorot).toBeGreaterThanOrEqual(0);
    const below = unitEconomics({ retail_agorot: (floor - 10) * 100, cost_usd_cents: 0, shipping_usd_cents: 4993, fx_usd_ils: 1 }, DEFAULT_SETTINGS);
    expect(below.contribution_agorot).toBeLessThan(0);
  });

  it('VAT is extracted from the consumer price, not added on top', () => {
    const e = unitEconomics({ retail_agorot: 11800, cost_usd_cents: 0, shipping_usd_cents: 0, fx_usd_ils: 3.7 }, DEFAULT_SETTINGS);
    expect(e.net_agorot).toBe(10000);
    expect(e.vat_agorot).toBe(1800);
  });

  it('the shipping line: the cheapest standard line, express only when there is nothing else (no_loss.py default_quote)', () => {
    const cj = [
      { usd: 14.44, name: 'CJPacket Eub', days: '12-50' },
      { usd: 25.22, name: 'CJPacket To Door', days: '11-18' },
      { usd: 154.26, name: 'DHL Official', days: '3-7' },
    ];
    expect(defaultLine(cj)).toEqual({ line: cj[0], express_only: false });
    expect(defaultLine([cj[1]!, cj[2]!])).toEqual({ line: cj[1], express_only: true });
    expect(defaultLine([])).toBeNull();
    expect(supplierKey('CJ Dropshipping', 'https://cjdropshipping.com/product/x-p-1.html')).toBe('cj');
    expect(supplierKey('AliExpress', 'https://www.aliexpress.com/item/1.html')).toBe('aliexpress');
  });

  it("the shipping line in the studio's order: manual, the supplier's file, any file, the room SKU, the cache, the final round; never a default", () => {
    const card = {
      supplier: { name: 'CJ Dropshipping', product_url: 'https://cjdropshipping.com/product/x-p-1.html' },
      price: { currency: 'USD' },
      options: null,
    };
    const freights = {
      cj: { products: { a: { options: [{ name: 'CJPacket Eub', days: '12-50', usd: 14.44 }], status: 'ok' } } },
      zendrop: { products: { b: { cheapest: { name: 'Zendrop regular', days: '14', usd: 13.38 }, status: 'ok', qty: 2 } } },
    };
    expect(resolveShipping({ id: 'a', card, row: { shipping_cost_usd: 9.5 }, freights, lead: null, sellQty: 1 })).toMatchObject({
      ok: true,
      usd_cents: 950,
      source: 'manual',
    });
    expect(resolveShipping({ id: 'a', card, row: undefined, freights, lead: null, sellQty: 1 })).toMatchObject({
      ok: true,
      usd_cents: 1444,
      source: 'cj',
      express_only: false,
      days: [12, 50],
    });
    // a quote for exactly the sale's pieces is taken as it is; for another count it is one piece's (as the studio does)
    expect(resolveShipping({ id: 'b', card, row: undefined, freights, lead: null, sellQty: 2 })).toMatchObject({
      ok: true,
      usd_cents: 1338,
      source: 'zendrop',
      quoted_for_sale: true,
      quoted_qty: 2,
    });
    expect(resolveShipping({ id: 'b', card, row: undefined, freights, lead: null, sellQty: 1 })).toMatchObject({ ok: true, quoted_for_sale: false });
    const withSku = { ...card, options: { default_sku: 's1', skus: [{ id: 's1', shipping_il: { amount: 1.99, currency: 'USD', days: '6-15' } }] } };
    expect(resolveShipping({ id: 'c', card: withSku, row: undefined, freights, lead: null, sellQty: 1 })).toMatchObject({
      ok: true,
      usd_cents: 199,
      source: 'card',
    });
    expect(
      resolveShipping({
        id: 'c',
        card,
        row: undefined,
        freights,
        cache: { lines: [{ usd: 23.39, name: 'AliExpress standard shipping', days: '22-32' }], label: 'מטמון' },
        lead: null,
        sellQty: 1,
      }),
    ).toMatchObject({ ok: true, usd_cents: 2339, source: 'cache' });
    expect(
      resolveShipping({ id: 'c', card, row: undefined, freights, lead: { rec: { ship_usd: 4.2, qty: 2 }, file: 'f.json', date: '2026-10-13' }, sellQty: 2 }),
    ).toMatchObject({ ok: true, usd_cents: 420, source: 'leads', quoted_for_sale: true });
    // a pricing row without a manual figure blocks the final-round fallback, as in the studio
    expect(
      resolveShipping({ id: 'c', card, row: { retail_ils: 99 }, freights, lead: { rec: { ship_usd: 4.2 }, file: 'f.json', date: '' }, sellQty: 1 }),
    ).toEqual({ ok: false, reason: 'no_line', source: null });
    expect(resolveShipping({ id: 'd', card, row: undefined, freights: { cj: { products: { d: { status: 'no_route' } } } }, lead: null, sellQty: 1 })).toEqual({
      ok: false,
      reason: 'no_route',
      source: 'cj',
    });
  });

  it("the starting price is the studio's, the card's or the final round's: never a margin target (SITE1)", () => {
    const card = { price: { currency: 'USD', suggested_retail: 149 } };
    expect(initialPrice(card, { retail_ils: 189, retail_src: 'studio' }, null)).toEqual({ retail_ils: 189, source: 'owner' });
    expect(initialPrice(card, { retail_ils: 189, retail_src: 'initial-no-loss-2026-10-20' }, null)).toEqual({ retail_ils: 189, source: 'studio' });
    expect(initialPrice(card, undefined, null)).toEqual({ retail_ils: 149, source: 'initial-card' });
    expect(initialPrice({ price: { currency: 'USD' } }, undefined, { rec: { price_ils: 129 }, file: 'f', date: '' })).toEqual({
      retail_ils: 129,
      source: 'initial-leads',
    });
    expect(initialPrice({ price: { currency: 'USD' } }, undefined, null)).toBeNull();
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
    const slotOf = (key: string): { set_of?: number; alternative_form?: unknown } | null => {
      const [room, slot] = key.split('/');
      const f = resolve(REPO, `data/slots/${room}.json`);
      if (!existsSync(f)) return null;
      const s = (JSON.parse(readFileSync(f, 'utf8')) as { slots: { id: string; set_of?: number; alternative_form?: unknown }[] }).slots.find(
        (x) => x.id === slot,
      );
      return s ? { set_of: s.set_of, alternative_form: s.alternative_form } : null;
    };
    // the real card (its options, dimensions, cost) and its final-round record, as the studio reads them
    const cards = new Map<string, Record<string, unknown>>();
    for (const f of walk(resolve(REPO, 'data/products'))) {
      const c = JSON.parse(readFileSync(f, 'utf8')) as { id?: string };
      if (c.id && !cards.has(c.id)) cards.set(c.id, c as Record<string, unknown>);
    }
    const leads = loadLeadRecords(REPO);
    const checked = data.products.filter((p) => p.slot_key && !p.shared_in?.length);
    expect(checked.length).toBeGreaterThan(20);
    const mismatches: string[] = [];
    for (const p of checked) {
      const card = (cards.get(p.id) ?? { name: p.name, notes: p.notes }) as Parameters<typeof sellQtyDefault>[0];
      const got = sellQtyDefault(card, slotOf(p.slot_key!), leads.get(p.id) ?? null);
      if (got.qty !== p.sell_qty_default.qty || got.sure !== p.sell_qty_default.sure)
        mismatches.push(`${p.id}: site ${got.qty}/${got.sure} (${got.reason}) vs studio ${p.sell_qty_default.qty}/${p.sell_qty_default.sure}`);
    }
    expect(mismatches, `${mismatches.length} of ${checked.length}`).toEqual([]);
    expect(setOf).toBeDefined();
  });
});

describe("the order in the customer's words (ART6)", () => {
  it('never names the supplier, and the four steps are in order', () => {
    expect(Object.values(ORDER_STATUS_HE).some((s) => s.includes('ספק'))).toBe(false);
    expect([ORDER_STATUS_HE.paid, ORDER_STATUS_HE.sent_to_supplier, ORDER_STATUS_HE.shipped, ORDER_STATUS_HE.delivered]).toEqual([
      'התקבלה',
      'בהכנה',
      'נשלחה',
      'נמסרה',
    ]);
    expect([
      orderStep('paid'),
      orderStep('sent_to_supplier'),
      orderStep('supplier_error'),
      orderStep('shipped'),
      orderStep('delivered'),
      orderStep('pending_payment'),
    ]).toEqual([0, 1, 1, 2, 3, null]);
  });
  it('S16 (QA ה7): an order stuck on a supplier error is said honestly, never "בהכנה", and names no supplier', () => {
    expect(ORDER_STATUS_HE.supplier_error).not.toBe('בהכנה');
    expect(ORDER_STATUS_HE.supplier_error).toBe('מתעכבת');
    expect(ORDER_DELAY_HE).not.toMatch(/ספק/);
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

  it("a certificate without a document (schema 1.2, source: seller-claim) is the seller's claim, never verified (SCH1)", () => {
    const s = publicSafety({ certificates: [{ name: 'CE (seller attribute)', verified: false, source: 'seller-claim' }] })!;
    expect(s.certificates).toEqual([{ name: 'CE (seller attribute)', url: null, verified: false, seller_claim: true }]);
    expect(safetyLinesHe(s)).toEqual([{ text: 'CE (seller attribute): טענת המוכר, אין מסמך', href: undefined }]);
    // the flag alone never makes a document: no url, no "verified"
    expect(publicSafety({ certificates: [{ name: 'CE', verified: true, source: 'seller-claim' }] })!.certificates[0]).toMatchObject({
      verified: false,
      seller_claim: true,
    });
    // the schema: a certificate needs a url or source: seller-claim
    const card = (certs: unknown[]) => ({
      ...JSON.parse(readFileSync(resolve(REPO, 'data/products/vase/vase-cj-matte-frosted-tapered-28.json'), 'utf8')),
      safety: { certificates: certs },
    });
    expect(ProductCardSchema.safeParse(card([{ name: 'CE', verified: false, source: 'seller-claim' }])).success).toBe(true);
    expect(ProductCardSchema.safeParse(card([{ name: 'CE', verified: false }])).success).toBe(false);
    expect(ProductCardSchema.safeParse(card([{ name: 'CE', verified: true, url: 'https://x.test/ce.pdf' }])).success).toBe(true);
    // the three vases are on the sill again (SCH2)
    expect(ProductCardSchema.parse(JSON.parse(readFileSync(resolve(REPO, 'data/products/vase/vase-cj-matte-frosted-tapered-28.json'), 'utf8'))).placement).toBe(
      'sill',
    );
  });
});
