/**
 * MOCK1 (2026-11-12): the wow-tour mock-up's room from the phase 2 tool layers of the warm-modern house
 * (tools/tour/<room>.<style>.json → the render folder's layers manifest). Behind HD_PUBLIC=0. Writes:
 *
 *   .generated/tour.<room>.<style>.json    the tour's room as its engine reads it (web/src/tour/): the base, every slot
 *                                          with its options (the default first, then the variants in the manifest's order;
 *                                          the cushions: the three sets), each option's layer and shadow, where its ring
 *                                          starts, its depth along the camera's axis, and the shop's record of its card
 *   web/public/media/tour/<room>/<style>/M0/  every layer cut to its slot's rectangle, at two widths (MOCK2): the layers'
 *                                          own width, where a desktop composes (QA finding 1 of 2026-11-10), and `lo` for
 *                                          a phone, which is what the room engine already does there (engine/engine.ts:
 *                                          a viewport ≤ 900 px composes at scene.widths.lo). The product is near-lossless
 *                                          WebP and the shadow lossless (the same settings as tools/make-house.ts, S12);
 *                                          and the wheel's card of every option: the product's own layer, trimmed to it
 *                                          and on nothing (MOCK2, FB1 — never a crop of the room). Where our own studio
 *                                          picture passed QA (tools/make-studio.ts) the card is that picture instead.
 *
 * The base is the house's own (tools/make-house.ts): the manifest's base.png is the pilot's, byte for byte (checked
 * here), so its encoded files are shared and nothing is encoded twice.
 *
 * A product's name and price are the shop's record of its card (.generated/catalog.story.full.json, the same pricing
 * path), when the shop has one. A card the shop does not sell yet has no public name and no price: it is shown under its
 * slot's name, "עוד לא במכירה" (no data is written here, and no card is read for a name).
 *
 * MOCK6 (2026-11-25): the living room is pinned to what MOCK5 used (`pin`: tools/tour/living-room.pin.json, the git blob
 * of every file read here), while render-agent makes the clean M0 plate in the same folder (FB12). A file whose blob
 * differs on disk is read from git's own copy of the pinned blob, so no new living-room file is picked up.
 *
 * MOCK7 (2026-11-26, briefs/site-mock7-tour-transitions-2026-11-26.md): the room's source is ONE line of its config,
 * `manifest` (the layers manifest's path from the repository's root; its folder is the layers' folder). Today it is
 * manifest-basket.json (Olia, the lfix fixes, the moved basket; the old walnut table is in none of its files). The base
 * is the manifest's own `base` layer (base-fb12s0.png, the plate without the old table): encoded here when it is not
 * the house's, so the house's old base never reaches the tour. The gate: the default composition of these files, in
 * the manifest's order and by its formula, is its own default frame (truths.default, the first cushion set), to the
 * channel value. The pin holds only for the manifest it was written for (a new `manifest` line reads the files as they
 * are, and says so). `depth` (by manifest) is the room's depth for the transitions (tools/lib/depth.ts).
 */
import sharp from 'sharp';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { dirname, extname, join, relative } from 'node:path';
import { GENERATED, MEDIA_OUT, REPO, repoPath, sitePath } from './lib/paths';
import { nearness, type DepthCfg } from './lib/depth';

type Box = [number, number, number, number];
type SlotCfg = {
  depth_m: number;
  kind: 'floor' | 'wall' | 'surface' | 'hang';
  anchors: [number, number][];
  order_a: number;
  dims?: boolean;
  hero?: boolean;
  /** MOCK7: the slot's name where the shop has none (the coffee table: a fixed product in data/slots) */
  name_he?: string;
};
type TourManifest = {
  room: string;
  style: string;
  /** MOCK7: the layers manifest, from the repository's root (one line: the room's source) */
  manifest: string;
  /** MOCK7: the room's depth for the transitions, by manifest */
  depth?: Record<string, DepthCfg>;
  house: string;
  plan: string;
  camera: string;
  room_plan: string;
  /** MOCK6: the git blobs this room is pinned to (tools/tour/living-room.pin.json) */
  pin?: string;
  slots: Record<string, SlotCfg>;
};
type Product = { card_id: string; sku?: string };
type Layer = { id: string; slot?: string; z: number; file?: string | null; product?: Product };
type Variant = { id: string; slot: string; variant: string; z: number; file: string; shadow: string; product: Product; truth: string };
type LayersManifest = {
  id: string;
  size: { width: number; height: number; camera_frame_px: Box };
  compose: { order: string[] };
  layers: Layer[];
  variants: Record<string, Variant[]>;
  slot_cushions: { order: string[]; sets: Record<string, { layer: string; shadow: string }> };
  truths: { default: Record<string, string> };
};

const MANIFEST = process.argv[2] ?? 'tools/tour/living-room.warm-modern.json';
const read = <T>(p: string): T => JSON.parse(readFileSync(p, 'utf8')) as T;
const fail = (msg: string): never => {
  console.error(`make-tour: ${msg}`);
  process.exit(1);
};
const t = read<TourManifest>(sitePath(MANIFEST));
const manifestPath = repoPath(t.manifest);
const dir = dirname(manifestPath);

// ---------- MOCK6: the pin (every file read below is the blob MOCK5 used) ----------
const pinFile = t.pin ? read<{ commit: string; manifest?: string; files: Record<string, string> }>(sitePath(t.pin)) : null;
// MOCK7: the pin holds for the manifest it was written for; another `manifest` line reads its files as they are
const pin = pinFile && pinFile.manifest === t.manifest ? pinFile : null;
if (pinFile && !pin) console.warn(`make-tour: ${t.pin} is for ${pinFile.manifest ?? 'manifest-r9.json'}, not ${t.manifest}: the files are read as they are`);
const pinnedFrom: string[] = [];
const checked = new Map<string, string>();
/** the file to read for `f`: itself when its git blob is the pinned one, else git's own copy of the pinned blob */
const touched = new Set<string>();
const at = (f: string): string => {
  touched.add(relative(REPO, f));
  if (!pin) return f;
  const hit = checked.get(f);
  if (hit) return hit;
  const rel = relative(REPO, f);
  const want = pin.files[rel] ?? fail(`${rel} is not in ${t.pin}: the living room reads only what MOCK5 read`);
  const blob = (b: Buffer) => createHash('sha1').update(`blob ${b.length}\0`).update(b).digest('hex');
  let use = f;
  if (!existsSync(f) || blob(readFileSync(f)) !== want) {
    use = join(GENERATED, 'pinned', `${want}${extname(f)}`);
    if (!existsSync(use)) {
      mkdirSync(dirname(use), { recursive: true });
      writeFileSync(use, execFileSync('git', ['cat-file', 'blob', want], { cwd: REPO, maxBuffer: 1 << 30 }));
    }
    pinnedFrom.push(rel);
  }
  checked.set(f, use);
  return use;
};
const lm = read<LayersManifest>(at(manifestPath));
const W = lm.size.width;
const H = lm.size.height;
const sha = (f: string) => createHash('sha256').update(readFileSync(f)).digest('hex');

// ---------- the house this tour stands in: its base, its sets' names ----------
const hm = read<{
  pilot: string;
  layers_dir: string;
  mobile_center_u: number;
  slot: { id: string; name_he?: string };
  sets: { id: string; label_he: string }[];
}>(sitePath(t.house));
const houseFile = join(GENERATED, `house.${t.room}.${t.style}.json`);
if (!existsSync(houseFile)) fail(`${houseFile} is missing: tools/make-house.ts runs first (npm run story)`);
const house = read<{ name_he: string; scene: { base: { src: string; widths: number[] }[]; aspect: number } }>(houseFile);
const pilotBase = at(join(repoPath(hm.pilot), hm.layers_dir, 'base.png'));
// MOCK7: the manifest's own base layer; the house's encoded base is shared only when it is that very file
const baseLayer = lm.layers.find((l) => l.id === 'base') ?? fail(`no base layer in ${t.manifest}`);
const baseFile = at(join(dir, baseLayer.file ?? 'base.png'));
const ownBase = sha(baseFile) !== sha(pilotBase);

// ---------- the shop's records, by card ----------
type Shop = {
  id: string;
  card_id?: string;
  name_he: string;
  price_agorot: number | null;
  price_provisional: boolean;
  availability: { status: string };
  dimensions_cm?: { width: number | null; depth: number | null; height: number | null };
};
const shop = new Map(read<{ products: Shop[] }>(join(GENERATED, 'catalog.story.full.json')).products.map((p) => [p.card_id ?? p.id, p]));
const slotNames = new Map(
  read<{ rooms: { id: string; slots: { id: string; name_he: string }[] }[] }>(join(GENERATED, 'catalog.public.json'))
    .rooms.find((r) => r.id === t.room)!
    .slots.map((s) => [s.id, s.name_he]),
);

// ---------- the slots and their options, in the manifest's compose order ----------
type Opt = { id: string; layer: string; shadow: string; truth: string; card: string | null; set: string | null };
const slotIds = lm.compose.order.filter((id) => id !== 'base' && !id.endsWith('-shadow'));
const layerOf = (id: string) => lm.layers.find((l) => l.id === id) ?? fail(`no layer ${id} in ${t.manifest}`);
const slots = slotIds.map((id) => {
  const cfg = t.slots[id] ?? fail(`tools/tour: no slot ${id}`);
  const z = layerOf(id).z;
  let options: Opt[];
  if (id === hm.slot.id) {
    options = lm.slot_cushions.order.map((s) => ({
      id: `set-${s}`,
      layer: lm.slot_cushions.sets[s]!.layer,
      shadow: lm.slot_cushions.sets[s]!.shadow,
      truth: lm.truths.default[s]!,
      card: null,
      set: s,
    }));
  } else {
    const d = layerOf(id);
    const truth = lm.truths.default[lm.slot_cushions.order[0]!]!;
    options = [
      { id: 'default', layer: d.file!, shadow: layerOf(`${id}-shadow`).file!, truth, card: d.product!.card_id, set: null },
      ...(lm.variants[id] ?? []).map((v) => ({ id: v.variant, layer: v.file, shadow: v.shadow, truth: v.truth, card: v.product.card_id, set: null })),
    ];
  }
  return { id, cfg, z, options };
});
for (const id of Object.keys(t.slots)) if (!slotIds.includes(id)) fail(`tools/tour names slot ${id}, which ${t.manifest} does not compose`);
const sources = [baseFile, ...slots.flatMap((s) => s.options.flatMap((o) => [at(join(dir, o.layer)), at(join(dir, o.shadow)), at(join(dir, o.truth))]))];
for (const f of sources) if (!existsSync(f)) fail(`missing ${f}`);

// ---------- MOCK7, the gate: the default composition of these files is the manifest's own default frame ----------
// (the manifest's formula, per product in its order: out = round((below × shadow / 255)(1 − a) + rgb × a), numpy's
// rint; the cushions: the first set, its shadow and its layer together). Every channel value, or the build stops.
const rint = (x: number) => {
  const f = Math.floor(x);
  const d = x - f;
  return d > 0.5 ? f + 1 : d < 0.5 ? f : f % 2 === 0 ? f : f + 1;
};
const gateTruth = lm.truths.default[lm.slot_cushions.order[0]!]!;
let gateStat = '';
{
  const rgb = async (f: string, ch: 3 | 4) => {
    const img = sharp(at(join(dir, f)));
    const { data, info } = await (ch === 4 ? img.ensureAlpha() : img.removeAlpha()).raw().toBuffer({ resolveWithObject: true });
    if (info.width !== W || info.height !== H) fail(`${f} is ${info.width}×${info.height}, not ${W}×${H}`);
    return data;
  };
  const st = Buffer.from(await rgb(baseLayer.file ?? 'base.png', 3));
  for (const s of slots) {
    const o = s.options[0]!;
    const p = await rgb(o.layer, 4);
    const sh = await rgb(o.shadow, 3);
    for (let i = 0; i < W * H; i++) {
      const al = p[i * 4 + 3]!;
      if (!al && sh[i * 3] === 255 && sh[i * 3 + 1] === 255 && sh[i * 3 + 2] === 255) continue;
      const a = al / 255;
      for (let k = 0; k < 3; k++) st[i * 3 + k] = rint(((st[i * 3 + k]! * sh[i * 3 + k]!) / 255) * (1 - a) + p[i * 4 + k]! * a);
    }
  }
  const truth = await rgb(gateTruth, 3);
  let max = 0;
  let over1 = 0;
  for (let i = 0; i < st.length; i++) {
    const d = Math.abs(st[i]! - truth[i]!);
    if (d > max) max = d;
    if (d > 1) over1++;
  }
  // the phase 2 tool's own truths are its graded composites, not its stack to the bit: render-agent's verification of
  // this manifest (verify-layers-basket.json, 3_stack) holds the stack to them at max 4 levels and 99.9% within 1 —
  // the same bound here (a room built by tools/make-tour-room.ts is held to 0)
  if (max > 4 || over1 > st.length * 0.001)
    fail(`the default layers in ${t.manifest}'s order miss ${gateTruth}: max ${max} levels, ${over1} channel values over 1`);
  gateStat = `max ${max} levels, ${((over1 / st.length) * 100).toFixed(3)}% of the values over 1`;
}

const REL = `tour/${t.room}/${t.style}/M0`;
const OUT = join(MEDIA_OUT, REL);
/** the wheel's card: the longest side of the picture (tools/make-studio.ts uses the same) */
const CARD = 360;
/** MOCK2: a phone composes at `lo`, a wider screen at the layers' own width (`hi`) */
const WIDTHS = { lo: 1920, hi: W } as const;
const PAD = 8;
/** our own studio pictures that passed QA, by product (tools/make-studio.ts) */
type Studio = { width: number; products: Record<string, { src: string; w: number; h: number }> };
const studioFile = join(GENERATED, 'studio-images.json');
const studio = existsSync(studioFile) ? read<Studio>(studioFile) : { width: CARD, products: {} };
if (studio.width !== CARD) fail(`studio-images.json is at ${studio.width}, the tour's card at ${CARD}`);
const stamp = createHash('sha256')
  .update(
    JSON.stringify({
      t,
      tool: readFileSync(new URL(import.meta.url), 'utf8'),
      manifest: sha(at(manifestPath)),
      sources: [...new Set(sources)].map((f) => [f, statSync(f).size, statSync(f).mtimeMs]),
    }),
  )
  .digest('hex')
  .slice(0, 16);

// ---------- the regions (px): a layer's alpha, and its shadow wherever it darkens ----------
type Px = { x0: number; y0: number; x1: number; y1: number };
type Measured = { rect: Px; alpha: Px[]; cover: number };
type Card = { w: number; h: number };
/** a slot's rectangle in the pixels of width `Wt`, rounded exactly as the engine rounds it (web/src/tour/gl.ts) */
const tierRect = (r: Px, Wt: number): Px => {
  const Ht = Math.round((Wt * H) / W);
  return { x0: Math.round((r.x0 / W) * Wt), x1: Math.round((r.x1 / W) * Wt), y0: Math.round((r.y0 / H) * Ht), y1: Math.round((r.y1 / H) * Ht) };
};
const STAMP = join(OUT, 'stamp.json');
const cached = existsSync(STAMP) ? read<{ stamp: string; slots: Record<string, Measured>; cover: number; cards: Record<string, Card> }>(STAMP) : null;
const raw = async (f: string) => {
  const { data, info } = await sharp(f).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  if (info.width !== W || info.height !== H) fail(`${f} is ${info.width}×${info.height}, not ${W}×${H}`);
  return data;
};
const empty = (): Px => ({ x0: W, y0: H, x1: -1, y1: -1 });
const grow = (b: Px, x: number, y: number) => {
  if (x < b.x0) b.x0 = x;
  if (x > b.x1) b.x1 = x;
  if (y < b.y0) b.y0 = y;
  if (y > b.y1) b.y1 = y;
};

let measured: Record<string, Measured>;
let cover: number;
const cards: Record<string, Card> = {};
if (cached?.stamp === stamp) {
  measured = cached.slots;
  cover = cached.cover;
  Object.assign(cards, cached.cards);
} else {
  rmSync(OUT, { recursive: true, force: true });
  mkdirSync(OUT, { recursive: true });
  const out = (rel: string) => {
    const f = join(OUT, rel);
    mkdirSync(dirname(f), { recursive: true });
    return f;
  };
  // MOCK7: the manifest's own base, at the two widths (the house's encoder's settings for a photograph, WebP only)
  if (ownBase)
    for (const Wt of new Set(Object.values(WIDTHS)))
      await (Wt === W ? sharp(baseFile) : sharp(baseFile).resize(Wt))
        .removeAlpha()
        .webp({ quality: 90, effort: 5, smartSubsample: true })
        .toFile(out(`base.${Wt}.webp`));
  measured = {};
  // "how much of the room they fill": the default products' alpha, inside the camera frame
  const [fx0, fy0, fx1, fy1] = lm.size.camera_frame_px;
  const covered = new Uint8Array(W * H);
  for (const s of slots) {
    const region = empty();
    const alpha: Px[] = [];
    for (const [n, o] of s.options.entries()) {
      const a = empty();
      const p = await raw(at(join(dir, o.layer)));
      const sh = await raw(at(join(dir, o.shadow)));
      for (let i = 0; i < W * H; i++) {
        const k = i * 4;
        const on = p[k + 3]! > 0;
        if (on) {
          grow(a, i % W, (i / W) | 0);
          if (n === 0) covered[i] = 1;
        }
        if (on || sh[k]! < 255 || sh[k + 1]! < 255 || sh[k + 2]! < 255) grow(region, i % W, (i / W) | 0);
      }
      if (a.x1 < 0) fail(`${o.layer} is empty`);
      alpha.push(a);
    }
    const rect: Px = {
      x0: Math.max(0, region.x0 - PAD),
      y0: Math.max(0, region.y0 - PAD),
      x1: Math.min(W, region.x1 + 1 + PAD),
      y1: Math.min(H, region.y1 + 1 + PAD),
    };
    measured[s.id] = { rect, alpha, cover: 0 };
    const cut = { left: rect.x0, top: rect.y0, width: rect.x1 - rect.x0, height: rect.y1 - rect.y0 };
    for (const [n, o] of s.options.entries()) {
      for (const Wt of new Set(Object.values(WIDTHS))) {
        // the slot's rectangle in that width's pixels, exactly as the engine rounds it (web/src/tour/gl.ts drawLayers)
        const r = tierRect(rect, Wt);
        const size = { width: r.x1 - r.x0, height: r.y1 - r.y0 };
        const layer = sharp(at(join(dir, o.layer)))
          .ensureAlpha()
          .extract(cut);
        await (Wt === W ? layer : layer.resize(size))
          // S12: near-lossless (lossy q86 and q95 missed the tool-layer threshold on the textiles)
          .webp({ nearLossless: true, quality: 60, effort: 5 })
          .toFile(out(`slots/${s.id}/${n + 1}.product.${Wt}.webp`));
        const shadow = sharp(at(join(dir, o.shadow)))
          .removeAlpha()
          .extract(cut);
        await (Wt === W ? shadow : shadow.resize(size))
          // a shadow multiplies the room: lossless, or the codec's noise near white would darken around the product
          .webp({ lossless: true, effort: 5 })
          .toFile(out(`slots/${s.id}/${n + 1}.shadow.${Wt}.webp`));
      }
      // MOCK2 (FB1): the wheel's card is the product on its own — its layer, trimmed to the product and on nothing.
      // Never a crop of the room, and never a supplier photo. A card with our own studio picture uses that instead.
      const a = alpha[n]!;
      const pad = Math.round(Math.max(a.x1 - a.x0, a.y1 - a.y0) * 0.03) + 2;
      const left = Math.max(0, a.x0 - pad);
      const top = Math.max(0, a.y0 - pad);
      const box = {
        left,
        top,
        width: Math.min(W, a.x1 + 1 + pad) - left,
        height: Math.min(H, a.y1 + 1 + pad) - top,
      };
      const k = CARD / Math.max(box.width, box.height);
      await sharp(at(join(dir, o.layer)))
        .ensureAlpha()
        .extract(box)
        .resize({ width: Math.max(1, Math.round(box.width * k)), height: Math.max(1, Math.round(box.height * k)) })
        .webp({ quality: 88, alphaQuality: 100, effort: 5 })
        .toFile(out(`slots/${s.id}/${n + 1}.card.${CARD}.webp`));
      cards[`${s.id}:${n + 1}`] = { w: Math.max(1, Math.round(box.width * k)), h: Math.max(1, Math.round(box.height * k)) };
    }
  }
  let n = 0;
  for (let y = Math.ceil(fy0); y < Math.floor(fy1); y++) for (let x = Math.ceil(fx0); x < Math.floor(fx1); x++) n += covered[y * W + x]!;
  cover = n / ((Math.floor(fx1) - Math.ceil(fx0)) * (Math.floor(fy1) - Math.ceil(fy0)));
  writeFileSync(STAMP, JSON.stringify({ stamp, slots: measured, cover, cards }));
}

// ---------- the camera and the room's box (the depth of the scan plane is computed from them, in the shader) ----------
type Plan = {
  rooms: { id: string; x: [number, number]; y: [number, number]; h: number }[];
  cameras: { id: string; loc: [number, number, number]; yaw_deg_left: number; u0: number; v0: number }[];
};
const plan = read<Plan>(repoPath(t.plan));
const cam = plan.cameras.find((c) => c.id === t.camera) ?? fail(`no camera ${t.camera} in ${t.plan}`);
const box = plan.rooms.find((r) => r.id === t.room_plan) ?? fail(`no room ${t.room_plan} in ${t.plan}`);
const [fx0, fy0, fx1, fy1] = lm.size.camera_frame_px;
const camera = {
  // the camera frame inside the canvas, canvas UV [u0, u1, v0, v1]
  frame: [fx0 / W, fx1 / W, fy0 / H, fy1 / H].map((x) => +x.toFixed(5)) as Box,
  // docs/house-plan.json conventions.projection: u = u0 + kx x/d, v = v0 + ky (hc - Z)/d (24 mm, 16:9)
  u0: cam.u0,
  v0: cam.v0,
  kx: 0.6667,
  ky: 1.1852,
  loc: cam.loc,
  yaw_deg_left: cam.yaw_deg_left,
  room: { x: box.x, y: box.y, h: box.h },
};

// ---------- the data ----------
// not rounded: the engine puts a layer back on its own pixels (rect × the canvas's size is a whole number)
const uv = (r: Px): Box => [r.x0 / W, r.x1 / W, r.y0 / H, r.y1 / H];
const depthCfg = t.depth?.[t.manifest] ?? null;
const depthMap = depthCfg ? await nearness(depthCfg) : null;
const dimsHe = (d: Shop['dimensions_cm'], kind: SlotCfg['kind']): string | null => {
  if (!d) return null;
  const a = d.width;
  const b = kind === 'floor' && d.depth && !d.height ? d.depth : d.height;
  return a && b ? `${a} × ${b} ס"מ` : null;
};
const placeholder = `data:image/webp;base64,${(
  await sharp(ownBase ? baseFile : pilotBase)
    .removeAlpha()
    .resize({ width: 48 })
    .webp({ quality: 60, effort: 6 })
    .toBuffer()
).toString('base64')}`;
const data = {
  room: t.room,
  style: t.style,
  name_he: house.name_he,
  source: lm.id,
  native: W,
  // MOCK2: the two widths a composition is made at; `lo` is what a phone uses (the room engine's own rule)
  widths: { lo: Math.min(WIDTHS.lo, W), hi: W },
  card_width: CARD,
  aspect: W / H,
  mobile_center_u: hm.mobile_center_u,
  base: ownBase
    ? { src: `${REL}/base`, widths: [...new Set(Object.values(WIDTHS))], placeholder, formats: ['webp'] }
    : { src: house.scene.base[0]!.src, widths: house.scene.base[0]!.widths, placeholder },
  camera,
  // MOCK7: the room's depth for the transitions (a small nearness map, near = white), or null: the page's fallback
  depth: depthCfg ? depthMap!.uri : null,
  cover: +cover.toFixed(4),
  slots: slots.map((s) => {
    const m = measured[s.id]!;
    const a0 = m.alpha[0]!;
    return {
      id: s.id,
      name_he: (s.id === hm.slot.id ? hm.slot.name_he : null) ?? slotNames.get(s.id) ?? s.cfg.name_he ?? fail(`no name for slot ${s.id}`),
      z: s.z,
      rect: uv(m.rect),
      depth_m: s.cfg.depth_m,
      kind: s.cfg.kind,
      order_a: s.cfg.order_a,
      hero: !!s.cfg.hero,
      // MOCK2: a card of something that stands on the floor or on a surface gets the studio card's ground shadow;
      // a curtain, a picture or a pendant does not stand on anything
      ground: s.cfg.kind === 'floor' || s.cfg.kind === 'surface',
      anchors: s.cfg.anchors.map(([x, y]) => [+((a0.x0 + (a0.x1 - a0.x0) * x) / W).toFixed(4), +((a0.y0 + (a0.y1 - a0.y0) * y) / H).toFixed(4)]),
      src: `${REL}/slots/${s.id}`,
      options: s.options.map((o, n) => {
        const p = o.card ? shop.get(o.card) : undefined;
        const set = o.set ? hm.sets.find((x) => x.id === o.set) : undefined;
        const own = p ? studio.products[p.id] : undefined;
        const card = cards[`${s.id}:${n + 1}`] ?? fail(`no card for ${s.id} ${n + 1}`);
        return {
          position: n + 1,
          // MOCK2 (FB1): what the wheel shows for this option — our own studio picture where one passed QA, else the
          // product's own layer trimmed to it. Neither is a crop of the room, and neither is a supplier photo.
          card: own
            ? { src: own.src, w: own.w, h: own.h, source: 'studio' as const }
            : { src: `${REL}/slots/${s.id}/${n + 1}.card.${CARD}`, w: card.w, h: card.h, source: 'layer' as const },
          box: uv({ ...m.alpha[n]!, x1: m.alpha[n]!.x1 + 1, y1: m.alpha[n]!.y1 + 1 }),
          // the shop's public id, name and price; null: the shop does not sell this card yet
          product_id: p?.id ?? null,
          name_he: p?.name_he ?? set?.label_he ?? null,
          price_agorot: p?.price_agorot ?? null,
          price_provisional: p?.price_provisional ?? false,
          available: !!p && p.availability.status === 'available',
          dims_he: s.cfg.dims ? dimsHe(p?.dimensions_cm, s.cfg.kind) : null,
          set: !!o.set,
        };
      }),
    };
  }),
};
mkdirSync(GENERATED, { recursive: true });
const outFile = join(GENERATED, `tour.${t.room}.${t.style}.json`);
writeFileSync(outFile, JSON.stringify(data));

const kb = (f: string) => statSync(f).size / 1024;
let defaults = 0;
let all = 0;
let files = 0;
const byWidth: Record<number, number> = {};
for (const s of slots)
  for (const [n] of s.options.entries())
    for (const Wt of new Set(Object.values(WIDTHS)))
      for (const kind of ['product', 'shadow'] as const) {
        const size = kb(join(OUT, `slots/${s.id}/${n + 1}.${kind}.${Wt}.webp`));
        byWidth[Wt] = (byWidth[Wt] ?? 0) + size;
        files++;
        if (Wt !== W) continue;
        all += size;
        if (n === 0) defaults += size;
      }
const studioCards = data.slots.reduce((n, s) => n + s.options.filter((o) => o.card.source === 'studio').length, 0);
const unsold = data.slots.flatMap((s) => s.options.filter((o) => !o.set && !o.product_id).map((o) => `${s.id} ${o.position}`));
console.log(
  `tour ${t.room}/${t.style}: ${lm.id}; ${slots.length} slots, ${slots.reduce((n, s) => n + s.options.length, 0)} options (${files} layer files; ` +
    Object.entries(byWidth)
      .map(([w, kb_]) => `${kb_.toFixed(0)} KB at ${w}`)
      .join(', ') +
    `; the default composition's ${slots.length * 2} layers ${defaults.toFixed(0)} KB of ${all.toFixed(0)} KB at ${W}` +
    `); the products fill ${(cover * 100).toFixed(1)}% of the frame; the wheel's cards: ${studioCards} our own studio pictures and ` +
    `${data.slots.reduce((n, s) => n + s.options.length, 0) - studioCards} trimmed layers, no room crops; ` +
    `${unsold.length} options are not in the shop yet (${unsold.join(', ')}); the gate: the defaults against ${gateTruth}, ${gateStat}; ` +
    `the base: ${ownBase ? `its own (${baseLayer.file})` : "the house's"}; depth: ${depthCfg ? depthCfg.file : 'none (the fallback)'}` +
    (pin
      ? `; pinned to ${t.pin} (${Object.keys(pin.files).length} files, ${pinnedFrom.length} read from git: ${pinnedFrom.join(', ') || 'none changed on disk'})`
      : '') +
    ` → ${outFile}`,
);

// ---------- MOCK7: `--write-pin` writes the pin for this manifest (every file read above, as git holds it at HEAD) ----------
if (process.argv.includes('--write-pin') && t.pin) {
  const commit = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: REPO, encoding: 'utf8' }).trim();
  const files: Record<string, string> = {};
  for (const rel of [...touched].sort()) {
    const staged = execFileSync('git', ['ls-files', '-s', '--', rel], { cwd: REPO, encoding: 'utf8' }).trim().split(/\s+/)[1];
    const b = readFileSync(join(REPO, rel));
    const blob = createHash('sha1').update(`blob ${b.length}\0`).update(b).digest('hex');
    if (staged !== blob) fail(`${rel} is not in git as it is on disk: commit it before pinning`);
    files[rel] = blob;
  }
  const note =
    "MOCK7 (2026-11-26, briefs/site-mock7-tour-transitions-2026-11-26.md): the living room pinned to manifest-basket.json (Olia, the lfix fixes, the moved basket; the old walnut table is in none of these files). Every file tools/make-tour.ts reads for this manifest, as git holds it: the blob of each at the commit below. A file whose blob differs on disk is read from git's own copy of the pinned blob (written to .generated/pinned/), so nothing new is picked up unnoticed. The pin holds only for `manifest`; a new manifest line reads its files as they are, and `npx --no-install tsx tools/make-tour.ts tools/tour/living-room.warm-modern.json --write-pin` writes the pin again (MOCK6's pin, for manifest-r9.json, is in git's history).";
  writeFileSync(sitePath(t.pin), JSON.stringify({ note, commit, manifest: t.manifest, files }, null, 2) + '\n');
  console.log(`make-tour: pinned ${Object.keys(files).length} files at ${commit.slice(0, 7)} → ${t.pin}`);
}
