/**
 * The catalog the site is built from. Produced by `tools/build-catalog.ts` from the repo
 * (data/slots, data/products, data/economics, docs/house-plan.json), which stays the source of truth.
 *
 * Two outputs with different audiences:
 *   PublicCatalog  · shipped to the browser. No supplier, no cost, no margin.
 *   FullCatalog    · build-time only: D1 seed and admin. Never imported by web code.
 */
import { z } from 'zod';

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
});
export type PublicProduct = z.infer<typeof PublicProductSchema>;

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
  hotspot: z
    .object({ u: Unit, v: Unit, provisional: z.boolean(), visible: z.boolean() })
    .nullable(),
  /** [u0, u1, v0, v1] */
  zoom_frame: z.tuple([Unit, Unit, Unit, Unit]).nullable(),
  options: z.array(SlotOptionSchema),
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

/** Build-time only (seed, admin). */
export type FullProduct = PublicProduct & {
  name_supplier: string;
  category: string | null;
  status: 'candidate' | 'selected' | 'rejected';
  source_path: string;
  supplier: { name: string; url: string; sku: string | null };
  cost_usd_cents: number;
  shipping_usd_cents: number;
  shipping_from_default: boolean;
  shipping_source: 'manual' | 'cj' | 'default';
  sell_qty: number;
  fulfillment_source: import('./schema/economics').FulfillmentSource;
  fx_usd_ils: number;
  nordic_score: number | null;
  economics: import('./pricing').UnitEconomics;
};

export type HiddenProduct = { id: string; slot: string; reason: string };

export type FullCatalog = Omit<PublicCatalog, 'products'> & {
  products: FullProduct[];
  hidden: HiddenProduct[];
  invalid_cards: { path: string; issues: string }[];
  economics: {
    settings: import('./schema/economics').EconomicsSettings;
    defaults_used: string[];
    sources: { settings: string | null; products: string | null; freight: string | null };
  };
};
