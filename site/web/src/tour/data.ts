/**
 * MOCK1: the tour's room, as tools/make-tour.ts writes it (.generated/tour.<room>.<style>.json), and the second house of
 * the style change: the Nordic house as the room engine already has it (its temporary layers, its default composition).
 *
 * MOCK4: three rooms of the warm-modern house — the living room, and the bedroom and the bathroom that
 * tools/make-tour-room.ts builds from their render folders. `tour` is the room the visitor is in: a live binding that
 * `setRoom` changes, so the engine, the effects and the page read the room they are in wherever they read `tour`.
 *
 * MOCK5 (2026-11-24): every room the owner approved — the living room, the bedroom (MB0, MB1), the bath (B2, B1), the
 * kitchen (D1, D2) and the work room (W0). An entry of ROOMS is a frame (its `room` is the frame's key, a file name);
 * the house's room it is of is its `group`, and a room's first frame is where its button lands (tools/tour/frames.json).
 */
import json from '@generated/tour.living-room.warm-modern.json';
import masterJson from '@generated/tour.master.warm-modern.json';
import masterMb1Json from '@generated/tour.master-mb1.warm-modern.json';
import bathJson from '@generated/tour.bath.warm-modern.json';
import bathB1Json from '@generated/tour.bath-b1.warm-modern.json';
import diningJson from '@generated/tour.dining.warm-modern.json';
import diningD2Json from '@generated/tour.dining-d2.warm-modern.json';
import workJson from '@generated/tour.work.warm-modern.json';
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
  /** MOCK4: the card's place in its room's sheet of cards ([x, y, w, h] px of a sheet [w, h]); absent: a file of its own */
  sprite?: [number, number, number, number];
  sheet?: [number, number];
};
/** MOCK4: a layer packed in an atlas page: [page (from 1), x, y, w, h] in the page's pixels */
export type AtlasRef = [number, number, number, number, number];
export type AtlasPage = { src: string; w: number; h: number };
/** a light of a slot's lamp (drawn with it); MOCK5: `slot` null — a lamp outside the frame, its light always on (D2) */
export type TourLight = { id: string; slot: string | null; rect: Box; atlas: Record<string, AtlasRef> };
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
  card_id?: string | null;
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
  /** MOCK4: furniture of the room that is not sold (composed, no mark, not counted) */
  fixed?: boolean;
  /** MOCK4: false: the product is shown at ×1 only (its rights: no close-up, no zoom) */
  closeup?: boolean;
  /** MOCK4: the option whose shadow file an option uses (options that share one to the byte share the file) */
  shadows?: number[];
  /** MOCK4: the product and its shadow in the room's atlas pages, per composition width (absent: files of its own) */
  atlas?: Record<string, { product: AtlasRef; shadow: AtlasRef }>;
  /** MOCK5: the key the owner's count counts the product by in its room (its card's original listing), and its area
   *  in this frame (a product is counted once in its room, in the frame where it is biggest) */
  count_key?: string | null;
  area_px?: number;
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
  base: { src: string; widths: number[]; placeholder: string; formats?: string[] };
  camera: TourCamera;
  cover: number;
  slots: TourSlot[];
  /** MOCK4: the room's name in the tour ("חדר שינה"); absent: the living room */
  room_he?: string;
  /** MOCK4: the slot whose three variants the wheel shows (the bedroom's throw, the bathroom's hand towel) */
  sample?: string;
  /** MOCK4: false: the visitor does not zoom here (the bedroom: the art's rights, ×1 only) */
  zoom?: boolean;
  /** MOCK4: the boxes of the frame no close-up and no zoom may show (canvas UV); MOCK5: one a print whose rights are
   *  not confirmed (the bedroom's two, the kitchen's 386242, the work room's two) */
  avoid?: Box[];
  /** MOCK5: the house's room the frame is of, its camera, and its name in the frame control */
  group?: string;
  frame?: string;
  frame_he?: string | null;
  atlas?: Record<string, { product: AtlasPage[]; shadow: AtlasPage[] }>;
  lights?: TourLight[];
  /** MOCK4: how many products for sale the room shows (the owner's temporary line) */
  for_sale?: number;
};

/** MOCK5: a frame of the tour (a file name); the frames of a room are `FRAMES[group]` */
export type RoomId = 'living-room' | 'master' | 'master-mb1' | 'bath' | 'bath-b1' | 'dining' | 'dining-d2' | 'work';
export const ROOM_IDS = ['living-room', 'master', 'master-mb1', 'bath', 'bath-b1', 'dining', 'dining-d2', 'work'] as const satisfies readonly RoomId[];
export const ROOMS: Record<RoomId, TourData> = {
  'living-room': json as unknown as TourData,
  master: masterJson as unknown as TourData,
  'master-mb1': masterMb1Json as unknown as TourData,
  bath: bathJson as unknown as TourData,
  'bath-b1': bathB1Json as unknown as TourData,
  dining: diningJson as unknown as TourData,
  'dining-d2': diningD2Json as unknown as TourData,
  work: workJson as unknown as TourData,
};
/** MOCK5: the house's rooms in the tour, and their frames (the first is the room's rest frame: tools/tour/frames.json) */
export type GroupId = 'living-room' | 'master' | 'bath' | 'dining' | 'work';
export const FRAMES: Record<GroupId, RoomId[]> = {
  'living-room': ['living-room'],
  master: ['master', 'master-mb1'],
  bath: ['bath', 'bath-b1'],
  dining: ['dining', 'dining-d2'],
  work: ['work'],
};
export const groupOf = (id: RoomId): GroupId => (ROOMS[id].group ?? id) as GroupId;
/** route ch. 5.5: the rooms' names in the tour (a frame is named by its room) */
export const GROUP_HE: Record<GroupId, string> = { 'living-room': 'סלון', master: 'חדר שינה', bath: 'חדר רחצה', dining: 'מטבח', work: 'חדר עבודה' };
export const ROOM_HE = Object.fromEntries(ROOM_IDS.map((id) => [id, GROUP_HE[groupOf(id)]])) as Record<RoomId, string>;
/** the room the visitor is in (a live binding: setRoom changes it for every module that reads it) */
export let tour: TourData = ROOMS['living-room'];
export const roomOf = (): RoomId => tour.room as RoomId;
export function setRoom(id: RoomId): void {
  tour = ROOMS[id];
}
/** the products a frame sells, as the owner's line counts them: a mark each, and a set's every product */
export const forSale = (r: TourData): number => r.for_sale ?? r.slots.reduce((n, s) => n + (s.fixed ? 0 : s.options[0]?.set ? 4 : 1), 0);
/**
 * MOCK5, the owner's line ("X מוצרים למכירה בחדר"): the products a room sells, each once, in the frame where it is
 * biggest (the counting rule, FB10 / V7Q6 with the manager's card count). A product is its card's original listing
 * (`count_key`: registration 1.3.9's copies, and two cards of one SKU, are one product). Returns the room's count and
 * how many of them each frame holds.
 */
export function roomCount(group: GroupId): { total: number; by: Partial<Record<RoomId, number>> } {
  const frames = FRAMES[group];
  if (frames.length === 1 && !ROOMS[frames[0]!].slots.some((s) => s.count_key)) return { total: forSale(ROOMS[frames[0]!]), by: { [frames[0]!]: forSale(ROOMS[frames[0]!]) } };
  const best = new Map<string, { f: RoomId; a: number }>();
  for (const f of frames)
    for (const s of ROOMS[f].slots) {
      if (s.fixed) continue;
      const k = s.count_key ?? `${f}:${s.id}`;
      const a = s.area_px ?? 0;
      const b = best.get(k);
      if (!b || a > b.a) best.set(k, { f, a });
    }
  const by: Partial<Record<RoomId, number>> = {};
  for (const { f } of best.values()) by[f] = (by[f] ?? 0) + 1;
  return { total: best.size, by };
}
export const WM = 'warm-modern';
export const NORDIC = 'nordic';
export type HouseId = typeof WM | typeof NORDIC;

/** a layer of a composition: a texture at a rectangle of the canvas, normal or multiply */
export type Draw = {
  key: string;
  url: string;
  rect: Box;
  shadow: boolean;
  /** MOCK4: its place on an atlas page [x, y, w, h], a light (screen), and whether its texture keeps mip levels */
  sub?: [number, number, number, number];
  screen?: boolean;
  mips?: boolean;
};

/**
 * MOCK2: the width the room is composed at. A phone takes `lo`, which is the rule the room engine already follows
 * (engine/engine.ts: a viewport of 900 CSS px or less composes at scene.widths.lo), and halves both the bytes the
 * phone downloads and the memory the card holds. It is chosen once, when the engine starts: changing it later would
 * mean uploading every texture again, in the middle of a tour.
 */
export const widthFor = (cssWidth: number): number => (__ARTIFACT__ || cssWidth <= 900 ? tour.widths.lo : tour.widths.hi);

export const layerUrl = (slot: TourSlot, position: number, kind: 'product' | 'shadow', width: number): string =>
  mediaUrl(`${slot.src}/${kind === 'shadow' ? (slot.shadows?.[position - 1] ?? position) : position}.${kind}`, width, 'webp');
/** the wheel's card of an option: the product on its own (MOCK2); MOCK4: a room's sheet, where its cards are one file */
export const cardUrl = (o: TourOption): string => mediaUrl(o.card.src);
/** MOCK4: an atlas page's file at a width */
export const atlasUrl = (r: TourData, kind: 'product' | 'shadow', page: number, width: number): string =>
  mediaUrl(r.atlas![String(width)]![kind][page - 1]!.src, width, 'webp');

/** the Nordic layers at the width nearest the composition's: its own files, not a picture stretched to fit */
const nordicWidth = (width: number): number => (__ARTIFACT__ || width <= nordicScene.widths.lo ? nordicScene.widths.lo : nordicScene.widths.hi);

/** the base of a house at the width the composition is made at */
export function baseOf(house: HouseId, ext: 'avif' | 'webp', width: number, r: TourData = tour): Draw {
  if (house === WM)
    return {
      key: r.room === 'living-room' ? 'wm:base' : `${r.room}:base`,
      url: mediaUrl(r.base.src, width, r.base.formats && !r.base.formats.includes(ext) ? 'webp' : ext),
      rect: [0, 1, 0, 1],
      shadow: false,
    };
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
