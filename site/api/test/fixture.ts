/**
 * The test catalog of the Worker's unit tests (api.test.ts, s12.test.ts): products with and without supplier options,
 * a pair sold as a set or one piece (P1), and the triptych, a set of three distinct SKUs (ת9, S12).
 */
import { DEFAULT_SETTINGS, noLossRetailIls, unitEconomics, type FullCatalog, type FullProduct } from '@hd/shared';

export function product(id: string, slot: string, price: number, cost: number, set?: { n: number; unit: number }): FullProduct {
  const sellQty = set?.n ?? 1;
  const base = {
    id,
    room: 'living-room',
    slot,
    name_he: `מוצר ${id}`,
    name_provisional: true,
    description_he: 'תיאור',
    price_agorot: price,
    compare_at_agorot: null,
    price_provisional: true,
    materials_he: ['פשתן'],
    dimensions_cm: { width: 10, depth: null, height: 20 },
    color_hex: '#F4F1EC',
    shipping_days: [12, 30] as [number, number],
    notes_he: [],
    set_of: set ? set.n : null,
    variants: [{ id: `${id}:default`, label_he: 'ברירת מחדל' }],
    pack: set ? { set_qty: set.n, unit_price_agorot: set.unit, unit_price_estimated: true } : null,
    safety: null,
    options: null,
    availability: { status: 'available' as const, reason: null },
  };
  const landed = Math.round((cost * sellQty + 1000 + (sellQty - 1) * Math.max(0, 1000 - 372)) * DEFAULT_SETTINGS.fx_usd_ils);
  return {
    ...base,
    name_supplier: 'Supplier name',
    category: null,
    status: 'candidate',
    source_path: `data/products/${slot}/${id}.json`,
    supplier: { name: 'CJ Dropshipping', url: 'https://example.invalid/p', sku: 'SKU1' },
    supplier_image: { url: 'https://example.invalid/p.jpg', usage_rights: 'unclear', quality: 'medium' },
    cost_usd_cents: cost,
    shipping_usd_cents: 1000,
    shipping_quoted_for_sale: false,
    shipping_source: 'cj',
    shipping_line: 'CJPacket Eub 12-50',
    price_source: 'studio',
    landed_agorot: landed,
    no_loss_agorot: noLossRetailIls(landed / 100, DEFAULT_SETTINGS) * 100,
    highest_comparable_agorot: null,
    availability_note_he: null,
    sell_qty: sellQty,
    sell_qty_source: 'default',
    sell_qty_sure: true,
    sell_qty_reason: null,
    unit_economics: set
      ? unitEconomics(
          { retail_agorot: set.unit, cost_usd_cents: cost, shipping_usd_cents: 1000, fx_usd_ils: DEFAULT_SETTINGS.fx_usd_ils, sell_qty: 1 },
          DEFAULT_SETTINGS,
        )
      : null,
    fulfillment_source: 'dropship_cj',
    fx_usd_ils: DEFAULT_SETTINGS.fx_usd_ils,
    nordic_score: 8,
    economics: unitEconomics(
      { retail_agorot: price, cost_usd_cents: cost, shipping_usd_cents: 1000, fx_usd_ils: DEFAULT_SETTINGS.fx_usd_ils, sell_qty: sellQty },
      DEFAULT_SETTINGS,
    ),
  };
}

export function withOptions(p: FullProduct): FullProduct {
  const v = (id: string, label: string, sku: string, retail: number, cost: number, ship: number, active: boolean, inRoom: boolean) => ({
    id: `${p.id}:${id}`,
    label_he: label,
    option_label_he: label,
    // ת8: the line's base name, without the colour the product's name may carry
    line_name_he: 'ציפית כרית פשתן',
    set_part: false,
    sale_excluded: null,
    supplier_sku: sku,
    cost_usd_cents: cost,
    shipping_usd_cents: ship,
    retail_agorot: retail,
    unit_retail_agorot: null,
    price_provisional: true,
    unit_price_estimated: false,
    price_floored: false,
    unit_price_floored: false,
    landed_agorot: Math.round((cost + ship) * DEFAULT_SETTINGS.fx_usd_ils),
    no_loss_agorot: noLossRetailIls(((cost + ship) * DEFAULT_SETTINGS.fx_usd_ils) / 100, DEFAULT_SETTINGS) * 100,
    unit_landed_agorot: null,
    unit_no_loss_agorot: null,
    unit_shipping_usd_cents: ship,
    active,
    in_room: inRoom,
    supplier_image_url: null,
  });
  const variants_full = [
    v('o-beige45', 'בז\', 45×45 ס"מ', '12000059524978165', 8900, 1117, 1000, true, true),
    v('o-black60', 'שחור, 60×60 ס"מ', '12000059524978199', 11900, 1599, 1100, true, false),
    v('o-green50', 'ירוק, 50×50 ס"מ', '12000059524978177', 9900, 1250, 1000, false, false),
  ];
  return { ...p, variants: variants_full.map(({ id, label_he }) => ({ id, label_he })), variants_full };
}

/** ת9: a set of distinct SKUs (a triptych): print 1 is the set's own; prints 2 and 3 are its parts, never sold alone */
export function triptych(p: FullProduct): FullProduct {
  const v = withOptions(p).variants_full![0]!;
  const print = (n: number, part: boolean) => ({
    ...v,
    id: `${p.id}:${n}+40x60`,
    label_he: `הדפס: הדפס ${n}, מידה: 40×60 ס"מ`,
    option_label_he: '40×60 ס"מ',
    line_name_he: 'שלישיית הדפסים גאומטריים',
    set_part: part,
    // S12: each print its own SKU; the set's own variant names its three parts (the supplier order expands it)
    supplier_sku: `TRIP${n}-40x60`,
    set_skus: part ? null : ['TRIP1-40x60', 'TRIP2-40x60', 'TRIP3-40x60'],
    set_incomplete: null,
    in_room: n === 1,
    retail_agorot: 21900,
    // the set's own economics: the product's cost, and the combined parcel of 3 (unit + 2 × (unit − $3.72))
    cost_usd_cents: p.cost_usd_cents,
    shipping_usd_cents: 1000 + 2 * (1000 - 372),
    unit_shipping_usd_cents: 1000,
  });
  const variants_full = [print(1, false), print(2, true), print(3, true)];
  return { ...p, pack: null, variants: [{ id: variants_full[0]!.id, label_he: variants_full[0]!.label_he }], variants_full };
}

export const catalog: FullCatalog = {
  version: 'testcatalog01',
  built_at: '2026-10-09T00:00:00.000Z',
  git_commit: 'test',
  mode: 'provisional',
  styles: [{ id: 'nordic', name_he: 'נורדי', available: true }],
  rooms: [
    {
      id: 'living-room',
      house_room_id: 'living',
      name_he: 'סלון',
      style: 'nordic',
      frame: 'M0',
      slots_version: '1.3.3',
      base_layers: [{ id: 'shell', z: 0, blend: 'normal' }],
      light_slots: [],
      exits: [],
      built: true,
      slots: [
        {
          id: 'vase',
          name_he: 'אגרטל',
          category: 'ceramics-tableware',
          placement: 'sill',
          z: 16,
          set_of: null,
          has_light: false,
          has_shadow: true,
          fillers_he: [],
          hotspot: { u: 0.25, v: 0.5, provisional: true, visible: true },
          zoom_frame: [0.1, 0.4, 0.3, 0.6],
          options: [
            { position: 1, product_id: 'vase-a', placeholder: false, label_he: 'א', is_default: true },
            { position: 2, product_id: 'vase-b', placeholder: false, label_he: 'ב', is_default: false },
            { position: 3, product_id: null, placeholder: true, label_he: 'ג', is_default: false },
          ],
          on_hold: null,
        },
      ],
    },
  ],
  products: [
    product('vase-a', 'vase', 15900, 1624),
    product('vase-b', 'vase', 25900, 2405),
    // P1: a pair sold as a set of 2 (₪349) or as one piece (₪199, estimated)
    product('candles-a', 'candle-holders', 34900, 907, { n: 2, unit: 19900 }),
    // supplier options (2026-10-11): the room's option, a dearer one, and one out of stock
    withOptions(product('cushion-a', 'cushions', 8900, 1117)),
    // ת9: three different prints sold as the set of 3 only (no single piece)
    triptych(product('prints-a', 'framed-art', 21900, 1200, { n: 3, unit: 6900 })),
  ],
  shipping: [
    { id: 'economy', label_he: 'חסכוני', price_agorot: 2900, free_over_agorot: 29900, days_he: '', provisional: true, is_default: true },
    { id: 'express', label_he: 'מהיר', price_agorot: 5900, free_over_agorot: null, days_he: '', provisional: true, is_default: false },
  ],
  vat_rate: 0.18,
  hidden: [],
  invalid_cards: [],
  economics: { settings: DEFAULT_SETTINGS, defaults_used: ['fx_usd_ils'], sources: { settings: null, products: null, freight: null } },
};
