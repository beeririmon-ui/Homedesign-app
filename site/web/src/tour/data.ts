/**
 * MOCK1: the tour's room, as tools/make-tour.ts writes it (.generated/tour.<room>.<style>.json), and the second house of
 * the style change: the Nordic house as the room engine already has it (its temporary layers, its default composition).
 */
import json from '@generated/tour.living-room.warm-modern.json';
import type { Box } from '../engine/types';
import { buildLayers } from '../engine/layers';
import { defaultSelection, livingRoom, scene as nordicScene } from '../catalog';
import { mediaUrl } from '../media';

export type TourOption = {
  position: number;
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

export const layerUrl = (slot: TourSlot, position: number, kind: 'product' | 'shadow'): string =>
  mediaUrl(`${slot.src}/${position}.${kind}`, tour.native, 'webp');
export const thumbUrl = (slot: TourSlot, position: number): string => mediaUrl(`${slot.src}/${position}.thumb.360`);

/** the base of a house at the width the composition is made at (the Nordic one: its lo width, the files the Artifact ships) */
export function baseOf(house: HouseId, ext: 'avif' | 'webp'): Draw {
  if (house === WM) return { key: 'wm:base', url: mediaUrl(tour.base.src, tour.native, ext), rect: [0, 1, 0, 1], shadow: false };
  const b = nordicScene.base[0]!;
  return {
    key: 'nordic:base',
    url: mediaUrl(b.src, nordicScene.widths.lo, nordicScene.formats.includes(ext) ? ext : 'webp'),
    rect: [0, 1, 0, 1],
    shadow: false,
  };
}

/**
 * The Nordic house's default composition above its base, in the room engine's own order (engine/layers.ts): the
 * temporary layers the site has today; known and accepted for the mock-up.
 */
export function nordicLayers(): Draw[] {
  return buildLayers(livingRoom, nordicScene, defaultSelection(livingRoom))
    .filter((l) => l.kind !== 'base' && l.blend !== 'screen')
    .map((l) => ({ key: `nordic:${l.key}`, url: mediaUrl(l.src, nordicScene.widths.lo, 'webp'), rect: l.rect, shadow: l.blend === 'multiply' }));
}
export const NORDIC_NAME_HE = 'נורדי';
