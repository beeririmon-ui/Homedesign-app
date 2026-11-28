/**
 * MOCK4 (2026-11-18): a room of the tour built from a render folder's own layers (the bedroom MB0 and the bathroom B2,
 * stage one with FB10), behind HD_PUBLIC=0. The same engine as the living room (web/src/tour/): the base, then every
 * product in z order with its shadow under it (multiply), then the light (screen). Reads tools/tour/<frame>.<style>.json
 * and the folder's manifest; never changes either. Writes:
 *
 *   .generated/tour.<frame>.<style>.json     the frame as the tour's engine reads it (the shape of tools/make-tour.ts's),
 *                                            with what is new here: the light, the atlas pages, the cards' sheet, the
 *                                            sample slot, the furniture that is not sold, and the ×1-only boxes
 *   web/public/media/tour/<frame>/<style>/   the base at two widths (`lo` a phone's, `hi` the layers' own); the sample
 *                                            slot's options one file each (the wheel swaps them); every other product,
 *                                            its shadow and the light packed in atlas pages (two files a room instead
 *                                            of forty: the Artifact holds 255 files a publish); the cards' sheet
 *
 * MOCK5 (2026-11-24, briefs/site-mock5-house-rooms-2026-11-24.md): every frame the owner approved — MB0 and MB1, B2 and
 * B1, D1 and D2 (−86), W0 — through this one tool. What it learned:
 *  - a frame of a manifest with several frames (the kitchen's: `frame` on every layer and light, `bases`, retired layers
 *    kept for the record) is chosen by the config's `frame_id`; retired layers never compose;
 *  - the warm-modern cameras are registered only in docs/house-plan.json `style_shells_1_3_1.<style>.<room>.cameras`
 *    (registration 1.3.9, its log ch. 6.1): they are read there first, so D2 is −86 and not the Nordic −91;
 *  - a slot may have several layers: the same product twice (MB1's two sconces) is one product, drawn from one piece
 *    of the two (they never overlap, checked); two products in one slot (the kitchen's condiment and sink sets) are two
 *    products of the tour, a config entry each (`of`: the manifest's slot, `product`: the layer's product);
 *  - a light names its lamps (`lamps`) rather than its slot; a lamp that is not in the frame (D2's pendant) gives a light
 *    that is always on; where the manifest's formula multiplies the light by (1 − every alpha), that is done here, on
 *    the default composition, so the engine's plain screen gives the folder's composite (a sample option of another
 *    shape differs under the default's alpha only: the kitchen's V3, at most 4 levels in 0.1% of the frame);
 *  - the sample slot has two options or three (B1's mat and the kitchen's pendant have two), or there is none (MB1, D2);
 *  - the rights rule: every print the config names (`prints`) is looked up on its card (`usage_rights`); a print whose
 *    rights are not "confirmed" is ×1 only — no close-up, no zoom in its frame, and every close-up keeps out of it
 *    (`avoid`, one box a print);
 *  - every product carries the key the owner's count counts it by (the card, through `mirror_of` to its original, and
 *    the supplier's listing: the bath's two dispensers are one SKU) and its area, so a room counts a product once, in
 *    the frame where it is biggest.
 *
 * The rest of a layer's rules are tools/make-tour.ts's: a layer is cut to its slot's rectangle (its alpha and wherever
 * its shadow darkens, 8 px round it), rounded per width exactly as the engine rounds it, the product near-lossless and
 * the shadow lossless. Before anything is written, the source layers composed in this order by the manifest's own
 * formula (the render tools' compose_one and light_one, to the last rounding) must give the folder's approved composite
 * to the pixel.
 *
 * A product's name and price are the shop's own record of its card (.generated/catalog.tour-rooms.full.json, the same
 * pricing path as every product; npm run tour builds it first). A card the shop cannot price yet keeps its slot's name.
 *
 * MOCK6 (2026-11-25, briefs/site-mock6-kids-rooms-2026-11-25.md): the boy's and the girl's rooms (K-boy, K-girl), and
 * B1's ledge planter. What it learned:
 *  - one style shell for two rooms (`shell`: style_shells_1_3_1.warm-modern.kids holds K-boy and K-girl); the girl's
 *    room is the boy's shifted in Y (`offset`: the shell's girl_offset_y), so her slots' plan places shift with it, and
 *    her camera is checked to be the boy's plus that offset;
 *  - a light's lamp may be named by its product (the kids' pendant), not only by its slot;
 *  - the safety rule (AP2-NEW, QA K-I7): a product may be shown and not sold (`sale`: "blocked", the Roman blind without
 *    EN 13120, the pendant without CE in a kids' room) or wait for its standard ("notify", the toys until EN 71). Either
 *    way it has no price and no cart here, and its slot carries the line the visitor reads and why;
 *  - the sample's options sit on the frame's own atlas pages (MOCK5 gave them two pages of their own): two files fewer a
 *    frame with a wheel, so the kids' rooms fit the Artifact's 255 files;
 *  - a wheel of many options (4–12, the kids' art sets to come, FB12): each option is a patch of its own (its product and
 *    its shadow, a file each), which the page loads only when the option is chosen (`lazy`), never in the background.
 */
import sharp, { type OverlayOptions } from 'sharp';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { basename, isAbsolute, join, relative } from 'node:path';
import { GENERATED, MEDIA_OUT, REPO, repoPath, sitePath } from './lib/paths';
import { nearness, type DepthCfg } from './lib/depth';

type Box = [number, number, number, number];
type SlotCfg = {
  card: string | null;
  kind: 'floor' | 'wall' | 'surface' | 'hang';
  name_he?: string;
  anchors?: [number, number][];
  depth_m?: number;
  fixed?: boolean;
  closeup?: boolean;
  hero?: boolean;
  /** MOCK5: the manifest's slot this product is in, when the tour's id is another (a second product of one slot) */
  of?: string;
  /** MOCK5: which product of the manifest's slot (a slot with two products); absent: every layer of the slot */
  product?: string;
  /** MOCK6, the safety rule: shown and not sold here ("blocked"), or waiting for its standard ("notify") */
  sale?: 'blocked' | 'notify';
  /** MOCK6: the short line the visitor reads in place of a price ("לא במכירה"), and why, in a sentence */
  sale_he?: string;
  sale_why_he?: string;
};
type Cfg = {
  room: string;
  /** MOCK5: the house's room this frame is of (the room buttons, the owner's count); absent: `room` */
  group?: string;
  /** MOCK5: the frame of a manifest with several (the kitchen's D1 / D2) */
  frame_id?: string;
  /** MOCK5: the frame's name in the frame control ("קיר המיטה") */
  frame_he?: string;
  style: string;
  name_he: string;
  layers: string;
  manifest: string;
  truth: string;
  /** MOCK7: the frame's depth for the transitions (tools/lib/depth.ts); absent: the page's fallback */
  depth?: DepthCfg;
  /** MOCK7: the camera is the manifest's own (`camera`: loc, yaw, lens, u0, v0), not yet registered in the house plan
   *  (M0-W, the new living room); its lens sets the projection (24 mm: kx 0.6667, ky 1.1852) */
  camera_from_manifest?: boolean;
  /** MOCK7: a folder of its own under tour/<room>/<style>/ (the living room's M0-W, beside the phase 2 room's M0) */
  media?: string;
  /** MOCK7: false: the room has no style change (the Nordic house is the old M0's, another camera) */
  styles?: boolean;
  /** MOCK7: the content hashes this frame is pinned to (tools/tour/living-room.pin.json); `--write-pin` writes them */
  pin?: string;
  /** MOCK7: a default frame the render tools' finish composed (FB15's rooms, M0-W: RGB shadows, its own rounding): the
   *  gate composes the layers as that finish does, at the truth's size (tools/tour/gate_finish.py; `frame_box_from`:
   *  the folder's file with the full-precision box, for a 1920 frame) */
  /** MOCK8: `max`: the largest difference a finish gate accepts (M0-W fix1: the render's own recompose of its stored
   *  frame is off by 1 in about 3,300 px, checks-m0w-fix1.json) */
  gate?: { kind: 'finish' | 'fb16'; frame_box_from?: string; max?: number };
  /** MOCK8 (FB16): the frame of the manifest's `fb16.frames` (default: `frame_id`, else `camera`): its grade (Lab) is
   *  applied on the composite by the engine, and its glows over the graded frame (screen; B1's glass: multiply) */
  fb16_frame?: string;
  /** MOCK8: the sample's options from a manifest's wheel (`<key>.wheel`: `order`, `sets`; M0-W's cushion sets) */
  wheel_sets?: string;
  /** MOCK8: an option's name in the wheel, by its product (the cushion sets: no card of their own) */
  option_names_he?: Record<string, string>;
  /** MOCK7: the lights on pages of their own, lossy (M0-W: three lamps whose light covers most of the frame; smooth,
   *  so a lossy page costs a small part of a lossless one, and a phone's first load stays under 3 MB) */
  light_pages?: 'lossy';
  /** MOCK7: the slot of a light the manifest names no lamp for (FB15's code lights: the kitchen sconce's pool), by its
   *  file's name */
  light_slots?: Record<string, string>;
  /** MOCK5: the frame's base (default plate.png) */
  plate?: string;
  plan: string;
  camera: string;
  room_plan: string;
  /** MOCK6: the style shell the camera is registered in, when it is not the room's own (the kids' rooms share `kids`) */
  shell?: string;
  /** MOCK6: a room that is another shifted in Y (the girl's): the shell's key that holds the shift, and the camera it
   *  shifts (the slots' plan places are the other room's, so they shift with it) */
  offset?: { key: string; from_camera: string };
  slots_file: string;
  sample: string | null;
  /** MOCK12 (plan wm-wheels 7.2): the frame's wheels, a ring each, by the tour's slot id (absent: `sample` and every
   *  slot the manifests give options to). Naming them keeps a wheel out until it is wanted */
  wheels?: string[];
  /** MOCK12: render-agent's per-room wheel manifest next to the room's (the M0-W `manifest-wheel*.json` format: every
   *  `<key>.wheel` = { slot, default, order, sets }, its `variants` and its `default: false` layers). The one line a
   *  room's new wheels take: every wheel in it becomes a wheel of this frame */
  wheel_manifest?: string;
  avoid?: string | null;
  /** MOCK5: the prints of the frame: each one's card is read for its rights (×1 only unless "confirmed") */
  prints?: string[];
  zoom?: boolean;
  slots: Record<string, SlotCfg>;
  variant_cards?: Record<string, string>;
  /** MOCK6: where the shop's name is only composed (`name_provisional`: a slot's name, a material and a colour, the
   *  slot often the living room's: "כריות ושמיכה" for the girl's cushions), the tour shows the slot's name instead */
  names?: 'slot-when-provisional';
};
type Light = { file: string; blend: string; slot?: string; product?: string; lamps?: string[]; frame?: string; retired?: unknown };
type MLayer = {
  slot: string;
  product: string;
  z: number;
  layer: string;
  shadow: string;
  card?: string;
  sold?: boolean;
  fixed?: boolean;
  default?: boolean;
  frame?: string;
  sub?: number;
  retired?: unknown;
};
type MVariant = { slot: string; product: string; default: boolean; layer: string; shadow: string; card?: string; frame?: string; retired?: unknown };
type Manifest = {
  id: string;
  /** MOCK7: the manifest's own camera (M0-W) */
  camera?: { loc: [number, number, number]; yaw: number; lens?: number; u0: number; v0: number; status?: string };
  canvas: [number, number];
  frame_box: [number, number, number, number];
  compose?: unknown;
  layers: MLayer[];
  light: Light | Light[];
  variants?: MVariant[];
  /** MOCK8 (FB16): the house light pass, per frame: the grade (Lab) and the glows over the graded frame */
  fb16?: {
    frames: Record<string, { grade: Fb16Grade; glows: { file: string; blend: 'screen' | 'multiply'; slot: string | null; product?: string | null }[] }>;
  };
} & Record<string, unknown>;
type Fb16Grade = { L_knots_in: number[]; L_knots_out: number[]; L_interp: string; da: number; db: number; ab: string };

const CFG = process.argv[2] ?? 'tools/tour/master.warm-modern.json';
const read = <T>(p: string): T => JSON.parse(readFileSync(p, 'utf8')) as T;
const fail = (msg: string): never => {
  console.error(`make-tour-room ${CFG}: ${msg}`);
  process.exit(1);
};
const c = read<Cfg>(sitePath(CFG));
const dir = repoPath(c.layers);
const m = read<Manifest>(join(dir, c.manifest));
const [W, H] = m.canvas;
const PLATE = c.plate ?? 'plate.png';
const GROUP = c.group ?? c.room;
const sha = (f: string) => createHash('sha256').update(readFileSync(f)).digest('hex');

// ---------- the frame's layers: z, then the manifest's own `sub` and order where two share a z ----------
// (a manifest of one frame may use `frame` for something else: MB0's variants name their composite there)
const inFrame = (x: { frame?: string; retired?: unknown }) => (!c.frame_id || x.frame === c.frame_id) && !x.retired;
const indexed = m.layers.map((l, i) => ({ l, i })).filter((x) => inFrame(x.l));
const layers = indexed
  .filter((x) => x.l.default !== false)
  .sort((a, b) => a.l.z - b.l.z || (a.l.sub ?? 0) - (b.l.sub ?? 0) || a.i - b.i)
  .map((x) => x.l);
/** the tour's slot a layer is (a config entry whose manifest slot and product it matches) */
const tourSlotOf = (l: { slot: string; product: string }): string => {
  const hits = Object.entries(c.slots).filter(([id, s]) => (s.of ?? id) === l.slot && (!s.product || s.product === l.product));
  if (hits.length !== 1) fail(`the layer ${l.slot} / ${l.product} matches ${hits.length} config slots, not 1`);
  return hits[0]![0];
};
const pieces = new Map<string, MLayer[]>();
for (const l of layers) {
  const id = tourSlotOf(l);
  pieces.set(id, [...(pieces.get(id) ?? []), l]);
}
for (const id of Object.keys(c.slots)) if (!pieces.has(id)) fail(`${CFG} names slot ${id}, which the frame does not compose`);
/** the tour's slots in the order of their first layer */
const order = [...pieces.keys()];
const zOf = (id: string) => pieces.get(id)![0]!.z;

// ---------- virtual layers: a slot's several layers of one product as one, and a light masked by every alpha ----------
const virt = new Map<string, { data: Buffer; ch: 1 | 3 | 4 }>();
const src = (f: string) => {
  const v = virt.get(f);
  return v ? sharp(v.data, { raw: { width: W, height: H, channels: v.ch } }) : sharp(join(dir, f));
};

// ---------- raw pixels ----------
const cache = new Map<string, Buffer>();
const raw = async (f: string, ch: 1 | 3 | 4): Promise<Buffer> => {
  const k = `${f}:${ch}`;
  let b = cache.get(k);
  if (b) return b;
  const v = virt.get(f);
  if (v && v.ch === ch) b = v.data;
  else {
    const img = src(f);
    const pipe = ch === 4 ? img.ensureAlpha() : ch === 3 ? img.removeAlpha().toColourspace('srgb') : img.removeAlpha().toColourspace('b-w');
    const { data, info } = await pipe.raw().toBuffer({ resolveWithObject: true });
    if (info.width !== W || info.height !== H || info.channels !== ch) fail(`${f} is ${info.width}×${info.height}×${info.channels}, not ${W}×${H}×${ch}`);
    b = data;
  }
  cache.set(k, b);
  return b;
};

// ---------- the lights: their slot (named, by product, or by the first lamp); masked where the formula says so ----------
const MASK_LIGHT = /times \(1 - every alpha\)/.test(typeof m.compose === 'string' ? m.compose : JSON.stringify(m.compose ?? ''));
const lightSlot = (x: Light): string | null => {
  const named = x.slot ?? layers.find((l) => l.product === x.product)?.slot ?? x.lamps?.[0]?.replace(/-(east|west)$/, '') ?? c.light_slots?.[basename(x.file)];
  if (!named) fail(`light ${x.file}: no slot, product or lamp`);
  // a lamp outside the frame (D2's pendant): its light is part of the room, always on. MOCK6: a lamp may be named by
  // its product (the kids' pendant, `ceiling-lights-…-warm-light`)
  const l = layers.find((y) => y.slot === named) ?? layers.find((y) => y.product === named);
  return l ? tourSlotOf(l) : null;
};
/** MOCK7: FB15's code lights name their file from the render root's style folder, or from the room's (`warm-modern/
 *  <folder>/light/…`, `<folder>/light/…`) */
const lightFile = (f: string): string => (existsSync(join(dir, f)) ? f : f.replace(new RegExp(`^(${c.style}/)?${basename(dir)}/`), ''));
const lightEntries = (Array.isArray(m.light) ? m.light : [m.light]).filter(inFrame).map((x) => {
  if (x.blend !== 'screen') fail(`light ${x.file} is ${x.blend}, not screen`);
  return { file: lightFile(x.file), slot: lightSlot(x) };
});

// ---------- MOCK8 (FB16): the frame's grade and glows ----------
/** the gate's limits: the finish's own grain and light wrap (fb15's finish against its composite: mean about 1, p99 4–10) */
const FB16_GATE = { mean: 1.5, p99: 10, over8: 0.02 } as const;
const FB16_FRAME = c.fb16_frame ?? c.frame_id ?? c.camera;
const f16 = c.gate?.kind === 'fb16' ? (m.fb16?.frames[FB16_FRAME] ?? fail(`${c.manifest} has no fb16 frame ${FB16_FRAME}`)) : null;
if (f16 && !/monotone cubic/.test(f16.grade.L_interp))
  fail(`fb16 ${FB16_FRAME}: the grade's L curve is ${f16.grade.L_interp}, not the monotone cubic the engine draws`);
/** the fb16 tool's pchip (assets/renders/tools/fb16/fb16.py): the slopes at the knots (Fritsch–Carlson, weighted) */
function pchipSlopes(xk: number[], yk: number[]): number[] {
  const h = xk.slice(1).map((x, i) => x - xk[i]!);
  const d = h.map((hi, i) => (yk[i + 1]! - yk[i]!) / hi);
  const mm = yk.map(() => 0);
  mm[0] = d[0]!;
  mm[mm.length - 1] = d[d.length - 1]!;
  for (let i = 1; i < xk.length - 1; i++)
    if (d[i - 1]! * d[i]! > 0) {
      const w1 = 2 * h[i]! + h[i - 1]!;
      const w2 = h[i]! + 2 * h[i - 1]!;
      mm[i] = (w1 + w2) / (w1 / d[i - 1]! + w2 / d[i]!);
    }
  return mm.map((x) => +x.toFixed(6));
}
const grade = f16
  ? { kin: f16.grade.L_knots_in, kout: f16.grade.L_knots_out, m: pchipSlopes(f16.grade.L_knots_in, f16.grade.L_knots_out), da: f16.grade.da, db: f16.grade.db }
  : null;
if (grade && (grade.kin.length !== 5 || grade.kout.length !== 5)) fail(`fb16 ${FB16_FRAME}: the engine's grade takes 5 knots, not ${grade.kin.length}`);
/** the glows, over the graded frame: their file (from the folder), their slot (a lamp's glow goes with it; the sample's
 *  default lamp's only with that option), screen or multiply */
const mdir = join(dir, c.manifest, '..');
const glowEntries = (f16?.glows ?? []).map((g) => {
  const file = relative(dir, join(mdir, g.file));
  const l = g.slot ? layers.find((y) => y.slot === g.slot) : undefined;
  const slot = l ? tourSlotOf(l) : null;
  // a lamp's glow goes with its default option only (MOCK8: the kitchen's pendant; MOCK12: any wheel's)
  return { file, mul: g.blend === 'multiply', slot, pos: undefined as number | undefined };
});

// ---------- MOCK12: the frame's wheels (MOCK4–11: one, the sample slot), and every wheel slot's options ----------
type Opt = { product: string; layer: string; shadow: string; card: string | null };
type WheelSpec = {
  slot: string;
  default: string;
  order: string[];
  sets: Record<string, { layer: string; shadow: string; default?: boolean; products?: { card_id?: string }[] }>;
};
const isSpec = (w: unknown): w is WheelSpec => {
  const x = w as Partial<WheelSpec> | null;
  return !!x && typeof x === 'object' && typeof x.slot === 'string' && !!x.sets && typeof x.sets === 'object' && Array.isArray(x.order);
};
/** a manifest's wheels in the M0-W format: every `<key>.wheel` with a slot, sets and an order (and `wheels`, a list or a
 *  map of them, should a manifest hold several that way) */
function wheelSpecs(mm: Record<string, unknown>): WheelSpec[] {
  const list = Object.values(mm).flatMap((v) => (v && typeof v === 'object' && isSpec((v as { wheel?: unknown }).wheel) ? [(v as { wheel: WheelSpec }).wheel] : []));
  const more = mm.wheels;
  for (const w of Array.isArray(more) ? more : more && typeof more === 'object' ? Object.values(more) : []) if (isSpec(w)) list.push(w);
  return list;
}
if (c.wheel_sets && !isSpec((m[c.wheel_sets] as { wheel?: unknown } | undefined)?.wheel)) fail(`${c.manifest} has no ${c.wheel_sets}.wheel`);
const wm = c.wheel_manifest ? read<Manifest>(join(dir, c.wheel_manifest)) : null;
/** a manifest's extra options of a manifest slot: its `default: false` layers, its variants and its wheels' other sets */
function extras(mm: Manifest, ms: string, tourId: string, def: MLayer, from: string): Opt[] {
  const cardOf = (product: string, card?: string): string | null =>
    c.variant_cards?.[product] ?? (card ? basename(card, '.json') : (c.slots[tourId]?.card ?? null));
  const out: Opt[] = [];
  for (const l of mm.layers.filter((x) => inFrame(x) && x.default === false && x.slot === ms)) out.push({ ...l, card: cardOf(l.product, l.card) });
  for (const v of (mm.variants ?? []).filter((x) => !!x && typeof x === 'object' && inFrame(x) && x.slot === ms && !x.default))
    out.push({ ...v, card: cardOf(v.product, v.card) });
  // MOCK8: a wheel of sets (M0-W's cushions: `cushions.wheel`, B the default, then A and C); MOCK12: render-agent's
  for (const w of wheelSpecs(mm).filter((x) => x.slot === ms)) {
    const d = w.sets[w.default] ?? fail(`${from} ${ms}.wheel: no default set ${w.default}`);
    if (d.layer !== def.layer || d.shadow !== def.shadow) fail(`${from} ${ms}.wheel: the default set is not the frame's ${ms} layer`);
    for (const k of w.order.filter((x) => x !== w.default)) {
      const v = w.sets[k] ?? fail(`${from} ${ms}.wheel: no set ${k}`);
      // a set of one product is that product (its card); a set of several (the cushions) is `set-<key>`, without a card
      const one = v.products?.length === 1 ? (v.products[0]!.card_id ?? null) : null;
      const product = one ? k : k.startsWith('set-') ? k : `set-${k}`;
      out.push({ product, layer: v.layer, shadow: v.shadow, card: one ?? cardOf(product) });
    }
  }
  return out;
}
/** every tour slot's options beyond its default: from the room's manifest and (MOCK12) its wheel manifest */
const optsOf = new Map<string, Opt[]>();
for (const [id, ps] of pieces) {
  const ms = c.slots[id]!.of ?? id;
  const more = [...extras(m, ms, id, ps[0]!, c.manifest), ...(wm ? extras(wm, ms, id, ps[0]!, c.wheel_manifest!) : [])];
  // an option both manifests list is one option
  const seen = new Set([ps[0]!.layer]);
  const uniq = more.filter((o) => !seen.has(o.layer) && !!seen.add(o.layer));
  if (!uniq.length) continue;
  if (ps.length !== 1) fail(`the wheel slot ${id} has ${ps.length} layers`);
  optsOf.set(id, [{ product: ps[0]!.product, layer: ps[0]!.layer, shadow: ps[0]!.shadow, card: c.slots[id]!.card }, ...uniq]);
}
/** the frame's wheels in order: the config's, else the sample first and then every slot with options */
function wheelIds(): string[] {
  return c.wheels ?? [...new Set([...(c.sample ? [c.sample] : []), ...optsOf.keys()])];
}
const WHEELS = wheelIds();
for (const id of WHEELS) {
  if (!c.slots[id]) fail(`the wheel ${id} is not a slot of ${CFG}`);
  const n = optsOf.get(id)?.length ?? 0;
  if (n < 2 || n > 12) fail(`the wheel slot ${id} has ${n} options, not 2 to 12`);
}
const wheelOpts = new Map(WHEELS.map((id) => [id, optsOf.get(id)!]));
const isWheel = (id: string) => wheelOpts.has(id);
/** MOCK6: a wheel of many options (4–12): a patch file each, loaded only when chosen; two or three sit on the atlas */
const many = (id: string) => wheelOpts.get(id)!.length > 3;
// options a config's own `wheels` leaves out (a wheel not wanted yet) are said and never composed
const leftOut = [...optsOf.keys()].filter((id) => !isWheel(id));
if (leftOut.length) console.log(`make-tour-room ${CFG}: options left out of the wheels: ${leftOut.join(', ')}`);
for (const g of glowEntries) if (g.slot && isWheel(g.slot)) g.pos = 1;

// ---------- the gate: the source layers in this order give the approved composite, to the pixel ----------
/** numpy's rint: half to even (the render tools' compose_one and light_one round with it) */
const rint = (x: number) => {
  const f = Math.floor(x);
  const d = x - f;
  return d > 0.5 ? f + 1 : d < 0.5 ? f : f % 2 === 0 ? f : f + 1;
};
/** every default alpha of the frame, as the render tools accumulate it: 1 − Π(1 − a) */
let aAll: Float64Array | null = null;
let gateNote = '';
{
  const st = new Float64Array(W * H * 3);
  const plate = await raw(PLATE, 3);
  for (let i = 0; i < st.length; i++) st[i] = plate[i]! / 255;
  const acc = new Float64Array(W * H);
  for (const l of layers) {
    const p = await raw(l.layer, 4);
    const s = await raw(l.shadow, 1);
    for (let i = 0; i < W * H; i++) {
      const al = p[i * 4 + 3]!;
      const sh = s[i]!;
      if (al === 0 && sh === 255) continue;
      const a = al / 255;
      for (let k = 0; k < 3; k++) st[i * 3 + k] = rint(((st[i * 3 + k]! * 255 * sh) / 255) * (1 - a) + p[i * 4 + k]! * a) / 255;
      if (al) acc[i] = 1 - (1 - acc[i]!) * (1 - al / 255);
    }
  }
  if (MASK_LIGHT) aAll = acc;
  for (const [n, e] of lightEntries.entries()) {
    const L = await raw(e.file, 3);
    let Lm = L;
    if (aAll) {
      // the light under the products goes, as the render tools take it out: rint(L × (1 − every alpha))
      Lm = Buffer.alloc(L.length);
      for (let i = 0; i < W * H; i++) for (let k = 0; k < 3; k++) Lm[i * 3 + k] = Math.min(255, rint(L[i * 3 + k]! * (1 - aAll[i]!)));
      const name = `virtual/light-${n}.png`;
      virt.set(name, { data: Lm, ch: 3 });
      cache.set(`${name}:3`, Lm);
      e.file = name;
    }
    for (let i = 0; i < st.length; i++) if (Lm[i]) st[i] = (255 - rint(((255 - st[i]! * 255) * (255 - Lm[i]!)) / 255)) / 255;
  }
  if (c.gate?.kind === 'fb16') {
    // MOCK8 (FB16): the stack on the frame's fb16 base, graded and with its glows, against the folder's fb16 frame. The
    // fb16 frame is the grade of the render's finished frame (its grain and light wrap: the stack never carried them,
    // MOCK7 gated it against the composite before the finish), so this gate is a measure with limits
    const args = [
      sitePath('tools/tour/gate_fb16.py'),
      dir,
      c.manifest,
      c.truth,
      repoPath('assets/renders/tools/finish'),
      repoPath('assets/renders/tools/fb16'),
    ];
    const opts = ['--frame', FB16_FRAME, '--plate', PLATE, ...(c.gate.frame_box_from ? ['--box', c.gate.frame_box_from] : [])];
    const out = execFileSync('python3.12', ['-I', ...args, ...opts], { encoding: 'utf8' });
    const g = JSON.parse(out) as { max: number; mean: number; p99: number; over8: number; size: [number, number] };
    if (g.mean > FB16_GATE.mean || g.p99 > FB16_GATE.p99 || g.over8 > FB16_GATE.over8)
      fail(`the stack graded misses ${c.truth}: mean ${g.mean}, p99 ${g.p99}, ${(g.over8 * 100).toFixed(2)}% over 8 (limits ${JSON.stringify(FB16_GATE)})`);
    gateNote = `${c.truth} (${g.size.join('×')}, fb16: the grade and the glows on the stack) within the finish's grain: mean ${g.mean}, p99 ${g.p99}, ${(g.over8 * 100).toFixed(2)}% over 8`;
  } else if (c.gate?.kind === 'finish') {
    // MOCK7: the folder's own finish (its compose, its frame view), read only, against the folder's default frame
    const args = [sitePath('tools/tour/gate_finish.py'), dir, c.manifest, c.truth, repoPath('assets/renders/tools/finish')];
    const opts = [...(c.frame_id ? ['--frame', c.frame_id] : []), '--plate', PLATE, ...(c.gate.frame_box_from ? ['--box', c.gate.frame_box_from] : [])];
    const out = execFileSync('python3.12', ['-I', ...args, ...opts], { encoding: 'utf8' });
    const g = JSON.parse(out) as { max: number; differing: number; size: [number, number] };
    if (g.max > (c.gate.max ?? 0)) fail(`the layers, as the finish composes them, miss ${c.truth} on ${g.differing} channel values (max ${g.max})`);
    gateNote = g.differing
      ? `${c.truth} (${g.size.join('×')}, the finish's frame) within ${g.max} on ${g.differing} channel values, as the render's own recompose`
      : `${c.truth} (${g.size.join('×')}, the finish's frame) to the value`;
  } else {
    const truth = await raw(c.truth, 3);
    let bad = 0;
    for (let i = 0; i < st.length; i++) if (Math.min(255, Math.max(0, rint(st[i]! * 255))) !== truth[i]) bad++;
    if (bad) fail(`the layers in this order miss ${c.truth} on ${bad} channel values`);
  }
}
const lights = lightEntries.map((x) => x.file);

// ---------- one product's several layers (MB1's two sconces) as one piece: they never overlap ----------
type Piece = { layer: string; shadow: string; product: string };
const slotPiece = new Map<string, Piece>();
for (const [id, ps] of pieces) {
  if (ps.length === 1) {
    slotPiece.set(id, ps[0]!);
    continue;
  }
  if (new Set(ps.map((p) => p.product)).size !== 1) fail(`slot ${id} has layers of ${ps.length} products: give each its own config entry`);
  const L = Buffer.alloc(W * H * 4);
  const S = Buffer.alloc(W * H, 255);
  const used = new Uint8Array(W * H);
  for (const p of ps) {
    const a = await raw(p.layer, 4);
    const s = await raw(p.shadow, 1);
    for (let i = 0; i < W * H; i++) {
      if (a[i * 4 + 3] === 0 && s[i] === 255) continue;
      if (used[i]) fail(`slot ${id}: its layers overlap at ${i % W}, ${(i / W) | 0}`);
      used[i] = 1;
      a.copy(L, i * 4, i * 4, i * 4 + 4);
      S[i] = s[i]!;
    }
  }
  const layer = `virtual/${id}.layer.png`;
  const shadow = `virtual/${id}.shadow.png`;
  virt.set(layer, { data: L, ch: 4 });
  virt.set(shadow, { data: S, ch: 1 });
  slotPiece.set(id, { layer, shadow, product: ps[0]!.product });
}

// ---------- the regions: a product's alpha and its shadow; a light where it adds ----------
type Px = { x0: number; y0: number; x1: number; y1: number };
const empty = (): Px => ({ x0: W, y0: H, x1: -1, y1: -1 });
const grow = (b: Px, x: number, y: number) => {
  if (x < b.x0) b.x0 = x;
  if (x > b.x1) b.x1 = x;
  if (y < b.y0) b.y0 = y;
  if (y > b.y1) b.y1 = y;
};
const PAD = 8;
const padRect = (r: Px): Px => ({ x0: Math.max(0, r.x0 - PAD), y0: Math.max(0, r.y0 - PAD), x1: Math.min(W, r.x1 + 1 + PAD), y1: Math.min(H, r.y1 + 1 + PAD) });
async function alphaBox(f: string): Promise<Px> {
  const p = await raw(f, 4);
  const b = empty();
  for (let i = 0; i < W * H; i++) if (p[i * 4 + 3]! > 0) grow(b, i % W, (i / W) | 0);
  if (b.x1 < 0) fail(`${f} is empty`);
  return b;
}
async function alphaArea(f: string): Promise<number> {
  const p = await raw(f, 4);
  let n = 0;
  for (let i = 0; i < W * H; i++) n += p[i * 4 + 3]! / 255;
  return Math.round(n);
}
async function region(pairs: { layer: string; shadow: string }[]): Promise<Px> {
  const b = empty();
  for (const { layer, shadow } of pairs) {
    const p = await raw(layer, 4);
    const s = await raw(shadow, 1);
    for (let i = 0; i < W * H; i++) if (p[i * 4 + 3]! > 0 || s[i]! < 255) grow(b, i % W, (i / W) | 0);
  }
  return padRect(b);
}
async function lightRegion(f: string): Promise<Px> {
  const L = await raw(f, 3);
  const b = empty();
  for (let i = 0; i < W * H; i++) if (L[i * 3]! || L[i * 3 + 1]! || L[i * 3 + 2]!) grow(b, i % W, (i / W) | 0);
  if (b.x1 < 0) fail(`${f} adds no light`);
  return padRect(b);
}

/** MOCK8: a glow's region: where it adds (screen), or where it darkens (multiply: B1's glass) */
async function glowRegion(f: string, mul: boolean): Promise<Px> {
  const L = await raw(f, 3);
  const b = empty();
  for (let i = 0; i < W * H; i++) {
    const on = mul ? L[i * 3]! < 255 || L[i * 3 + 1]! < 255 || L[i * 3 + 2]! < 255 : L[i * 3]! || L[i * 3 + 1]! || L[i * 3 + 2]!;
    if (on) grow(b, i % W, (i / W) | 0);
  }
  if (b.x1 < 0) fail(`${f} does nothing`);
  return padRect(b);
}

// ---------- the plan: each product's depth along the camera's axis (the mask's code, the reveal's plane) ----------
type Camera = { id?: string; loc: [number, number, number]; yaw_deg_left: number; u0: number; v0: number };
type Shell = Record<string, unknown> & { cameras?: Record<string, unknown> };
type Plan = {
  cameras: (Camera & { id: string })[];
  rooms: { id: string; x: [number, number]; y: [number, number]; h: number }[];
  style_shells_1_3_1?: Record<string, Record<string, Shell>>;
};
const plan = read<Plan>(repoPath(c.plan));
// MOCK5 (registration 1.3.9, ch. 6.1): a style's own camera first (its shell), then the shared list. MOCK6: the shell
// may be shared by two rooms (registration 1.3.9a: `kids` holds K-boy and K-girl)
const shellKey = c.shell ?? c.room_plan;
const shell = plan.style_shells_1_3_1?.[c.style]?.[shellKey];
const shellCam = shell?.cameras?.[c.camera] as Camera | undefined;
const mc = c.camera_from_manifest ? (m.camera ?? fail(`${c.manifest} has no camera`)) : null;
const cam: Camera = mc
  ? { id: c.camera, loc: mc.loc, yaw_deg_left: mc.yaw, u0: mc.u0, v0: mc.v0 }
  : shellCam && Array.isArray(shellCam.loc)
    ? shellCam
    : (plan.cameras.find((x) => x.id === c.camera) ?? fail(`no camera ${c.camera}`));
const camFrom = mc
  ? `${c.manifest} camera (${mc.lens ?? 24} mm, not in the house plan yet)`
  : shellCam && Array.isArray(shellCam.loc)
    ? `style_shells_1_3_1.${c.style}.${shellKey}.cameras.${c.camera}`
    : `cameras.${c.camera}`;
/** the lens's projection: the plan's 24 mm (16:9, 36 mm wide), scaled by the focal length */
const LENS = (mc?.lens ?? 24) / 24;
// MOCK6: the girl's room is the boy's shifted exactly in Y (the shell's girl_offset_y): her camera must be his plus the
// shift (checked), and the slots' plan places, which are the boy's, shift with it
let offY = 0;
if (c.offset) {
  const v = shell?.[c.offset.key];
  if (typeof v !== 'number') fail(`no number ${c.offset.key} in style_shells_1_3_1.${c.style}.${shellKey}`);
  const ref = shell?.cameras?.[c.offset.from_camera] as Camera | undefined;
  if (!ref || !Array.isArray(ref.loc)) fail(`no camera ${c.offset.from_camera} in style_shells_1_3_1.${c.style}.${shellKey}`);
  const d = [cam.loc[0] - ref!.loc[0], cam.loc[1] - ref!.loc[1], cam.loc[2] - ref!.loc[2]];
  if (Math.abs(d[0]!) > 1e-9 || Math.abs(d[1]! - (v as number)) > 1e-9 || Math.abs(d[2]!) > 1e-9 || cam.yaw_deg_left !== ref!.yaw_deg_left)
    fail(`camera ${c.camera} is not ${c.offset.from_camera} shifted ${String(v)} in Y`);
  offY = v as number;
}
const box = plan.rooms.find((r) => r.id === c.room_plan) ?? fail(`no room ${c.room_plan}`);
const yaw = (cam.yaw_deg_left * Math.PI) / 180;
const fwd: [number, number] = [-Math.sin(yaw), -Math.cos(yaw)];
const depthOf = (x: number, y: number) => +((x - cam.loc[0]) * fwd[0] + (y - cam.loc[1]) * fwd[1]).toFixed(3);
type SlotRow = { id: string; name_he: string; plan_m?: Record<string, unknown> };
type SlotsFile = { slots: SlotRow[]; by_style?: Record<string, { slots?: Record<string, { plan_m?: Record<string, unknown> } | null> }> };
const slotsFile = read<SlotsFile>(repoPath(c.slots_file));
const mid = (r: unknown): number | null => (Array.isArray(r) && typeof r[0] === 'number' ? ((r[0] as number) + (r[1] as number)) / 2 : null);
function planDepth(id: string): number | null {
  // the style's own place first (by_style), then the shared slot's
  const p = slotsFile.by_style?.[c.style]?.slots?.[id]?.plan_m ?? slotsFile.slots.find((s) => s.id === id)?.plan_m;
  if (!p) return null;
  const pts: [number, number][] = [];
  const center = p.center as number[] | undefined;
  if (center) pts.push([center[0]!, center[1]!]);
  for (const k of ['centers', 'plates'] as const) for (const q of (p[k] as number[][] | undefined) ?? []) pts.push([q[0]!, q[1]!]);
  const plate = p.plate as number[] | undefined;
  if (plate) pts.push([plate[0]!, plate[1]!]);
  if (p.gather) pts.push(p.gather as [number, number]);
  for (const s of (p.stacks_y as number[][] | undefined) ?? []) if (mid(p.x) !== null) pts.push([mid(p.x)!, (s[0]! + s[1]!) / 2]);
  if (!pts.length && mid(p.x) !== null && mid(p.y) !== null) pts.push([mid(p.x)!, mid(p.y)!]);
  if (!pts.length) return null;
  return depthOf(pts.reduce((a, q) => a + q[0], 0) / pts.length, pts.reduce((a, q) => a + q[1], 0) / pts.length + offY);
}

// ---------- the cards of the repo: a print's rights, and the key the owner's count counts a product by ----------
type Card = { id: string; notes?: unknown; supplier?: { product_url?: string; name?: string } };
const cardFiles = new Map<string, string>();
const walk = (d: string): void => {
  for (const e of readdirSync(d, { withFileTypes: true }))
    if (e.isDirectory()) walk(join(d, e.name));
    else if (e.name.endsWith('.json')) cardFiles.set(e.name.slice(0, -5), join(d, e.name));
};
walk(repoPath('data/products'));
const cardJson = (id: string): Card | null => (cardFiles.has(id) ? read<Card>(cardFiles.get(id)!) : null);
const mirrorOf = (card: Card | null): string | null => {
  const notes = Array.isArray(card?.notes) ? card!.notes.join(' ') : typeof card?.notes === 'string' ? card.notes : '';
  return /mirror_of:\s*([a-z0-9][a-z0-9-]*[a-z0-9])/.exec(notes)?.[1] ?? null;
};
/** a card's original: its `mirror_of`, followed to the end (registration 1.3.9: one card a slot, the same SKU) */
const rootOf = (id: string): string => {
  let cur = id;
  for (let n = 0; n < 5; n++) {
    const up = mirrorOf(cardJson(cur));
    if (!up || up === cur) break;
    cur = up;
  }
  return cur;
};
/** the owner's count: one product a listing (the bath's niche set and vanity pump are one SKU, one page); a hash of
 *  it, so no supplier's address reaches the page */
const countKey = (card: string | null): string | null => {
  if (!card) return null;
  const root = rootOf(card);
  const url = cardJson(root)?.supplier?.product_url;
  const key = url
    ? url
        .replace(/[?#].*$/, '')
        .replace(/\/+$/, '')
        .toLowerCase()
    : root;
  return createHash('sha256').update(key).digest('hex').slice(0, 12);
};
const deepFind = (x: unknown, key: string): unknown => {
  if (!x || typeof x !== 'object') return undefined;
  if (key in (x as Record<string, unknown>)) return (x as Record<string, unknown>)[key];
  for (const v of Object.values(x as Record<string, unknown>)) {
    const r = deepFind(v, key);
    if (r !== undefined) return r;
  }
  return undefined;
};
// the rights rule (MOCK4's 776445, MOCK5's every print): ×1 only unless the card says "confirmed"
const rights: { slot: string; card: string | null; usage_rights: string }[] = [];
for (const id of c.prints ?? []) {
  const s = c.slots[id] ?? fail(`print ${id} is not a slot of ${CFG}`);
  const card = s.card ? cardJson(s.card) : null;
  const r = card ? deepFind(card, 'usage_rights') : undefined;
  rights.push({ slot: id, card: s.card, usage_rights: typeof r === 'string' ? r : 'missing' });
}
const x1 = new Set([...rights.filter((r) => r.usage_rights !== 'confirmed').map((r) => r.slot), ...(c.avoid ? [c.avoid] : [])]);

// ---------- the shop's record of a card ----------
type Shop = {
  id: string;
  card_id?: string;
  name_he: string;
  name_provisional?: boolean;
  price_agorot: number | null;
  price_provisional: boolean;
  availability: { status: string };
  dimensions_cm?: { width: number | null; depth: number | null; height: number | null };
  variants: { id: string; label_he: string }[];
};
const shopFile = join(GENERATED, 'catalog.tour-rooms.full.json');
if (!existsSync(shopFile)) fail(`${shopFile} is missing: npm run tour builds it first`);
const shop = new Map(read<{ products: Shop[] }>(shopFile).products.map((p) => [p.card_id ?? p.id, p]));
/** the shop's name of a card, with the option the layer shows (its colour, its size) when the shop has that option */
function shopName(p: Shop, product: string, card: string): string {
  // a copy's layer is named after its original (registration 1.3.9: `mirror_of`)
  const root = rootOf(card);
  const pre = product.startsWith(`${card}-`) ? card : product.startsWith(`${root}-`) ? root : null;
  const suffix = pre ? product.slice(pre.length + 1) : '';
  // a frame's code in the shop's name (a slot's working name, "(B2)") is not a word for a visitor
  const name = p.name_he.replace(/\s*\((?:[A-Z]{1,2}\d+x?)\)/g, '');
  const base = name.split(/,| · /)[0]!.trim();
  if (!suffix) return name;
  // the shop's option whose every value is in the layer's own name (a partial match would name another size)
  let best: { v: Shop['variants'][number]; n: number } | null = null;
  for (const v of p.variants) {
    const parts = v.id.split(':')[1]?.split('+') ?? [];
    // a pack of one or two (`1pc`) is the shop's own axis, not something a layer's name says
    const need = parts.filter((x) => !/^\d+pcs?$/.test(x));
    if (need.length && need.every((x) => suffix.includes(x)) && (!best || need.length > best.n)) best = { v, n: need.length };
  }
  if (!best) return base;
  const values = best.v.label_he
    .split(', ')
    .map((kv) => kv.split(': ')[1] ?? kv)
    // a pack's size is not the product's name, and a supplier's word in Latin is not ours (ת12): neither is shown
    .filter((x) => !/^\d+ יחידות$|^יחידה אחת$/.test(x) && !/[A-Za-z]/.test(x));
  return values.length ? `${base}, ${values.join(', ')}` : base;
}

// ---------- widths, files ----------
const REL = `tour/${c.room}/${c.style}${c.media ? `/${c.media}` : ''}`;
// MOCK6: the tool's own test (tools/test/mock6-tour-room.test.ts) writes a fixture elsewhere, never into the site's media
const OUT = join(process.env.HD_TOUR_MEDIA ?? MEDIA_OUT, REL);
const GEN_OUT = process.env.HD_TOUR_GENERATED ?? GENERATED;
const WIDTHS = { lo: 1920, hi: W } as const;
const CARD = 360;
const tierRect = (r: Px, Wt: number): Px => {
  const Ht = Math.round((Wt * H) / W);
  return { x0: Math.round((r.x0 / W) * Wt), x1: Math.round((r.x1 / W) * Wt), y0: Math.round((r.y0 / H) * Ht), y1: Math.round((r.y1 / H) * Ht) };
};
const cut = (r: Px) => ({ left: r.x0, top: r.y0, width: r.x1 - r.x0, height: r.y1 - r.y0 });
/** a layer's rectangle at a width, as raw pixels: RGBA for a product, RGB for a shadow (grey) or a light */
async function piece(f: string, kind: 'product' | 'shadow' | 'light', r: Px, Wt: number): Promise<{ data: Buffer; w: number; h: number; ch: 3 | 4 }> {
  const t = tierRect(r, Wt);
  const size = { width: t.x1 - t.x0, height: t.y1 - t.y0 };
  let img = src(f);
  img = kind === 'product' ? img.ensureAlpha() : kind === 'shadow' ? img.removeAlpha().toColourspace('srgb') : img.removeAlpha();
  img = img.extract(cut(r));
  if (Wt !== W) img = img.resize(size);
  const { data, info } = await img.raw().toBuffer({ resolveWithObject: true });
  if (info.width !== size.width || info.height !== size.height) fail(`${f}: ${info.width}×${info.height} at ${Wt}, not ${size.width}×${size.height}`);
  return { data, w: info.width, h: info.height, ch: info.channels as 3 | 4 };
}
/** shelf packing in pages of at most `max` × `max`, 2 px apart; returns where each piece goes */
function pack(sizes: { w: number; h: number }[], max: number): { page: number; x: number; y: number }[] {
  const ord = sizes.map((s, i) => ({ ...s, i })).sort((a, b) => b.h - a.h || b.w - a.w);
  const at: { page: number; x: number; y: number }[] = [];
  let page = 0;
  let x = 0;
  let y = 0;
  let row = 0;
  for (const s of ord) {
    if (s.w > max || s.h > max) fail(`a piece of ${s.w}×${s.h} does not fit a page of ${max}`);
    if (x + s.w > max) {
      x = 0;
      y += row + 2;
      row = 0;
    }
    if (y + s.h > max) {
      page++;
      x = 0;
      y = 0;
      row = 0;
    }
    at[s.i] = { page, x, y };
    x += s.w + 2;
    row = Math.max(row, s.h);
  }
  return at;
}
async function sheet(
  pcs: { data: Buffer; w: number; h: number; ch: 3 | 4 }[],
  at: { page: number; x: number; y: number }[],
  page: number,
  ch: 3 | 4,
): Promise<sharp.Sharp> {
  const mine = pcs.map((p, i) => ({ p, a: at[i]! })).filter((x) => x.a.page === page);
  const w = Math.max(...mine.map((x) => x.a.x + x.p.w));
  const h = Math.max(...mine.map((x) => x.a.y + x.p.h));
  const overlays: OverlayOptions[] = mine.map(({ p, a }) => ({ input: p.data, raw: { width: p.w, height: p.h, channels: p.ch }, left: a.x, top: a.y }));
  const bg = ch === 4 ? { r: 0, g: 0, b: 0, alpha: 0 } : { r: 255, g: 255, b: 255 };
  const img = sharp({ create: { width: w, height: h, channels: ch, background: bg } }).composite(overlays);
  // a composite comes out with an alpha channel whatever went in: read it as it is, and drop it from a page of shadows
  const { data, info } = await img.raw().toBuffer({ resolveWithObject: true });
  const out = sharp(data, { raw: { width: info.width, height: info.height, channels: info.channels } });
  return ch === 3 ? out.removeAlpha() : out;
}

/** MOCK12: a sheet's file name, page `n` (from 1): `cards`, `cards-2`, … (the first keeps MOCK4's name) */
const pageName = (kind: 'cards' | 'studio', n: number) => (n === 1 ? kind : `${kind}-${n}`);

/**
 * MOCK12 (FB29): how much of a product's rim the room cuts, as shares of its rim (alpha ≥ 0.5, 4-connected):
 *  - `occluded`: where the rim meets a layer drawn above it (within 2 px): a sofa's arm over the throw, a cushion on the
 *    bedding. The layers are cut from one hero render, so a rim that meets an upper layer is that layer's outline;
 *  - `frame`: where the rim runs straight along the frame's lines (the hero covers the frame: a product it ended stops
 *    there) or the canvas's edge. A cord that leaves the frame is a few pixels of it.
 * Over `CUT`, the card is not shown outside the room (FB29: "משהו מסתיר אותו, אז הוא חתוך"): the page names the product.
 */
const CUT = { occluded: 0.03, frame: 0.015 } as const;
function rimCut(p: Buffer, top: Int16Array, k: number, fbx: [number, number, number, number]): { occluded: number; frame: number } {
  const on = (x: number, y: number) => x >= 0 && y >= 0 && x < W && y < H && p[(y * W + x) * 4 + 3]! >= 128;
  let x0 = W;
  let y0 = H;
  let x1 = -1;
  let y1 = -1;
  for (let i = 0; i < W * H; i++)
    if (p[i * 4 + 3]! >= 128) {
      const x = i % W;
      const y = (i / W) | 0;
      if (x < x0) x0 = x;
      if (x > x1) x1 = x;
      if (y < y0) y0 = y;
      if (y > y1) y1 = y;
    }
  if (x1 < 0) return { occluded: 0, frame: 0 };
  let rim = 0;
  let occ = 0;
  for (let y = y0; y <= y1; y++)
    for (let x = x0; x <= x1; x++) {
      if (!on(x, y) || (on(x - 1, y) && on(x + 1, y) && on(x, y - 1) && on(x, y + 1))) continue;
      rim++;
      let hit = false;
      for (let dy = -2; dy <= 2 && !hit; dy++)
        for (let dx = -2; dx <= 2; dx++) {
          const X = x + dx;
          const Y = y + dy;
          if (X < 0 || Y < 0 || X >= W || Y >= H || on(X, Y)) continue;
          if (top[Y * W + X]! > k) {
            hit = true;
            break;
          }
        }
      if (hit) occ++;
    }
  const X0 = Math.round(fbx[0]);
  const Y0 = Math.round(fbx[1]);
  const X1 = Math.round(fbx[2]) - 1;
  const Y1 = Math.round(fbx[3]) - 1;
  let cut = 0;
  for (let x = Math.max(x0, X0); x <= Math.min(x1, X1); x++)
    for (const [Y, d] of [
      [Y1, 1],
      [Y0, -1],
    ] as const)
      for (let r = Y - 2; r <= Y + 2; r++)
        if (on(x, r) && !on(x, r + d)) {
          cut++;
          break;
        }
  for (let y = Math.max(y0, Y0); y <= Math.min(y1, Y1); y++)
    for (const [X, d] of [
      [X1, 1],
      [X0, -1],
    ] as const)
      for (let r = X - 2; r <= X + 2; r++)
        if (on(r, y) && !on(r + d, y)) {
          cut++;
          break;
        }
  for (let x = x0; x <= x1; x++) cut += (on(x, 0) ? 1 : 0) + (on(x, H - 1) ? 1 : 0);
  for (let y = y0; y <= y1; y++) cut += (on(0, y) ? 1 : 0) + (on(W - 1, y) ? 1 : 0);
  return { occluded: rim ? +(occ / rim).toFixed(4) : 0, frame: rim ? +(cut / rim).toFixed(4) : 0 };
}

/**
 * MOCK12 (FB29: "עם פדר, חיתוך פדר מסביב"): a card's rim without the room it was cut from. The layer's matte fades over
 * about 4 px of the room's own pixels; here it becomes a one-pixel anti-aliased edge (alpha 0.35 → 0, 0.75 → 1, smooth
 * between), and every pixel of the edge takes its colour from the product's solid pixels nearest it (within 3 px), not
 * from the wall behind it. Nothing is eroded, so a cord or a branch keeps its core.
 */
function hardenRim(px: Buffer, w: number, h: number): Buffer {
  const out = Buffer.from(px);
  for (let i = 0; i < w * h; i++) {
    const a = px[i * 4 + 3]! / 255;
    const t = Math.min(1, Math.max(0, (a - 0.35) / 0.4));
    const s = t * t * (3 - 2 * t);
    out[i * 4 + 3] = Math.round(s * 255);
    if (a >= 0.98 || s === 0) continue;
    const x = i % w;
    const y = (i / w) | 0;
    let r = 0;
    let g = 0;
    let b = 0;
    let n = 0;
    for (let rad = 1; rad <= 3 && !n; rad++)
      for (let dy = -rad; dy <= rad; dy++)
        for (let dx = -rad; dx <= rad; dx++) {
          const X = x + dx;
          const Y = y + dy;
          if (X < 0 || Y < 0 || X >= w || Y >= h) continue;
          const j = Y * w + X;
          if (px[j * 4 + 3]! < 250) continue;
          r += px[j * 4]!;
          g += px[j * 4 + 1]!;
          b += px[j * 4 + 2]!;
          n++;
        }
    if (n) {
      out[i * 4] = Math.round(r / n);
      out[i * 4 + 1] = Math.round(g / n);
      out[i * 4 + 2] = Math.round(b / n);
    }
  }
  return out;
}

// ---------- MOCK8 (FB20), MOCK12 (FB29): the studio pictures (assets/renders/wheel-studio/<style>/), of every product ----------
type StudioRow = { variant: string; room: string; slot: string; webp: string; products: { card_id: string; sku: string | null }[] };
// the tool's own test names a studio of its own (tools/test/mock12-wheels.test.ts), never the render folder's
const STUDIO_MANIFEST = process.env.HD_WHEEL_STUDIO ?? repoPath(`assets/renders/wheel-studio/${c.style}`, 'manifest.json');
const studioRows = existsSync(STUDIO_MANIFEST) ? read<{ variants: StudioRow[] }>(STUDIO_MANIFEST).variants : [];
const studioFile = (r: StudioRow) => (isAbsolute(r.webp) ? r.webp : repoPath(r.webp));
/** MOCK12: every picture a product of this frame is shown by outside the room (the strip, the wheel, the card): one for
 *  a product that does not change, one an option for a wheel */
type Shown = { key: string; slot: string; n: number; product: string; layer: string; card: string | null };
const shownList: Shown[] = order
  .filter((id) => !c.slots[id]!.fixed)
  .flatMap((id): Shown[] =>
    isWheel(id)
      ? wheelOpts.get(id)!.map((o, i) => ({ key: `${id}:${i + 1}`, slot: id, n: i + 1, product: o.product, layer: o.layer, card: o.card }))
      : [{ key: `${id}:1`, slot: id, n: 1, product: slotPiece.get(id)!.product, layer: slotPiece.get(id)!.layer, card: c.slots[id]!.card }],
  );
/** a product's studio picture: its own room's and slot's still first, then the same product's still from another room
 *  (the bedroom's throw is the living room's Pecan); never a still of another colour of the card */
const studioFor = (s: Shown): StudioRow | null => {
  const ms = c.slots[s.slot]!.of ?? s.slot;
  return studioRows.find((r) => r.room === GROUP && r.slot === ms && r.variant === s.product) ?? studioRows.find((r) => r.variant === s.product) ?? null;
};
const studioOf = new Map(shownList.map((s) => [s.key, studioFor(s)]));
for (const r of studioOf.values()) if (r && !existsSync(studioFile(r))) fail(`the studio picture ${r.webp} is missing`);
const STUDIO = 512;

// ---------- build (cached by a stamp of the inputs and this file) ----------
const lightSources = (Array.isArray(m.light) ? m.light : [m.light]).filter(inFrame).map((x) => lightFile(x.file));
const sources = [
  ...new Set([
    PLATE,
    c.truth,
    ...layers.flatMap((l) => [l.layer, l.shadow]),
    ...[...wheelOpts.values()].flat().flatMap((o) => [o.layer, o.shadow]),
    ...lightSources,
    ...glowEntries.map((g) => g.file),
    c.manifest,
    ...(c.wheel_manifest ? [c.wheel_manifest] : []),
  ]),
];
// ---------- MOCK7: the pin (content hashes of every file read for this frame) ----------
if (c.pin) {
  const files = Object.fromEntries(
    [...sources, ...(c.depth ? [relative(dir, repoPath(c.depth.file))] : [])].map((f) => [
      relative(REPO, join(dir, f)),
      createHash('sha256')
        .update(readFileSync(join(dir, f)))
        .digest('hex'),
    ]),
  );
  if (process.argv.includes('--write-pin')) {
    const note =
      "MOCK7 (2026-11-26): the living room, M0-W (the coordinator's update to briefs/site-mock7-tour-transitions-2026-11-26.md): every file tools/make-tour-room.ts reads for it, by content (sha256: the folder is not in git yet, so a changed file stops the build instead of being read from git's copy). The phase 2 room's pin (git blobs, manifest-basket.json) is tools/tour/living-room-phase2.pin.json. `npx --no-install tsx tools/make-tour-room.ts tools/tour/living-room-m0w.warm-modern.json --write-pin` writes this again.";
    writeFileSync(sitePath(c.pin), JSON.stringify({ note, manifest: relative(REPO, join(dir, c.manifest)), hash: 'sha256', files }, null, 2) + '\n');
    console.log(`make-tour-room: pinned ${Object.keys(files).length} files → ${c.pin}`);
  } else {
    const pin = read<{ files: Record<string, string> }>(sitePath(c.pin));
    const off = Object.keys({ ...files, ...pin.files }).filter((f) => files[f] !== pin.files[f]);
    if (off.length) fail(`not the pinned files (${c.pin}): ${off.slice(0, 4).join(', ')}${off.length > 4 ? ` and ${off.length - 4} more` : ''}`);
  }
}
const stamp = createHash('sha256')
  .update(
    JSON.stringify({
      c,
      tool: readFileSync(new URL(import.meta.url), 'utf8'),
      sources: sources.map((f) => [f, statSync(join(dir, f)).size, statSync(join(dir, f)).mtimeMs]),
      studio: [...studioOf.entries()].map(([k, r]) => (r ? [k, r.webp, statSync(studioFile(r)).size] : null)),
    }),
  )
  .digest('hex')
  .slice(0, 16);
const STAMP = join(OUT, 'stamp.json');
type AtlasRef = [number, number, number, number, number];
type Sprite = [number, number, number, number];
/** MOCK12: a picture's place on a sheet of pictures: [page (from 1), x, y, w, h] */
type SheetRef = [number, number, number, number, number];
type Built = {
  rects: Record<string, Px>;
  alpha: Record<string, Px>;
  area: Record<string, number>;
  lights: Px[];
  atlas: Record<
    number,
    {
      product: AtlasRef[];
      shadow: AtlasRef[];
      light: AtlasRef[];
      /** MOCK8: the glows (FB16), on lossy pages after the lights' */
      glow: AtlasRef[];
      pages: { product: [number, number][]; shadow: [number, number][] };
      /** MOCK6: a wheel's options (two or three) on the frame's own atlas pages, a place each ([page, x, y, w, h]);
       *  MOCK12: by wheel. A wheel of many options has none here: a patch file each */
      wheels: Record<string, { product: AtlasRef[]; shadow: AtlasRef[] }>;
    }
  >;
  /** the cards (the product's layer trimmed to it, its rim hardened: MOCK12), by `<slot>:<n>`, on sheets of 2048 */
  cards: { at: Record<string, SheetRef>; sheets: [number, number][] };
  /** MOCK12 (FB29): a card the room cuts (an occluder over it, or the frame's edge): the page shows its name instead */
  cut: Record<string, 'occluded' | 'frame'>;
  /** MOCK12: how much of the card's rim is cut, for the record (occluded, frame), by `<slot>:<n>` */
  cutPct: Record<string, [number, number]>;
  shadowOf: Record<string, number[]>;
  /** MOCK8: the glows' regions, and the studio pictures' places on their sheets (by `<slot>:<n>`) */
  glows: Px[];
  studio: { at: Record<string, SheetRef>; sheets: [number, number][] };
};
let built: Built;
const others = order.filter((id) => !isWheel(id));
const cached = existsSync(STAMP) ? read<{ stamp: string; built: Built }>(STAMP) : null;
if (cached?.stamp === stamp && cached.built.cut && cached.built.atlas[WIDTHS.lo]?.wheels) built = cached.built;
else {
  rmSync(OUT, { recursive: true, force: true });
  mkdirSync(OUT, { recursive: true });
  const rects: Record<string, Px> = {};
  const alpha: Record<string, Px> = {};
  const area: Record<string, number> = {};
  for (const id of others) {
    const p = slotPiece.get(id)!;
    rects[id] = await region([p]);
    alpha[`${id}:1`] = await alphaBox(p.layer);
    area[id] = await alphaArea(p.layer);
  }
  for (const [id, opts] of wheelOpts) {
    rects[id] = await region(opts);
    for (const [n, o] of opts.entries()) alpha[`${id}:${n + 1}`] = await alphaBox(o.layer);
    area[id] = await alphaArea(opts[0]!.layer);
  }
  const lightRects = await Promise.all(lights.map(lightRegion));
  const glowRects = await Promise.all(glowEntries.map((g) => glowRegion(g.file, g.mul)));
  // a wheel's shadows: one file for options that share it to the byte (the throw's three, the linen towel's two)
  const shadowOf: Record<string, number[]> = {};
  for (const [id, opts] of wheelOpts) {
    const shaOf = opts.map((o) => sha(join(dir, o.shadow)));
    shadowOf[id] = opts.map((_, n) => shaOf.indexOf(shaOf[n]!) + 1);
  }
  /** the wheel's options that have a shadow of their own (the others share one to the byte) */
  const own = (id: string) => wheelOpts.get(id)!.flatMap((_, n) => (shadowOf[id]![n] === n + 1 ? [n] : []));
  const onAtlas = WHEELS.filter((id) => !many(id));
  const atlas: Built['atlas'] = {};
  for (const Wt of new Set(Object.values(WIDTHS))) {
    // every other product and its shadow, and the light, in pages no wider than the composition (the engine already
    // needs a texture that wide, so every card that runs the tour holds one). MOCK6: and the wheels' options after them
    // (two or three a wheel), an option that shares its shadow sharing its place
    const sp: Awaited<ReturnType<typeof piece>>[] = [];
    const ss: Awaited<ReturnType<typeof piece>>[] = [];
    const spAt: Record<string, number[]> = {};
    const ssAt: Record<string, number[]> = {};
    for (const id of onAtlas) {
      const opts = wheelOpts.get(id)!;
      spAt[id] = [];
      for (const o of opts) {
        spAt[id].push(sp.length);
        sp.push(await piece(o.layer, 'product', rects[id]!, Wt));
      }
      ssAt[id] = [];
      for (const n of own(id)) {
        ssAt[id].push(ss.length);
        ss.push(await piece(opts[n]!.shadow, 'shadow', rects[id]!, Wt));
      }
    }
    const prods = [...(await Promise.all(others.map((id) => piece(slotPiece.get(id)!.layer, 'product', rects[id]!, Wt)))), ...sp];
    const lossyLights = c.light_pages === 'lossy';
    const lps = await Promise.all(lights.map((f, i) => piece(f, 'light', lightRects[i]!, Wt)));
    const shads = [...(await Promise.all(others.map((id) => piece(slotPiece.get(id)!.shadow, 'shadow', rects[id]!, Wt)))), ...(lossyLights ? [] : lps), ...ss];
    const pa = pack(prods, Wt);
    const sa = pack(shads, Wt);
    const la = lossyLights ? pack(lps, Wt) : [];
    const pages = { product: [] as [number, number][], shadow: [] as [number, number][] };
    for (let pg = 0; pg <= Math.max(...pa.map((a) => a.page)); pg++) {
      const s = await sheet(prods, pa, pg, 4);
      const meta = await s.metadata();
      pages.product.push([meta.width!, meta.height!]);
      await s.webp({ nearLossless: true, quality: 60, effort: 5 }).toFile(join(OUT, `atlas.product.${pg + 1}.${Wt}.webp`));
    }
    for (let pg = 0; pg <= Math.max(...sa.map((a) => a.page)); pg++) {
      const s = await sheet(shads, sa, pg, 3);
      const meta = await s.metadata();
      pages.shadow.push([meta.width!, meta.height!]);
      await s.webp({ lossless: true, effort: 5 }).toFile(join(OUT, `atlas.shadow.${pg + 1}.${Wt}.webp`));
    }
    // MOCK7: the lights' own pages after the shadows' (lossy: a light is a smooth glow, added in screen)
    const nS = pages.shadow.length;
    for (let pg = 0; lossyLights && pg <= Math.max(...la.map((a) => a.page)); pg++) {
      const s = await sheet(lps, la, pg, 3);
      const meta = await s.metadata();
      pages.shadow.push([meta.width!, meta.height!]);
      await s.webp({ quality: 86, effort: 5 }).toFile(join(OUT, `atlas.shadow.${nS + pg + 1}.${Wt}.webp`));
    }
    // MOCK8: the glows (FB16) on lossy pages of their own after those (smooth light, drawn over the graded frame)
    const gps = await Promise.all(glowEntries.map((g, i) => piece(g.file, 'light', glowRects[i]!, Wt)));
    const ga = gps.length ? pack(gps, Wt) : [];
    const nG = pages.shadow.length;
    for (let pg = 0; gps.length && pg <= Math.max(...ga.map((a) => a.page)); pg++) {
      const s = await sheet(gps, ga, pg, 3);
      const meta = await s.metadata();
      pages.shadow.push([meta.width!, meta.height!]);
      await s.webp({ quality: 86, effort: 5 }).toFile(join(OUT, `atlas.shadow.${nG + pg + 1}.${Wt}.webp`));
    }
    const ref = (at: { page: number; x: number; y: number }[], pcs: { w: number; h: number }[], k: number): AtlasRef => [
      at[k]!.page + 1,
      at[k]!.x,
      at[k]!.y,
      pcs[k]!.w,
      pcs[k]!.h,
    ];
    const sBase = others.length + (lossyLights ? 0 : lights.length);
    atlas[Wt] = {
      product: others.map((_, i) => ref(pa, prods, i)),
      shadow: others.map((_, i) => ref(sa, shads, i)),
      light: lights.map((_, i) => {
        if (!lossyLights) return ref(sa, shads, others.length + i);
        const r = ref(la, lps, i);
        return [r[0] + nS, r[1], r[2], r[3], r[4]] as AtlasRef;
      }),
      glow: gps.map((_, i) => {
        const r = ref(ga, gps, i);
        return [r[0] + nG, r[1], r[2], r[3], r[4]] as AtlasRef;
      }),
      pages,
      // the wheels' options (the wheel swaps them by their place on the page). MOCK4 wrote a file each, MOCK5 two pages
      // of their own; MOCK6 the frame's pages, so a frame with a wheel is two files fewer (the Artifact's file limit)
      wheels: Object.fromEntries(
        onAtlas.map((id) => [
          id,
          {
            product: spAt[id]!.map((k) => ref(pa, prods, others.length + k)),
            shadow: shadowOf[id]!.map((s) => ref(sa, shads, sBase + ssAt[id]![own(id).indexOf(s - 1)]!)),
          },
        ]),
      ),
    };
    // MOCK6: a wheel of many options (the kids' art sets to come): a patch each, its product and its shadow a file of
    // their own, which the page loads only when that option is chosen (never in the background, never all ten)
    for (const id of WHEELS.filter(many)) {
      const r = rects[id]!;
      mkdirSync(join(OUT, 'slots', id), { recursive: true });
      for (const [n, o] of wheelOpts.get(id)!.entries()) {
        const pp = await piece(o.layer, 'product', r, Wt);
        await sharp(pp.data, { raw: { width: pp.w, height: pp.h, channels: pp.ch } })
          .webp({ nearLossless: true, quality: 60, effort: 5 })
          .toFile(join(OUT, 'slots', id, `${n + 1}.product.${Wt}.webp`));
        if (shadowOf[id]![n] !== n + 1) continue;
        const sh = await piece(o.shadow, 'shadow', r, Wt);
        await sharp(sh.data, { raw: { width: sh.w, height: sh.h, channels: sh.ch } })
          .removeAlpha()
          .webp({ lossless: true, effort: 5 })
          .toFile(join(OUT, 'slots', id, `${n + 1}.shadow.${Wt}.webp`));
      }
    }
  }
  // the base: the plate, byte for byte (the folder's own), at both widths
  for (const Wt of new Set(Object.values(WIDTHS))) {
    const b = sharp(join(dir, PLATE)).removeAlpha();
    // the house's own base setting (tools/make-house.ts BASE_WEBP_Q: lossy q90 shows on plaster at 1:1)
    await (Wt === W ? b : b.resize({ width: Wt })).webp({ quality: 95, effort: 5 }).toFile(join(OUT, `base.${Wt}.webp`));
  }
  // MOCK12 (FB29): what the room cuts. Every default layer above a product (its draw order) is an occluder: where a
  // product's rim meets one, the product is hidden there; where its rim runs along the frame's lines, the hero ended it
  const top = new Int16Array(W * H).fill(-1);
  for (const [k, l] of layers.entries()) {
    const p = await raw(l.layer, 4);
    for (let i = 0; i < W * H; i++) if (p[i * 4 + 3]! >= 128) top[i] = k;
  }
  const lastIndex = (id: string) => Math.max(...pieces.get(id)!.map((p) => layers.indexOf(p)));
  const cut: Built['cut'] = {};
  const cutPct: Built['cutPct'] = {};
  for (const s of shownList) {
    const r = rimCut(await raw(s.layer, 4), top, lastIndex(s.slot), m.frame_box);
    cutPct[s.key] = [r.occluded, r.frame];
    if (r.occluded > CUT.occluded) cut[s.key] = 'occluded';
    else if (r.frame > CUT.frame) cut[s.key] = 'frame';
  }
  // the cards: every product on its own (its layer trimmed to it, FB1; MOCK12: its rim hardened and its edge's colour
  // taken from inside it, so no room is left round it), on sheets of 2048
  const cardPieces: { data: Buffer; w: number; h: number; ch: 4 }[] = [];
  for (const s of shownList) {
    const a = await alphaBox(s.layer);
    const pad = Math.round(Math.max(a.x1 - a.x0, a.y1 - a.y0) * 0.03) + 2;
    const left = Math.max(0, a.x0 - pad);
    const top0 = Math.max(0, a.y0 - pad);
    const bx = { left, top: top0, width: Math.min(W, a.x1 + 1 + pad) - left, height: Math.min(H, a.y1 + 1 + pad) - top0 };
    const k = Math.min(1, CARD / Math.max(bx.width, bx.height));
    const px = await src(s.layer).ensureAlpha().extract(bx).raw().toBuffer();
    const { data, info } = await sharp(hardenRim(px, bx.width, bx.height), { raw: { width: bx.width, height: bx.height, channels: 4 } })
      .resize({ width: Math.max(1, Math.round(bx.width * k)), height: Math.max(1, Math.round(bx.height * k)) })
      .raw()
      .toBuffer({ resolveWithObject: true });
    cardPieces.push({ data, w: info.width, h: info.height, ch: 4 });
  }
  const ca = pack(cardPieces, 2048);
  const cardSheets: [number, number][] = [];
  for (let pg = 0; pg <= Math.max(-1, ...ca.map((a) => a.page)); pg++) {
    const cs = await sheet(cardPieces, ca, pg, 4);
    const meta = await cs.metadata();
    cardSheets.push([meta.width!, meta.height!]);
    await cs.webp({ quality: 88, alphaQuality: 100, effort: 5 }).toFile(join(OUT, `${pageName('cards', pg + 1)}.${CARD}.webp`));
  }
  // MOCK8 (FB20), MOCK12: the studio pictures, every product's that has one, on sheets of 2048 (the Artifact's file limit)
  const have = shownList.filter((s) => studioOf.get(s.key));
  const spcs = await Promise.all(
    have.map(async (s) => {
      const { data, info } = await sharp(studioFile(studioOf.get(s.key)!))
        .removeAlpha()
        .resize({ width: STUDIO, height: STUDIO, fit: 'cover' })
        .raw()
        .toBuffer({ resolveWithObject: true });
      return { data, w: info.width, h: info.height, ch: 3 as const };
    }),
  );
  const sat = pack(spcs, 2048);
  const studioSheets: [number, number][] = [];
  for (let pg = 0; pg <= Math.max(-1, ...sat.map((a) => a.page)); pg++) {
    const ss = await sheet(spcs, sat, pg, 3);
    const meta = await ss.metadata();
    studioSheets.push([meta.width!, meta.height!]);
    await ss.webp({ quality: 88, effort: 5 }).toFile(join(OUT, `${pageName('studio', pg + 1)}.${STUDIO}.webp`));
  }
  built = {
    glows: glowRects,
    studio: {
      at: Object.fromEntries(have.map((s, i) => [s.key, [sat[i]!.page + 1, sat[i]!.x, sat[i]!.y, spcs[i]!.w, spcs[i]!.h] as SheetRef])),
      sheets: studioSheets,
    },
    rects,
    alpha,
    area,
    lights: lightRects,
    atlas,
    cards: {
      at: Object.fromEntries(shownList.map((s, i) => [s.key, [ca[i]!.page + 1, ca[i]!.x, ca[i]!.y, cardPieces[i]!.w, cardPieces[i]!.h] as SheetRef])),
      sheets: cardSheets,
    },
    cut,
    cutPct,
    shadowOf,
  };
  writeFileSync(STAMP, JSON.stringify({ stamp, built }));
}

// ---------- the data ----------
const uv = (r: Px): Box => [r.x0 / W, r.x1 / W, r.y0 / H, r.y1 / H];
const fb = m.frame_box;
const camera = {
  frame: [fb[0] / W, fb[2] / W, fb[1] / H, fb[3] / H].map((x) => +x.toFixed(5)) as Box,
  u0: cam.u0,
  v0: cam.v0,
  kx: +(0.6667 * LENS).toFixed(4),
  ky: +(1.1852 * LENS).toFixed(4),
  loc: cam.loc,
  yaw_deg_left: cam.yaw_deg_left,
  room: { x: box.x, y: box.y, h: box.h },
};
const dimsHe = (d: Shop['dimensions_cm'], kind: SlotCfg['kind']): string | null => {
  if (!d) return null;
  const a = d.width;
  const b = kind === 'floor' && d.depth && !d.height ? d.depth : d.height;
  return a && b ? `${a} × ${b} ס"מ` : null;
};
const placeholder = `data:image/webp;base64,${(await sharp(join(dir, PLATE)).removeAlpha().resize({ width: 48 }).webp({ quality: 60, effort: 6 }).toBuffer()).toString('base64')}`;
const slotName = (id: string) =>
  c.slots[id]!.name_he ?? slotsFile.slots.find((s) => s.id === (c.slots[id]!.of ?? id))?.name_he ?? fail(`no name for slot ${id}`);
// the mask's code is a product's depth × 40: two products a code apart are told apart (a nudge of 2.5 cm where they tie)
const codes = new Set<number>();
const depth = (id: string): number => {
  let d = planDepth(c.slots[id]!.of ?? id) ?? c.slots[id]!.depth_m ?? fail(`no depth for slot ${id}: give it depth_m`);
  while (codes.has(Math.round(d * 40))) d += 0.025;
  codes.add(Math.round(d * 40));
  return +d.toFixed(3);
};
/** a picture on a sheet of the frame (a card, a studio picture): its file, its place and the sheet's size */
const onSheet = (kind: 'cards' | 'studio', size: number, at: SheetRef, sheets: [number, number][]) => ({
  src: `${REL}/${pageName(kind, at[0])}.${size}`,
  w: at[3],
  h: at[4],
  sprite: [at[1], at[2], at[3], at[4]] as Sprite,
  sheet: sheets[at[0] - 1]!,
});
const option = (slot: string, n: number, product: string, card: string | null) => {
  const p = card ? shop.get(card) : undefined;
  // MOCK6, the safety rule: a product shown and not sold here (or waiting for its standard) has no price and no cart
  const held = !!c.slots[slot]!.sale;
  const key = `${slot}:${n}`;
  const a = built.alpha[key]!;
  const st = built.studio.at[key];
  return {
    position: n,
    card: { ...onSheet('cards', CARD, built.cards.at[key]!, built.cards.sheets), source: 'layer' as const },
    /** MOCK12: the option's product as the render folder names it (its layer's product; a set's `set-<key>`) */
    variant: product,
    // MOCK12 (FB29): the room cuts this card (an occluder, the frame's edge): outside the room it is never shown
    ...(built.cut[key] ? { cut: built.cut[key] } : {}),
    box: uv({ ...a, x1: a.x1 + 1, y1: a.y1 + 1 }),
    product_id: p?.id ?? null,
    card_id: card,
    name_he:
      c.option_names_he?.[product] ?? (p ? (c.names === 'slot-when-provisional' && p.name_provisional ? slotName(slot) : shopName(p, product, card!)) : null),
    price_agorot: held ? null : (p?.price_agorot ?? null),
    price_provisional: held ? false : (p?.price_provisional ?? false),
    available: !held && !!p && p.availability.status === 'available',
    dims_he: p ? dimsHe(p.dimensions_cm, c.slots[slot]!.kind) : null,
    set: false,
    // MOCK8 (FB20): the option's studio picture (the product as sold), on the room's studio sheets; MOCK12 (FB29): every
    // product's, not the wheel's only. A print whose rights are not confirmed keeps its close-up in the preview (PR1)
    ...(st ? { studio: { ...onSheet('studio', STUDIO, st, built.studio.sheets), source: 'studio' as const, ...(x1.has(slot) ? { preview_only: true } : {}) } } : {}),
  };
};
const at = (Wt: number) => built.atlas[Wt]!;
const slots = await Promise.all(
  order.map(async (id, i) => {
    const cfg = c.slots[id]!;
    const pc = slotPiece.get(id)!;
    const wheel = isWheel(id);
    const k = others.indexOf(id);
    const opts = wheel ? wheelOpts.get(id)!.map((o, n) => option(id, n + 1, o.product, o.card)) : cfg.fixed ? [] : [option(id, 1, pc.product, cfg.card)];
    const a0 = built.alpha[`${id}:1`]!;
    // one mark a layer where a product is drawn twice (MB1's two sconces), unless the config places them
    let anchors = cfg.anchors;
    const ps = pieces.get(id)!;
    if (!anchors && ps.length > 1) {
      anchors = [];
      for (const l of ps) {
        const b = await alphaBox(l.layer);
        anchors.push([+(((b.x0 + b.x1) / 2 - a0.x0) / (a0.x1 - a0.x0)).toFixed(3), +(((b.y0 + b.y1) / 2 - a0.y0) / (a0.y1 - a0.y0)).toFixed(3)]);
      }
    }
    return {
      id,
      name_he: slotName(id),
      z: zOf(id),
      rect: uv(built.rects[id]!),
      depth_m: depth(id),
      kind: cfg.kind,
      order_a: i + 1,
      hero: !!cfg.hero,
      ground: cfg.kind === 'floor' || cfg.kind === 'surface',
      anchors: (anchors ?? [[0.5, 0.5]]).map(([x, y]) => [+((a0.x0 + (a0.x1 - a0.x0) * x) / W).toFixed(4), +((a0.y0 + (a0.y1 - a0.y0) * y) / H).toFixed(4)]),
      src: `${REL}/slots/${id}`,
      fixed: !!cfg.fixed,
      // a print whose rights are not confirmed is shown at ×1 only (MOCK4 776445; MOCK5 every print)
      closeup: x1.has(id) ? false : (cfg.closeup ?? true),
      shadows: wheel ? built.shadowOf[id] : undefined,
      // the owner's count: the key a product is counted by in its room, and its area here (counted where it is biggest)
      count_key: cfg.fixed ? null : countKey(cfg.card),
      area_px: built.area[id] ?? 0,
      // the atlas: [page, x, y, w, h] of this product and of its shadow, per width
      atlas: wheel ? undefined : Object.fromEntries(Object.values(WIDTHS).map((Wt) => [Wt, { product: at(Wt).product[k]!, shadow: at(Wt).shadow[k]! }])),
      // MOCK5: the sample's options, a place each on the atlas pages (MOCK6: the frame's own), per width and option
      atlas_opts:
        wheel && !many(id)
          ? Object.fromEntries(
              Object.values(WIDTHS).map((Wt) => {
                const wa = at(Wt).wheels[id]!;
                return [Wt, wheelOpts.get(id)!.map((_, n) => ({ product: wa.product[n]!, shadow: wa.shadow[n]! }))];
              }),
            )
          : undefined,
      // MOCK6: a wheel of many options: a patch file each (src/<n>.product, src/<shadows[n]>.shadow), loaded only when
      // that option is chosen, never in the background
      lazy: wheel && many(id) ? true : undefined,
      // MOCK6, the safety rule: shown and not sold here, or waiting for its standard (the line the visitor reads, and why)
      sale: cfg.sale
        ? {
            state: cfg.sale,
            label_he: cfg.sale_he ?? fail(`slot ${id}: sale without sale_he`),
            why_he: cfg.sale_why_he ?? fail(`slot ${id}: sale without sale_why_he`),
          }
        : undefined,
      // a fixed piece of furniture is composed like any layer and has no option to show: one, with no card
      options: cfg.fixed
        ? [
            {
              position: 1,
              card: { src: `${REL}/${pageName('cards', 1)}.${CARD}`, w: 1, h: 1, source: 'layer' as const, sprite: [0, 0, 1, 1], sheet: built.cards.sheets[0]! },
              box: uv({ ...a0, x1: a0.x1 + 1, y1: a0.y1 + 1 }),
              product_id: null,
              card_id: null,
              name_he: null,
              price_agorot: null,
              price_provisional: false,
              available: false,
              dims_he: null,
              set: false,
            },
          ]
        : opts,
    };
  }),
);
const avoid = [...x1].map((id) => uv(built.alpha[`${id}:1`]!));
const data = {
  room: c.room,
  group: GROUP,
  frame: c.camera,
  frame_he: c.frame_he ?? null,
  style: c.style,
  name_he: 'מודרני חם',
  room_he: c.name_he,
  // B1's manifest has no id: its folder's name
  source: m.id ?? basename(dir),
  native: W,
  widths: { lo: Math.min(WIDTHS.lo, W), hi: W },
  card_width: CARD,
  aspect: W / H,
  mobile_center_u: 0.5,
  base: { src: `${REL}/base`, widths: [WIDTHS.lo, W], placeholder, formats: ['webp'] },
  camera,
  camera_from: camFrom,
  styles: c.styles === false ? false : undefined,
  // MOCK7: the frame's depth for the transitions (a small nearness map, near = white), or null: the page's fallback
  depth: c.depth ? (await nearness(c.depth)).uri : null,
  cover: 0,
  // MOCK12: the frame's wheels (a ring each); `sample` is the first, for what read one wheel a frame
  sample: WHEELS[0],
  wheels: WHEELS,
  // ×1 only: no zoom in a frame that shows a print whose rights are unclear
  zoom: x1.size ? false : c.zoom !== false,
  avoid,
  x1: [...x1],
  rights,
  atlas: Object.fromEntries(
    Object.values(WIDTHS).map((Wt) => [
      Wt,
      {
        product: at(Wt).pages.product.map(([w, h], i) => ({ src: `${REL}/atlas.product.${i + 1}`, w, h })),
        shadow: at(Wt).pages.shadow.map(([w, h], i) => ({ src: `${REL}/atlas.shadow.${i + 1}`, w, h })),
      },
    ]),
  ),
  lights: [
    ...lights.map((f, i) => ({
      id: basename(lightSources[i] ?? f, '.png'),
      slot: lightEntries[i]!.slot,
      rect: uv(built.lights[i]!),
      atlas: Object.fromEntries(Object.values(WIDTHS).map((Wt) => [Wt, at(Wt).light[i]!])),
    })),
    // MOCK8 (FB16): the glows, over the graded frame
    ...glowEntries.map((g, i) => ({
      id: basename(g.file, '.png'),
      slot: g.slot,
      rect: uv(built.glows[i]!),
      atlas: Object.fromEntries(Object.values(WIDTHS).map((Wt) => [Wt, at(Wt).glow[i]!])),
      post: true,
      ...(g.mul ? { mul: true } : {}),
      ...(g.pos ? { pos: g.pos } : {}),
    })),
  ],
  // MOCK8 (FB16): the house grade of this frame (Lab: the L curve's knots and slopes, the shift to warm), applied by the
  // engine on the composite, before the glows
  grade: grade ?? undefined,
  fb16: f16 ? FB16_FRAME : undefined,
  for_sale: slots.filter((s) => !s.fixed).length,
  slots,
};
// how much of the frame the products fill (the counter's line): their alpha boxes would overstate it, so it is left
// out here (0) and the page shows the count alone
mkdirSync(GEN_OUT, { recursive: true });
const outFile = join(GEN_OUT, `tour.${c.room}.${c.style}.json`);
writeFileSync(outFile, JSON.stringify(data));

const kb = (f: string) => statSync(join(OUT, f)).size / 1024;
const lo = WIDTHS.lo;
const loFiles = [
  `base.${lo}.webp`,
  ...data.atlas[lo]!.product.map((p) => `${basename(p.src)}.${lo}.webp`),
  ...data.atlas[lo]!.shadow.map((p) => `${basename(p.src)}.${lo}.webp`),
  // MOCK6: a wheel of many options loads its chosen option's patch only (the first, at rest)
  ...WHEELS.filter(many).flatMap((id) => [`slots/${id}/1.product.${lo}.webp`, `slots/${id}/1.shadow.${lo}.webp`]),
  // the strip's pictures: the cards and (MOCK12) the studio pictures, the door waits for them
  ...built.cards.sheets.map((_, i) => `${pageName('cards', i + 1)}.${CARD}.webp`),
  ...built.studio.sheets.map((_, i) => `${pageName('studio', i + 1)}.${STUDIO}.webp`),
];
const held = slots.filter((s) => s.sale).map((s) => `${s.id} (${s.sale!.state})`);
const unsold = slots.filter((s) => !s.fixed).flatMap((s) => s.options.filter((o) => !o.product_id).map((o) => `${s.id} ${o.position}`));
console.log(
  `tour ${c.room}/${c.style} (${GROUP} ${c.camera}, camera ${camFrom}, yaw ${cam.yaw_deg_left}): ${data.source}; ${slots.length} layers (${data.for_sale} for sale, ` +
    `${slots.length - data.for_sale} fixed), ${lights.length} light${MASK_LIGHT ? ' (masked by every alpha)' : ''}; the order gives ${gateNote || `${c.truth} to the pixel`}; ` +
    `×1 only: ${rights.length || x1.size ? [...x1].map((id) => `${id} (${rights.find((r) => r.slot === id)?.usage_rights ?? 'config'})`).join(', ') || 'none' : 'none'}; ` +
    `a phone's first load ${loFiles.reduce((n, f) => n + kb(f), 0).toFixed(0)} KB in ${loFiles.length} files ` +
    `(atlas pages ${data.atlas[lo]!.product.length}+${data.atlas[lo]!.shadow.length}); ${unsold.length} not priced by the shop yet (${unsold.join(', ')}); ` +
    `held for safety: ${held.join(', ') || 'none'}; wheels: ${WHEELS.map((id) => `${id} (${wheelOpts.get(id)!.length})`).join(', ') || 'none'}; ` +
    `outside the room (FB29): ${shownList.filter((s) => studioOf.get(s.key)).length} studio, ${shownList.filter((s) => !studioOf.get(s.key) && !built.cut[s.key]).length} cut clean, ` +
    `${shownList.filter((s) => !studioOf.get(s.key) && built.cut[s.key]).length} by name (cut by the room: ${shownList.filter((s) => built.cut[s.key]).map((s) => `${s.key} ${built.cut[s.key]}`).join(', ') || 'none'}) → ${outFile}`,
);
