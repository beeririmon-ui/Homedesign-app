/**
 * MOCK1: the tour's room, as tools/make-tour.ts writes it (.generated/tour.<room>.<style>.json), and the second house of
 * the style change: the Nordic house as the room engine already has it (its temporary layers, its default composition).
 */
import json from '@generated/tour.living-room.warm-modern.json';
import type { Box } from '../engine/types';
import { buildLayers } from '../engine/layers';
import { defaultSelection, livingRoom, scene as nordicScene } from '../catalog';
import { mediaUrl } from '../media';

/** MOCK2 (FB1): what the wheel shows for an option — the product on its own, never a crop of the room */
export type TourCard = {
  src: string;
  w: number;
  h: number;
  /** `studio`: our own product picture, which passed QA; `layer`: the product's own layer, trimmed to it */
  source: 'studio' | 'layer';
};
export type TourOption = {
  position: number;
  card: TourCard;
  /** the option's alpha box, canvas UV */
  box: Box;
  product_id: string | null;
  name_he: string | null;
  price_agorot: number | null;
  price_provisional: boolean;
  available: boolean;
  dims_he: string | null;
  set: boolean;
};
export type TourSlot = {
  id: string;
  name_he: string;
  z: number;
  /** the rectangle every option's layer and shadow is cut to, canvas UV */
  rect: Box;
  depth_m: number;
  kind: 'floor' | 'wall' | 'surface' | 'hang';
  order_a: number;
  hero: boolean;
  /** the card's ground shadow: a thing that stands on the floor or on a surface has one */
  ground: boolean;
  anchors: [number, number][];
  src: string;
  options: TourOption[];
};
export type TourCamera = {
  frame: Box;
  u0: number;
  v0: number;
  kx: number;
  ky: number;
  loc: [number, number, number];
  yaw_deg_left: number;
  room: { x: [number, number]; y: [number, number]; h: number };
};
export type TourData = {
  room: string;
  style: string;
  name_he: string;
  source: string;
  native: number;
  /** MOCK2: the widths a composition is made at — `lo` on a phone, `hi` (the layers' own) on a wider screen */
  widths: { lo: number; hi: number };
  card_width: number;
  aspect: number;
  mobile_center_u: number;
  base: { src: string; widths: number[]; placeholder: string };
  camera: TourCamera;
  cover: number;
  slots: TourSlot[];
};

export const tour = json as unknown as TourData;
export const WM = 'warm-modern';
export const NORDIC = 'nordic';
export type HouseId = typeof WM | typeof NORDIC;

/** a layer of a composition: a texture at a rectangle of the canvas, normal or multiply */
export type Draw = { key: string; url: string; rect: Box; shadow: boolean };

/**
 * MOCK2: the width the room is composed at. A phone takes `lo`, which is the rule the room engine already follows
 * (engine/engine.ts: a viewport of 900 CSS px or less composes at scene.widths.lo), and halves both the bytes the
 * phone downloads and the memory the card holds. It is chosen once, when the engine starts: changing it later would
 * mean uploading every texture again, in the middle of a tour.
 */
export const widthFor = (cssWidth: number): number => (__ARTIFACT__ || cssWidth <= 900 ? tour.widths.lo : tour.widths.hi);

export const layerUrl = (slot: TourSlot, position: number, kind: 'product' | 'shadow', width: number): string =>
  mediaUrl(`${slot.src}/${position}.${kind}`, width, 'webp');
/** the wheel's card of an option: the product on its own (MOCK2) */
export const cardUrl = (o: TourOption): string => mediaUrl(o.card.src);

/** the Nordic layers at the width nearest the composition's: its own files, not a picture stretched to fit */
const nordicWidth = (width: number): number => (__ARTIFACT__ || width <= nordicScene.widths.lo ? nordicScene.widths.lo : nordicScene.widths.hi);

/** the base of a house at the width the composition is made at */
export function baseOf(house: HouseId, ext: 'avif' | 'webp', width: number): Draw {
  if (house === WM) return { key: 'wm:base', url: mediaUrl(tour.base.src, width, ext), rect: [0, 1, 0, 1], shadow: false };
  const b = nordicScene.base[0]!;
  const w = nordicWidth(width);
  return {
    key: `nordic:base:${w}`,
    url: mediaUrl(b.src, w, nordicScene.formats.includes(ext) ? ext : 'webp'),
    rect: [0, 1, 0, 1],
    shadow: false,
  };
}

/**
 * The Nordic house's default composition above its base, in the room engine's own order (engine/layers.ts): the
 * temporary layers the site has today; known and accepted for the mock-up.
 */
export function nordicLayers(width: number): Draw[] {
  const w = nordicWidth(width);
  return buildLayers(livingRoom, nordicScene, defaultSelection(livingRoom))
    .filter((l) => l.kind !== 'base' && l.blend !== 'screen')
    .map((l) => ({ key: `nordic:${l.key}:${w}`, url: mediaUrl(l.src, w, 'webp'), rect: l.rect, shadow: l.blend === 'multiply' }));
}
export const NORDIC_NAME_HE = 'נורדי';
