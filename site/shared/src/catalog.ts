/**
 * The catalog the site is built from. Produced by `tools/build-catalog.ts` from the repo
 * (data/slots, data/products, data/economics, docs/house-plan.json), which stays the source of truth.
 *
 * Two outputs with different audiences:
 *   PublicCatalog  · shipped to the browser. No supplier, no cost, no margin.
 *   FullCatalog    · build-time only: D1 seed and admin. Never imported by web code.
 */
import { z } from 'zod';
import { PublicSafetySchema } from './safety';
import { PublicOptionsSchema } from './options';

const Unit = z.number().min(0).max(1);

export const ShippingOptionSchema = z.object({
  id: z.enum(['economy', 'express']),
  label_he: z.string(),
  price_agorot: z.number().int().min(0),
  /** economy only: free at or above this subtotal (incl. VAT) */
  free_over_agorot: z.number().int().positive().nullable(),
  days_he: z.string(),
  provisional: z.boolean(),
  is_default: z.boolean(),
});
export type ShippingOption = z.infer<typeof ShippingOptionSchema>;

export const PublicProductSchema = z.object({
  id: z.string(),
  room: z.string(),
  slot: z.string(),
  name_he: z.string(),
  name_provisional: z.boolean(),
  description_he: z.string(),
  price_agorot: z.number().int().positive(),
  compare_at_agorot: z.number().int().positive().nullable(),
  price_provisional: z.boolean(),
  materials_he: z.array(z.string()),
  dimensions_cm: z.object({
    width: z.number().nullable(),
    depth: z.number().nullable(),
    height: z.number().nullable(),
  }),
  color_hex: z.string(),
  shipping_days: z.tuple([z.number(), z.number()]).nullable(),
  notes_he: z.array(z.string()),
  set_of: z.number().int().nullable(),
  variants: z.array(z.object({ id: z.string(), label_he: z.string() })).min(1),
  /**
   * Set or single (P1). null: sold as one sale unit only (no choice shown). Otherwise `price_agorot` is the set of
   * `set_qty` and one piece costs `unit_price_agorot`; `unit_price_estimated` until the studio sets a unit price.
   */
  pack: z
    .object({
      set_qty: z.number().int().min(2),
      unit_price_agorot: z.number().int().positive(),
      unit_price_estimated: z.boolean(),
    })
    .nullable(),
  /** Standards and safety claims from the card (D9); null when the card has none. */
  safety: PublicSafetySchema.nullable(),
  /**
   * Every option of the supplier (card `options`, studio rules ג 2026-10-11), compact (shared/src/options.ts); null when
   * the product is sold as one SKU. Each option is a variant (optionVariantId); `variants` then holds the room's only.
   */
  options: PublicOptionsSchema.nullable(),
  /**
   * Whether the product is sold (2026-11-03). 'unavailable' is shown as "המלאי אינו זמין כעת" with the waiting list
   * (PRE1) and is never added to a cart: NL2 (the no-loss price is more than twice the highest Israeli comparable, or
   * the supplier ships express only), or the slot itself is on hold (AU2, R6Q2). The stored price never changes.
   */
  availability: z.object({
    status: z.enum(['available', 'unavailable']),
    reason: z.enum(['nl2-above-market', 'nl2-express-only', 'slot-on-hold']).nullable(),
  }),
});
export type PublicProduct = z.infer<typeof PublicProductSchema>;
export type Availability = PublicProduct['availability'];

export const SlotOptionSchema = z.object({
  position: z.number().int().min(1),
  product_id: z.string().nullable(),
  placeholder: z.boolean(),
  label_he: z.string(),
  is_default: z.boolean(),
});
export type SlotOption = z.infer<typeof SlotOptionSchema>;

export const CatalogSlotSchema = z.object({
  id: z.string(),
  name_he: z.string(),
  category: z.string().nullable(),
  placement: z.string(),
  z: z.number(),
  set_of: z.number().int().nullable(),
  has_light: z.boolean(),
  has_shadow: z.boolean(),
  fillers_he: z.array(z.string()),
  hotspot: z.object({ u: Unit, v: Unit, provisional: z.boolean(), visible: z.boolean() }).nullable(),
  /** [u0, u1, v0, v1] */
  zoom_frame: z.tuple([Unit, Unit, Unit, Unit]).nullable(),
  options: z.array(SlotOptionSchema),
  /** the slot is on hold (AU2, R6Q2): shown "המלאי אינו זמין כעת" with the waiting list, nothing to choose */
  on_hold: z.object({ decision: z.string(), note_he: z.string() }).nullable(),
});
export type CatalogSlot = z.infer<typeof CatalogSlotSchema>;

export const CatalogRoomSchema = z.object({
  id: z.string(),
  house_room_id: z.string(),
  name_he: z.string(),
  style: z.string(),
  frame: z.string(),
  slots_version: z.string(),
  base_layers: z.array(z.object({ id: z.string(), z: z.number(), blend: z.enum(['normal', 'multiply', 'screen']) })),
  light_slots: z.array(z.string()),
  slots: z.array(CatalogSlotSchema),
  /** Transitions reachable from this room's frame (docs/house-plan.json), used for preloading. */
  exits: z.array(z.object({ transition: z.string(), to_room: z.string(), to_frame: z.string(), reverse: z.boolean() })),
  built: z.boolean(),
});
export type CatalogRoom = z.infer<typeof CatalogRoomSchema>;

export const StyleSchema = z.object({ id: z.string(), name_he: z.string(), available: z.boolean() });

export const PublicCatalogSchema = z.object({
  version: z.string(),
  built_at: z.string(),
  git_commit: z.string(),
  mode: z.enum(['strict', 'provisional']),
  styles: z.array(StyleSchema),
  rooms: z.array(CatalogRoomSchema),
  products: z.array(PublicProductSchema),
  shipping: z.array(ShippingOptionSchema),
  vat_rate: z.number(),
});
export type PublicCatalog = z.infer<typeof PublicCatalogSchema>;

/** One sellable variant with its own price and cost (build-time: seed and admin). */
export type FullVariant = {
  id: string;
  label_he: string;
  /** the option's label on the product page and in the cart, null for a product without options */
  option_label_he: string | null;
  supplier_sku: string | null;
  cost_usd_cents: number;
  shipping_usd_cents: number;
  retail_agorot: number;
  unit_retail_agorot: number | null;
  price_provisional: boolean;
  unit_price_estimated: boolean;
  /** the derived price was raised to this option's own no-loss price (SITE1 floor); the studio's own prices are never raised */
  price_floored: boolean;
  unit_price_floored: boolean;
  /** this option's landed cost and no-loss price (agorot), the evidence for the floor */
  landed_agorot: number;
  no_loss_agorot: number;
  unit_landed_agorot: number | null;
  unit_no_loss_agorot: number | null;
  /** freight of ONE piece (USD cents) by the default line, for the single-piece scenario */
  unit_shipping_usd_cents: number;
  active: boolean;
  in_room: boolean;
  /** the supplier's picture of this option (tools/supplier-images.ts serves it from our media) */
  supplier_image_url: string | null;
};

/** Build-time only (seed, admin). */
export type FullProduct = PublicProduct & {
  /** S7: the card's id (the supplier's words in it); the public `id` is the card's slug (@hd/shared/product-url) */
  card_id?: string;
  /** every variant with its own price and cost; the first is the room's (with no options: the product itself) */
  variants_full?: FullVariant[];
  name_supplier: string;
  category: string | null;
  status: 'candidate' | 'selected' | 'rejected';
  source_path: string;
  supplier: { name: string; url: string; sku: string | null };
  /** the card's first image url and its stated rights (FR-I); the public catalog never carries the supplier url */
  supplier_image: { url: string | null; usage_rights: 'confirmed' | 'unclear' | 'none'; quality: 'high' | 'medium' | 'low' };
  cost_usd_cents: number;
  /** freight of one piece by the default line (USD cents), or of the whole sale when shipping_quoted_for_sale */
  shipping_usd_cents: number;
  shipping_quoted_for_sale: boolean;
  shipping_source: import('./schema/economics').ShippingSource;
  shipping_line: string;
  /** where the price came from (studio/build.py card_economics): the owner, the pricing file, the card, the final round */
  price_source: 'owner' | 'studio' | 'initial-card' | 'initial-leads';
  /** the no-loss facts of the headline (the room's SKU in its sale units): landed cost and the lowest non-losing price */
  landed_agorot: number;
  no_loss_agorot: number;
  /** the highest Israeli comparable the price was set against (il_value), for NL2 */
  highest_comparable_agorot: number | null;
  /** why the product is not sold (studio language, never shown to the customer) */
  availability_note_he: string | null;
  sell_qty: number;
  /** where sell_qty came from: the studio (products.json) or the studio's default rule, and how sure that is */
  sell_qty_source: 'studio' | 'default';
  sell_qty_sure: boolean;
  sell_qty_reason: string | null;
  /** economics of one piece sold alone (pack 'unit'), null when there is no unit option */
  unit_economics: import('./pricing').UnitEconomics | null;
  fulfillment_source: import('./schema/economics').FulfillmentSource;
  fx_usd_ils: number;
  nordic_score: number | null;
  economics: import('./pricing').UnitEconomics;
};

export type HiddenProduct = { id: string; slot: string; reason: string };
/** a card the DS API left unfilled (shared/src/card-draft.ts): not shown, listed for the sourcing-agent */
export type DraftCard = { path: string; fields: string[] };

/**
 * The supplier's first photo of a shown product (FR-I, 2026-10-10), served from our media, never hot-linked:
 * tools/supplier-images.ts downloads it once and writes `.generated/supplier-images.json` (this shape).
 * `usage_rights` is copied from the card (all "unclear" today: to clear with the suppliers before launch).
 */
export type SupplierImage = {
  /** media path without the extension, e.g. products/<id>/supplier.800 (file: <src>.webp, named by the encoding width) */
  src: string;
  /** the picture's own size (a small original is not enlarged) */
  width: number;
  height: number;
  usage_rights: 'confirmed' | 'unclear' | 'none';
};
export type SupplierImageManifest = {
  generated_at: string;
  /** the width the files are encoded at (and named by) */
  width: number;
  products: Record<string, SupplierImage>;
  /**
   * The supplier's picture of each option (card `options`), by product: one file per distinct picture
   * (media/products/<id>/<name>.<width>.webp), and per SKU, in the order of the product's `options.v`, the index of its
   * file (null: none). `artifact`: the file ships with the Artifact (its file limit; the others fall back there).
   */
  options?: Record<string, { files: { name: string; width: number; height: number; artifact: boolean }[]; sku: (number | null)[] }>;
  missing: { id: string; reason: string }[];
};

export type FullCatalog = Omit<PublicCatalog, 'products'> & {
  products: FullProduct[];
  hidden: HiddenProduct[];
  invalid_cards: { path: string; issues: string }[];
  /** cards shown without their `options` because those are broken (the rest of the card is fine) */
  invalid_options?: { path: string; issues: string }[];
  /** cards the DS API left as drafts (colors, visual_weight unfilled): not shown, for the sourcing-agent */
  draft_cards?: DraftCard[];
  /** the studio's own prices that would lose on the site's reading (never raised by the site; a question for the owner) */
  studio_prices_losing?: { id: string; variant_id: string; price_agorot: number; no_loss_agorot: number }[];
  economics: {
    settings: import('./schema/economics').EconomicsSettings;
    defaults_used: string[];
    sources: { settings: string | null; products: string | null; freight: string | null };
  };
};
