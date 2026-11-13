/**
 * MOCK1 (2026-11-12): the wow-tour mock-up's room from the phase 2 tool layers of the warm-modern house
 * (tools/tour/<room>.<style>.json → the render folder's layers manifest). Behind HD_PUBLIC=0. Writes:
 *
 *   .generated/tour.<room>.<style>.json    the tour's room as its engine reads it (web/src/tour/): the base, every slot
 *                                          with its options (the default first, then the variants in the manifest's order;
 *                                          the cushions: the three sets), each option's layer and shadow, where its ring
 *                                          starts, its depth along the camera's axis, and the shop's record of its card
 *   web/public/media/tour/<room>/<style>/M0/  every layer cut to its slot's rectangle, at the layers' own width (the house
 *                                          composes there, QA finding 1 of 2026-11-10): the product near-lossless WebP, the
 *                                          shadow lossless (the same settings as tools/make-house.ts, S12); and the wheel's
 *                                          picture of every option, cut from the approved composite that shows it
 *
 * The base is the house's own (tools/make-house.ts): the manifest's base.png is the pilot's, byte for byte (checked
 * here), so its encoded files are shared and nothing is encoded twice.
 *
 * A product's name and price are the shop's record of its card (.generated/catalog.story.full.json, the same pricing
 * path), when the shop has one. A card the shop does not sell yet has no public name and no price: it is shown under its
 * slot's name, "עוד לא במכירה" (no data is written here, and no card is read for a name).
 */
import sharp from 'sharp';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { GENERATED, MEDIA_OUT, repoPath, sitePath } from './lib/paths';

type Box = [number, number, number, number];
type SlotCfg = { depth_m: number; kind: 'floor' | 'wall' | 'surface' | 'hang'; anchors: [number, number][]; order_a: number; dims?: boolean; hero?: boolean };
type TourManifest = {
  room: string;
  style: string;
  layers: string;
  manifest: string;
  house: string;
  plan: string;
  camera: string;
  room_plan: string;
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
const dir = repoPath(t.layers);
const lm = read<LayersManifest>(join(dir, t.manifest));
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
const pilotBase = join(repoPath(hm.pilot), hm.layers_dir, 'base.png');
if (sha(join(dir, 'base.png')) !== sha(pilotBase))
  fail(`${t.layers}/base.png is not the house's base (${hm.pilot}/${hm.layers_dir}/base.png): encode it here first`);

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
const sources = slots.flatMap((s) => s.options.flatMap((o) => [join(dir, o.layer), join(dir, o.shadow), join(dir, o.truth)]));
for (const f of sources) if (!existsSync(f)) fail(`missing ${f}`);

const REL = `tour/${t.room}/${t.style}/M0`;
const OUT = join(MEDIA_OUT, REL);
const THUMB = 360;
const PAD = 8;
const stamp = createHash('sha256')
  .update(
    JSON.stringify({
      t,
      tool: readFileSync(new URL(import.meta.url), 'utf8'),
      manifest: sha(join(dir, t.manifest)),
      sources: [...new Set(sources)].map((f) => [f, statSync(f).size, statSync(f).mtimeMs]),
    }),
  )
  .digest('hex')
  .slice(0, 16);

// ---------- the regions (px): a layer's alpha, and its shadow wherever it darkens ----------
type Px = { x0: number; y0: number; x1: number; y1: number };
type Measured = { rect: Px; alpha: Px[]; cover: number };
const STAMP = join(OUT, 'stamp.json');
const cached = existsSync(STAMP) ? read<{ stamp: string; slots: Record<string, Measured>; cover: number }>(STAMP) : null;
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
if (cached?.stamp === stamp) {
  measured = cached.slots;
  cover = cached.cover;
} else {
  rmSync(OUT, { recursive: true, force: true });
  mkdirSync(OUT, { recursive: true });
  const out = (rel: string) => {
    const f = join(OUT, rel);
    mkdirSync(dirname(f), { recursive: true });
    return f;
  };
  measured = {};
  // "how much of the room they fill": the default products' alpha, inside the camera frame
  const [fx0, fy0, fx1, fy1] = lm.size.camera_frame_px;
  const covered = new Uint8Array(W * H);
  for (const s of slots) {
    const region = empty();
    const alpha: Px[] = [];
    for (const [n, o] of s.options.entries()) {
      const a = empty();
      const p = await raw(join(dir, o.layer));
      const sh = await raw(join(dir, o.shadow));
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
      await sharp(join(dir, o.layer))
        .ensureAlpha()
        .extract(cut)
        // S12: near-lossless (lossy q86 and q95 missed the tool-layer threshold on the textiles)
        .webp({ nearLossless: true, quality: 60, effort: 5 })
        .toFile(out(`slots/${s.id}/${n + 1}.product.${W}.webp`));
      await sharp(join(dir, o.shadow))
        .removeAlpha()
        .extract(cut)
        // a shadow multiplies the room: lossless, or the codec's noise near white would darken around the product
        .webp({ lossless: true, effort: 5 })
        .toFile(out(`slots/${s.id}/${n + 1}.shadow.${W}.webp`));
      // the wheel's card: the product in the room, from the approved composite that shows it (never a layer on its own)
      const a = alpha[n]!;
      const side = Math.min(H, Math.round(Math.max(a.x1 - a.x0, a.y1 - a.y0) * 1.16) + 24);
      const left = Math.max(0, Math.min(W - side, Math.round((a.x0 + a.x1) / 2 - side / 2)));
      const top = Math.max(0, Math.min(H - side, Math.round((a.y0 + a.y1) / 2 - side / 2)));
      await sharp(join(dir, o.truth))
        .extract({ left, top, width: side, height: side })
        .resize({ width: THUMB, height: THUMB })
        .webp({ quality: 80 })
        .toFile(out(`slots/${s.id}/${n + 1}.thumb.${THUMB}.webp`));
    }
  }
  let n = 0;
  for (let y = Math.ceil(fy0); y < Math.floor(fy1); y++) for (let x = Math.ceil(fx0); x < Math.floor(fx1); x++) n += covered[y * W + x]!;
  cover = n / ((Math.floor(fx1) - Math.ceil(fx0)) * (Math.floor(fy1) - Math.ceil(fy0)));
  writeFileSync(STAMP, JSON.stringify({ stamp, slots: measured, cover }));
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
const dimsHe = (d: Shop['dimensions_cm'], kind: SlotCfg['kind']): string | null => {
  if (!d) return null;
  const a = d.width;
  const b = kind === 'floor' && d.depth && !d.height ? d.depth : d.height;
  return a && b ? `${a} × ${b} ס"מ` : null;
};
const placeholder = `data:image/webp;base64,${(await sharp(pilotBase).removeAlpha().resize({ width: 48 }).webp({ quality: 60, effort: 6 }).toBuffer()).toString('base64')}`;
const data = {
  room: t.room,
  style: t.style,
  name_he: house.name_he,
  source: lm.id,
  native: W,
  aspect: W / H,
  mobile_center_u: hm.mobile_center_u,
  base: { src: house.scene.base[0]!.src, widths: house.scene.base[0]!.widths, placeholder },
  camera,
  cover: +cover.toFixed(4),
  slots: slots.map((s) => {
    const m = measured[s.id]!;
    const a0 = m.alpha[0]!;
    return {
      id: s.id,
      name_he: (s.id === hm.slot.id ? hm.slot.name_he : null) ?? slotNames.get(s.id) ?? fail(`no name for slot ${s.id}`),
      z: s.z,
      rect: uv(m.rect),
      depth_m: s.cfg.depth_m,
      kind: s.cfg.kind,
      order_a: s.cfg.order_a,
      hero: !!s.cfg.hero,
      anchors: s.cfg.anchors.map(([x, y]) => [+((a0.x0 + (a0.x1 - a0.x0) * x) / W).toFixed(4), +((a0.y0 + (a0.y1 - a0.y0) * y) / H).toFixed(4)]),
      src: `${REL}/slots/${s.id}`,
      options: s.options.map((o, n) => {
        const p = o.card ? shop.get(o.card) : undefined;
        const set = o.set ? hm.sets.find((x) => x.id === o.set) : undefined;
        return {
          position: n + 1,
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
for (const s of slots)
  for (const [n] of s.options.entries())
    for (const kind of ['product', 'shadow'] as const) {
      const size = kb(join(OUT, `slots/${s.id}/${n + 1}.${kind}.${W}.webp`));
      all += size;
      files++;
      if (n === 0) defaults += size;
    }
const unsold = data.slots.flatMap((s) => s.options.filter((o) => !o.set && !o.product_id).map((o) => `${s.id} ${o.position}`));
console.log(
  `tour ${t.room}/${t.style}: ${lm.id}; ${slots.length} slots, ${slots.reduce((n, s) => n + s.options.length, 0)} options (${files} layer files, ${all.toFixed(0)} KB; ` +
    `the default composition's ${slots.length * 2} layers ${defaults.toFixed(0)} KB at ${W}); the products fill ${(cover * 100).toFixed(1)}% of the frame; ` +
    `${unsold.length} options are not in the shop yet (${unsold.join(', ')}) → ${outFile}`,
);
