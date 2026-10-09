/**
 * zod for `data/slots/<room>.json`. There is no JSON schema for these files in the repo, so this one is
 * derived from the files themselves (union of every key in the 8 files, 2026-10-09). Unknown keys pass
 * through, because the designer adds fields between versions; the engine only relies on the fields below.
 */
import { z } from 'zod';

/** Relative frame coordinate (0-1). */
const Unit = z.number().min(0).max(1);

export const HotspotSchema = z.looseObject({ u: Unit, v: Unit });
/** [u0, u1, v0, v1], the same order the Design Bible uses for frame boxes. */
export const FrameBoxSchema = z.tuple([Unit, Unit, Unit, Unit]);

export const PlacementSchema = z.enum(['floor', 'wall', 'window', 'surface', 'sofa', 'ceiling', 'sill']);

export const SlotSchema = z.looseObject({
  id: z.string().regex(/^[a-z0-9-]+$/),
  name_he: z.string(),
  category: z.string().optional(),
  placement: z.string(),
  position: z.string().optional(),
  z: z.number(),
  variants: z.number().int().positive().optional(),
  set_of: z.number().int().positive().optional(),
  has_light_layer: z.boolean().optional(),
  has_shadow_layer: z.boolean().optional(),
  fillers: z.array(z.string()).optional(),
  frames: z.array(z.string()).optional(),
  hotspot: z.union([HotspotSchema, z.tuple([Unit, Unit])]).nullable().optional(),
  zoom_frame: z.union([FrameBoxSchema, z.looseObject({})]).nullable().optional(),
});
export type Slot = z.infer<typeof SlotSchema>;

export const BaseLayerSchema = z.looseObject({
  id: z.string(),
  z: z.number(),
  blend: z.enum(['normal', 'multiply', 'screen']).optional(),
  description: z.string().optional(),
  includes: z.array(z.string()).optional(),
});

export const FillerSchema = z.looseObject({
  id: z.string(),
  name_he: z.string(),
  slot: z.string(),
  sold: z.boolean().optional(),
});

export const LightLayersSchema = z.looseObject({
  z: z.number(),
  blend: z.literal('screen'),
  count: z.number().int().optional(),
  slots: z.array(z.string()),
});

export const SlotsFileSchema = z.looseObject({
  room: z.string(),
  version: z.string(),
  view: z.string().optional(),
  views: z.array(z.string()).optional(),
  variants_required: z.number().int().optional(),
  base_layers: z.array(BaseLayerSchema),
  slots: z.array(SlotSchema).min(1),
  fillers: z.array(FillerSchema).optional(),
  light_layers: LightLayersSchema.optional(),
});
export type SlotsFile = z.infer<typeof SlotsFileSchema>;
