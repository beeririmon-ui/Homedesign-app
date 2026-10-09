/**
 * Temporary room media until QA-passed layers exist (CLAUDE.md: "נכס שלא עבר QA לא נכנס לאתר").
 *
 * Source images are resolved through assets/manifest.json ids, never hard-coded render paths.
 * Output follows the final naming convention (docs/architecture.md, "נכסים"), so swapping in real
 * layers later changes files, not code:
 *
 *   media/rooms/<room>/<style>/<frame>/base/<layer>.<w>.<fmt>
 *   media/rooms/<room>/<style>/<frame>/slots/<slot>/<n>.<product|shadow|light>.<w>.<fmt>
 *   media/rooms/<room>/<style>/<frame>/depth.<w>.webp
 *   media/rooms/hall/<style>/H0/base/shell.<w>.<fmt>
 *   media/transitions/<id>/<style>/<w>/<NNN>.webp
 *
 * How the temporary layers are made (all flagged temporary in the scene manifest):
 *   shell        the full styled preview (products baked in; fixed furniture is not separated yet)
 *   product n=1  a cut-out of the preview inside the slot boxes (identical to the shell)
 *   product n>1  the same cut-out recoloured toward the option's product colour (shading kept)
 *   shadow       none: the shell already carries the real shadow of option 1, and a second, synthetic
 *                multiply shadow (shared by all options) darkened the room around each product
 *   light        none: the lamp glow is baked into the shell; a synthetic screen glow on top doubled it
 *   depth        synthesised from the room planes and the slot boxes (no depth render for this image)
 *
 * Mask rules (QA: switching options may change nothing outside the product's bounding box):
 *   - alpha is exactly 0 outside the slot shapes: the feather runs inward from the box edge, the layer rect is
 *     the shapes' bounding box with no padding;
 *   - inside, alpha = "differs from the local background" (objectness), cleaned (blur + re-threshold) so
 *     background noise does not become specks of colour;
 *   - the recolour weight also falls off with colour distance from the product's own mean colour, so wall,
 *     floor or sofa pixels that slipped into the box keep their colour.
 */
import sharp from 'sharp';
import { readFileSync, writeFileSync, mkdirSync, rmSync, existsSync, readdirSync, statSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { join, dirname } from 'node:path';
import type { PublicCatalog } from '@hd/shared';
import { GENERATED, MEDIA_OUT, repoPath, sitePath } from './lib/paths';

type Box = [number, number, number, number]; // u0 u1 v0 v1
type Ellipse = [number, number, number, number]; // cu cv ru rv
type TempSlot = {
  boxes: Box[];
  ellipses?: Ellipse[];
  objectness?: boolean;
  hotspot: [number, number];
  visible?: boolean;
  depth: number;
  glow?: [number, number, number][];
  exclude?: string[];
  variant_palette?: string[];
  zoom?: Box;
};
type TempFile = {
  room: string;
  style: string;
  frame: string;
  source_manifest_id: string;
  hall_source: string;
  transition_source: { id: string; dir: string; frames: number };
  mobile_center_u: number;
  slots: Record<string, TempSlot>;
  fixed_occluders?: Record<string, Box>;
};

const FAST = process.argv.includes('--fast'); // skip AVIF (quicker local iterations)
const WIDTHS = { lo: 1920, hi: 2752 } as const;
const FORMATS = FAST ? (['webp'] as const) : (['avif', 'webp'] as const);

const temp = JSON.parse(readFileSync(sitePath('tools/temp/living-room.nordic.json'), 'utf8')) as TempFile;
const catalog = JSON.parse(readFileSync(join(GENERATED, 'catalog.public.json'), 'utf8')) as PublicCatalog;
const manifest = JSON.parse(readFileSync(repoPath('assets/manifest.json'), 'utf8')) as {
  assets: { id: string; path: string; status?: string }[];
};

function manifestPath(id: string): string {
  const a = manifest.assets.find((x) => x.id === id);
  if (!a) throw new Error(`assets/manifest.json has no asset "${id}"`);
  return repoPath(a.path);
}

const room = catalog.rooms.find((r) => r.id === temp.room && r.built);
if (!room) throw new Error(`catalog has no built room ${temp.room}; run npm run catalog first`);
const productColor = new Map(catalog.products.map((p) => [p.id, p.color_hex]));
const PALETTE = ['#A7B09A', '#3A3A3A', '#E6DCCB', '#C8A27A'];

const roomDir = `rooms/${temp.room}/${temp.style}/${temp.frame}`;
const SCENE_FILE = join(GENERATED, `scene.${temp.room}.${temp.style}.json`);
const STAMP_FILE = join(GENERATED, 'media.stamp');

/** Inputs hash: regenerate only when the source images, coordinates, option colours or this script change. */
function inputsStamp(): string {
  const h = createHash('sha256');
  h.update(readFileSync(fileURLToPath(import.meta.url)));
  h.update(readFileSync(sitePath('tools/temp/living-room.nordic.json')));
  h.update(JSON.stringify(room!.slots.map((s) => s.options.map((o) => (o.product_id ? productColor.get(o.product_id) : null)))));
  h.update(JSON.stringify(FORMATS));
  for (const p of [manifestPath(temp.source_manifest_id), repoPath(temp.hall_source)]) {
    const st = statSync(p);
    h.update(`${p}:${st.size}:${st.mtimeMs}`);
  }
  h.update(readdirSync(repoPath(temp.transition_source.dir)).join(','));
  return h.digest('hex');
}
const stamp = inputsStamp();
if (
  !process.argv.includes('--force') &&
  existsSync(STAMP_FILE) &&
  existsSync(SCENE_FILE) &&
  existsSync(MEDIA_OUT) &&
  readFileSync(STAMP_FILE, 'utf8') === stamp
) {
  console.log('temp media up to date (use --force to rebuild)');
  process.exit(0);
}
rmSync(MEDIA_OUT, { recursive: true, force: true });
mkdirSync(MEDIA_OUT, { recursive: true });

async function encode(img: sharp.Sharp, rel: string): Promise<void> {
  for (const fmt of FORMATS) {
    const out = join(MEDIA_OUT, `${rel}.${fmt}`);
    mkdirSync(dirname(out), { recursive: true });
    const pipeline = img.clone();
    if (fmt === 'avif') await pipeline.avif({ quality: 52, effort: 4 }).toFile(out);
    else await pipeline.webp({ quality: 80, alphaQuality: 90, effort: 5 }).toFile(out);
  }
}

const hexRgb = (hex: string): [number, number, number] => {
  const n = parseInt(hex.slice(1), 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
};
const lum = (r: number, g: number, b: number) => 0.2126 * r + 0.7152 * g + 0.0722 * b;
const smooth = (a: number, b: number, x: number) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

function ellipseWeight(u: number, v: number, e: Ellipse, feather: number): number {
  const d = Math.hypot((u - e[0]) / e[2], (v - e[1]) / e[3]);
  return 1 - smooth(1, 1 + feather / Math.min(e[2], e[3]), d);
}

/** Bounding boxes of every shape of a slot (ellipses included). */
function shapeBoxes(t: TempSlot): Box[] {
  return [...t.boxes, ...(t.ellipses ?? []).map((e): Box => [e[0] - e[2], e[0] + e[2], e[1] - e[3], e[1] + e[3]])];
}

/** Feathered rounded-rect weight of a point in frame coordinates. */
function boxWeight(u: number, v: number, b: Box, feather: number): number {
  const du = Math.max(b[0] - u, 0, u - b[1]);
  const dv = Math.max(b[2] - v, 0, v - b[3]);
  const d = Math.hypot(du, dv * (9 / 16));
  return 1 - smooth(0, feather, d);
}

type Raw = { data: Buffer; width: number; height: number };

async function loadRaw(path: string, width: number): Promise<Raw> {
  const { data, info } = await sharp(path).resize({ width }).removeAlpha().raw().toBuffer({ resolveWithObject: true });
  return { data, width: info.width, height: info.height };
}

const sceneSlots: Record<string, unknown> = {};

/** Weight 1 inside the box, 0 on and outside its edge, smooth over `feather` inward. */
function insideBoxWeight(u: number, v: number, b: Box, feather: number): number {
  const d = Math.min(u - b[0], b[1] - u, (v - b[2]) * (9 / 16), (b[3] - v) * (9 / 16));
  return d <= 0 ? 0 : smooth(0, feather, d);
}
function insideEllipseWeight(u: number, v: number, e: Ellipse, feather: number): number {
  const d = Math.hypot((u - e[0]) / e[2], (v - e[1]) / e[3]);
  return d >= 1 ? 0 : 1 - smooth(1 - feather / Math.min(e[2], e[3]), 1, d);
}

/** Separable box blur of a float mask (radius in px), used to clean the objectness mask. */
function blurMask(m: Float32Array, w: number, h: number, r: number): Float32Array {
  const tmp = new Float32Array(w * h);
  const out = new Float32Array(w * h);
  const n = 2 * r + 1;
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      let s = 0;
      for (let k = -r; k <= r; k++) s += m[y * w + Math.min(w - 1, Math.max(0, x + k))]!;
      tmp[y * w + x] = s / n;
    }
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      let s = 0;
      for (let k = -r; k <= r; k++) s += tmp[Math.min(h - 1, Math.max(0, y + k)) * w + x]!;
      out[y * w + x] = s / n;
    }
  return out;
}

/** Product layer cut-outs. Alpha = slot shapes (feathered inward) × cleaned objectness − occluders in front. */
async function makeSlotLayers(base: Raw, key: 'lo' | 'hi', slotId: string, t: TempSlot, optionColors: (string | null)[]) {
  const all = shapeBoxes(t);
  if (all.length === 0) return null;
  const W = base.width;
  const H = base.height;
  const u0 = Math.max(0, Math.min(...all.map((b) => b[0])));
  const u1 = Math.min(1, Math.max(...all.map((b) => b[1])));
  const v0 = Math.max(0, Math.min(...all.map((b) => b[2])));
  const v1 = Math.min(1, Math.max(...all.map((b) => b[3])));
  const x0 = Math.floor(u0 * W);
  const y0 = Math.floor(v0 * H);
  const w = Math.ceil(u1 * W) - x0;
  const h = Math.ceil(v1 * H) - y0;
  const feather = 0.0035; // ≈ 7 px at 1920, inside the box

  // local background: the middle half (by luminance) of a ring just outside the shapes' bounding box
  const ring = Math.round(W * 0.006);
  const border: [number, number, number][] = [];
  for (let x = -ring; x < w + ring; x += 2) for (const y of [-ring, h - 1 + ring]) border.push(px(base, x0 + x, y0 + y));
  for (let y = -ring; y < h + ring; y += 2) for (const x of [-ring, w - 1 + ring]) border.push(px(base, x0 + x, y0 + y));
  border.sort((a, b) => lum(...a) - lum(...b));
  const mid = border.slice(Math.floor(border.length * 0.25), Math.ceil(border.length * 0.75));
  const bg = [0, 1, 2].map((i) => mid.reduce((sum, c) => sum + c[i]!, 0) / mid.length) as [number, number, number];

  const occBoxes: Box[] = [];
  const occEllipses: Ellipse[] = [];
  for (const name of t.exclude ?? []) {
    const fixed = temp.fixed_occluders?.[name];
    if (fixed) occBoxes.push(fixed);
    occBoxes.push(...(temp.slots[name]?.boxes ?? []));
    occEllipses.push(...(temp.slots[name]?.ellipses ?? []));
  }
  const useObjectness = t.objectness !== false;
  const shape = new Float32Array(w * h);
  const obj = new Float32Array(w * h);
  for (let y = 0; y < h; y++) {
    const v = (y0 + y + 0.5) / H;
    for (let x = 0; x < w; x++) {
      const u = (x0 + x + 0.5) / W;
      let box = 0;
      for (const b of t.boxes) box = Math.max(box, insideBoxWeight(u, v, b, feather));
      for (const e of t.ellipses ?? []) box = Math.max(box, insideEllipseWeight(u, v, e, feather));
      if (box <= 0) continue;
      let occ = 0;
      for (const b of occBoxes) occ = Math.max(occ, boxWeight(u, v, b, 0.004));
      for (const e of occEllipses) occ = Math.max(occ, ellipseWeight(u, v, e, 0.004));
      shape[y * w + x] = box * (1 - occ);
      const [r, g, b] = px(base, x0 + x, y0 + y);
      obj[y * w + x] = useObjectness ? smooth(0.05, 0.14, Math.hypot(r - bg[0], g - bg[1], b - bg[2])) : 1;
    }
  }
  // clean the objectness: close small holes and drop isolated specks, then soften the edge by ~2 px
  const r1 = Math.max(1, Math.round(W / 960));
  const cleaned = blurMask(obj, w, h, 2 * r1);
  for (let i = 0; i < cleaned.length; i++) cleaned[i] = smooth(0.35, 0.65, cleaned[i]!);
  const soft = blurMask(cleaned, w, h, r1);
  const alpha = new Float32Array(w * h);
  for (let i = 0; i < alpha.length; i++) alpha[i] = shape[i]! * soft[i]!;

  // the product's own colour (well inside the mask), and its mean luminance
  let lumSum = 0;
  let wSum = 0;
  const mean = [0, 0, 0];
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      const a = alpha[y * w + x]!;
      if (a < 0.8) continue;
      const c = px(base, x0 + x, y0 + y);
      lumSum += lum(...c);
      for (let k = 0; k < 3; k++) mean[k] = mean[k]! + c[k]!;
      wSum++;
    }
  const meanLum = wSum > 0 ? lumSum / wSum : 0.5;
  const meanChroma = wSum > 0 ? mean.map((m) => m / wSum - meanLum) : [0, 0, 0];

  const product: string[] = [];
  for (let n = 0; n < optionColors.length; n++) {
    const target = optionColors[n];
    const out = Buffer.alloc(w * h * 4);
    const [tr, tg, tb] = target ? hexRgb(target) : [0, 0, 0];
    const tl = target ? Math.max(0.04, lum(tr, tg, tb)) : 0;
    for (let y = 0; y < h; y++)
      for (let x = 0; x < w; x++) {
        const a = alpha[y * w + x]!;
        const o = (y * w + x) * 4;
        if (a <= 0) continue; // fully transparent, colour 0 (premultiplied-safe)
        let [r, g, b] = px(base, x0 + x, y0 + y);
        if (n > 0 && target) {
          const l = lum(r, g, b);
          // pixels whose colour is far from the product's own colour (wall, floor, a neighbour) are not recoloured
          const cd = Math.hypot(r - l - meanChroma[0]!, g - l - meanChroma[1]!, b - l - meanChroma[2]!);
          const sim = 1 - smooth(0.04, 0.12, cd);
          const nl = Math.min(1, Math.max(0, tl + (l - meanLum) * 0.9));
          const k = nl / tl;
          const sat = 0.82 * sim;
          r = r * (1 - sat) + Math.min(1, tr * k) * sat;
          g = g * (1 - sat) + Math.min(1, tg * k) * sat;
          b = b * (1 - sat) + Math.min(1, tb * k) * sat;
        }
        out[o] = Math.round(r * 255);
        out[o + 1] = Math.round(g * 255);
        out[o + 2] = Math.round(b * 255);
        out[o + 3] = Math.round(a * 255);
      }
    const rel = `${roomDir}/slots/${slotId}/${n + 1}.product.${WIDTHS[key]}`;
    await encode(sharp(out, { raw: { width: w, height: h, channels: 4 } }), rel);
    product.push(rel);
  }

  return { rect: [x0 / W, (x0 + w) / W, y0 / H, (y0 + h) / H] as Box, product };
}

function px(img: Raw, x: number, y: number): [number, number, number] {
  const i = (Math.min(img.height - 1, Math.max(0, y)) * img.width + Math.min(img.width - 1, Math.max(0, x))) * 3;
  return [img.data[i]! / 255, img.data[i + 1]! / 255, img.data[i + 2]! / 255];
}

/** Synthetic depth (1 = near): back wall far, left wall nearer to the left edge, floor nearer to the bottom. */
async function makeDepth() {
  const W = 480;
  const H = 270;
  const out = Buffer.alloc(W * H);
  const corner = 0.4;
  const slotList = Object.values(temp.slots);
  for (let y = 0; y < H; y++)
    for (let x = 0; x < W; x++) {
      const u = (x + 0.5) / W;
      const v = (y + 0.5) / H;
      let d = u > corner ? 0.1 : 0.1 + 0.62 * ((corner - u) / corner);
      const floorLine = u > corner ? 0.72 + 0.07 * ((u - corner) / (1 - corner)) : 0.72 + 0.17 * ((corner - u) / corner);
      if (v > floorLine) d = Math.max(d, 0.12 + 0.88 * ((v - floorLine) / (1 - floorLine)));
      const ceilLine = u > corner ? 0.1 - 0.05 * ((u - corner) / (1 - corner)) : 0.1 + 0.06 * ((corner - u) / corner);
      if (v < ceilLine) d = Math.max(d, 0.1 + 0.4 * ((ceilLine - v) / ceilLine));
      for (const t of slotList) for (const b of shapeBoxes(t)) d = Math.max(d, t.depth * boxWeight(u, v, b, 0.015));
      out[y * W + x] = Math.round(Math.min(1, d) * 255);
    }
  const rel = `${roomDir}/depth.${W}`;
  const file = join(MEDIA_OUT, `${rel}.webp`);
  mkdirSync(dirname(file), { recursive: true });
  await sharp(out, { raw: { width: W, height: H, channels: 1 } })
    .blur(3)
    .webp({ quality: 90 })
    .toFile(file);
  return `${rel}`;
}

async function main() {
  const t0 = Date.now();
  const source = manifestPath(temp.source_manifest_id);
  const scene: Record<string, unknown> = {
    room: temp.room,
    style: temp.style,
    frame: temp.frame,
    temporary: true,
    source: temp.source_manifest_id,
    aspect: 16 / 9,
    mobile_center_u: temp.mobile_center_u,
    widths: WIDTHS,
    formats: FORMATS,
  };
  const bases: Record<string, Raw> = {};
  for (const key of ['lo', 'hi'] as const) {
    bases[key] = await loadRaw(source, WIDTHS[key]);
    await encode(sharp(source).resize({ width: WIDTHS[key] }), `${roomDir}/base/shell.${WIDTHS[key]}`);
  }
  // 1280 for small phones and the poster image
  await encode(sharp(source).resize({ width: 1280 }), `${roomDir}/base/shell.1280`);
  scene.base = [{ id: 'shell', z: 0, blend: 'normal', src: `${roomDir}/base/shell`, widths: [1280, WIDTHS.lo, WIDTHS.hi], temporary: true }];

  for (const slot of room!.slots) {
    const t = temp.slots[slot.id];
    if (!t) continue;
    const pal = t.variant_palette ?? PALETTE;
    const colors = slot.options.map((o, i) => (i === 0 ? null : ((o.product_id ? productColor.get(o.product_id) : null) ?? pal[(i - 1) % pal.length]!)));
    const entry: Record<string, unknown> = { z: slot.z, depth: t.depth, temporary: true };
    // the product's own box, for its ring on the stage (split products: the part the zoom shows)
    const shapes = shapeBoxes(t);
    entry.ring = t.zoom
      ? t.zoom
      : shapes.length
        ? [Math.min(...shapes.map((b) => b[0])), Math.max(...shapes.map((b) => b[1])), Math.min(...shapes.map((b) => b[2])), Math.max(...shapes.map((b) => b[3]))]
        : null;
    for (const key of ['lo', 'hi'] as const) {
      const layers = await makeSlotLayers(bases[key]!, key, slot.id, t, colors);
      if (key === 'lo') {
        entry.product = layers ? { rect: layers.rect, src: slot.options.map((_, n) => `${roomDir}/slots/${slot.id}/${n + 1}.product`) } : null;
        // temporary layers are cut from the shell, which already holds this slot's real shadow and lamp light
        entry.shadow = null;
        entry.light = null;
      }
    }
    sceneSlots[slot.id] = entry;
  }
  scene.slots = sceneSlots;
  scene.depth = { src: await makeDepth(), width: 480 };

  // Hall frame H0 (site opening frame, U1). Temporary: prototype hall render.
  const hallSrc = repoPath(temp.hall_source);
  for (const w of [1280, WIDTHS.lo]) await encode(sharp(hallSrc).resize({ width: w }), `rooms/hall/${temp.style}/H0/base/shell.${w}`);
  scene.hall = { src: `rooms/hall/${temp.style}/H0/base/shell`, widths: [1280, WIDTHS.lo], temporary: true };

  // Transition T-E0 (hall → living), temporary frames from the prototype walk-in.
  const tdir = repoPath(temp.transition_source.dir);
  const frames = readdirSync(tdir)
    .filter((f) => f.endsWith('.webp'))
    .sort();
  const tw = 1280;
  for (const [i, f] of frames.entries()) {
    const out = join(MEDIA_OUT, `transitions/${temp.transition_source.id}/${temp.style}/${tw}/${String(i + 1).padStart(3, '0')}.webp`);
    mkdirSync(dirname(out), { recursive: true });
    await sharp(join(tdir, f)).resize({ width: tw }).webp({ quality: 72, effort: 5 }).toFile(out);
  }
  scene.transitions = {
    [temp.transition_source.id]: {
      from: 'hall',
      to: temp.room,
      frames: frames.length,
      fps: 30,
      width: tw,
      src: `transitions/${temp.transition_source.id}/${temp.style}/${tw}`,
      temporary: true,
    },
  };

  writeFileSync(SCENE_FILE, JSON.stringify(scene, null, 1));
  writeFileSync(STAMP_FILE, stamp);
  console.log(`temp media → ${MEDIA_OUT} (${((Date.now() - t0) / 1000).toFixed(1)}s, formats ${FORMATS.join('+')})`);
}

await main();
