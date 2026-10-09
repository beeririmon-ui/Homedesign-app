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
 *   product n=1  a feathered cut-out of the preview at the slot box (identical to the shell)
 *   product n>1  the same cut-out recoloured toward the option's product colour (luminance kept)
 *   shadow       one soft multiply shadow per slot, shared by its options
 *   light        one screen glow per lamp slot, shared by its options (the pool is the same per spec)
 *   depth        synthesised from the room planes and the slot boxes (no depth render for this image)
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

/** Product layer cut-outs. Alpha = feathered slot boxes × "differs from the local background" − occluders in front. */
async function makeSlotLayers(base: Raw, key: 'lo' | 'hi', slotId: string, t: TempSlot, optionColors: (string | null)[]) {
  const all = shapeBoxes(t);
  if (all.length === 0) return null;
  const W = base.width;
  const H = base.height;
  const pad = 0.012;
  const u0 = Math.max(0, Math.min(...all.map((b) => b[0])) - pad);
  const u1 = Math.min(1, Math.max(...all.map((b) => b[1])) + pad);
  const v0 = Math.max(0, Math.min(...all.map((b) => b[2])) - pad * (16 / 9));
  const v1 = Math.min(1, Math.max(...all.map((b) => b[3])) + pad * (16 / 9));
  const x0 = Math.floor(u0 * W);
  const y0 = Math.floor(v0 * H);
  const w = Math.ceil(u1 * W) - x0;
  const h = Math.ceil(v1 * H) - y0;

  // local background: the middle half (by luminance) of the crop border
  const border: [number, number, number][] = [];
  for (let x = 0; x < w; x += 2) for (const y of [0, h - 1]) border.push(px(base, x0 + x, y0 + y));
  for (let y = 0; y < h; y += 2) for (const x of [0, w - 1]) border.push(px(base, x0 + x, y0 + y));
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
  const alpha = new Float32Array(w * h);
  let lumSum = 0;
  let wSum = 0;
  for (let y = 0; y < h; y++) {
    const v = (y0 + y + 0.5) / H;
    for (let x = 0; x < w; x++) {
      const u = (x0 + x + 0.5) / W;
      let box = 0;
      for (const b of t.boxes) box = Math.max(box, boxWeight(u, v, b, 0.006));
      for (const e of t.ellipses ?? []) box = Math.max(box, ellipseWeight(u, v, e, 0.006));
      if (box <= 0) continue;
      let occ = 0;
      for (const b of occBoxes) occ = Math.max(occ, boxWeight(u, v, b, 0.004));
      for (const e of occEllipses) occ = Math.max(occ, ellipseWeight(u, v, e, 0.004));
      const i = ((y0 + y) * W + (x0 + x)) * 3;
      const r = base.data[i]! / 255;
      const g = base.data[i + 1]! / 255;
      const b = base.data[i + 2]! / 255;
      const dist = Math.hypot(r - bg[0], g - bg[1], b - bg[2]);
      const a = box * (useObjectness ? smooth(0.04, 0.13, dist) : 1) * (1 - occ);
      alpha[y * w + x] = a;
      lumSum += lum(r, g, b) * a;
      wSum += a;
    }
  }
  const meanLum = wSum > 0 ? lumSum / wSum : 0.5;

  const product: string[] = [];
  for (let n = 0; n < optionColors.length; n++) {
    const target = optionColors[n];
    const out = Buffer.alloc(w * h * 4);
    const [tr, tg, tb] = target ? hexRgb(target) : [0, 0, 0];
    const tl = target ? Math.max(0.04, lum(tr, tg, tb)) : 0;
    for (let y = 0; y < h; y++)
      for (let x = 0; x < w; x++) {
        const i = ((y0 + y) * W + (x0 + x)) * 3;
        let r = base.data[i]! / 255;
        let g = base.data[i + 1]! / 255;
        let b = base.data[i + 2]! / 255;
        if (n > 0 && target) {
          const l = lum(r, g, b);
          const nl = Math.min(1, Math.max(0, tl + (l - meanLum) * 0.9));
          const k = nl / tl;
          const sat = 0.82;
          r = r * (1 - sat) + Math.min(1, tr * k) * sat;
          g = g * (1 - sat) + Math.min(1, tg * k) * sat;
          b = b * (1 - sat) + Math.min(1, tb * k) * sat;
        }
        const o = (y * w + x) * 4;
        out[o] = Math.round(r * 255);
        out[o + 1] = Math.round(g * 255);
        out[o + 2] = Math.round(b * 255);
        out[o + 3] = Math.round(alpha[y * w + x]! * 255);
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

/** Soft contact/cast shadow, multiply. Light comes from the window on the left, so it falls right. */
async function makeShadow(key: 'lo' | 'hi', slotId: string, t: TempSlot, placement: string) {
  if (shapeBoxes(t).length === 0) return null;
  const W = WIDTHS[key];
  const H = Math.round((W * 9) / 16);
  const wall = placement === 'wall' || placement === 'window' || placement === 'ceiling';
  const boxes = shapeBoxes(t).map(
    (b): Box =>
      wall ? [b[0] + 0.004, b[1] + 0.008, b[2] + 0.01, b[3] + 0.012] : [b[0] + 0.01, b[1] + 0.025, b[3] - (b[3] - b[2]) * 0.08, Math.min(1, b[3] + 0.018)],
  );
  const u0 = Math.max(0, Math.min(...boxes.map((b) => b[0])) - 0.02);
  const u1 = Math.min(1, Math.max(...boxes.map((b) => b[1])) + 0.02);
  const v0 = Math.max(0, Math.min(...boxes.map((b) => b[2])) - 0.03);
  const v1 = Math.min(1, Math.max(...boxes.map((b) => b[3])) + 0.03);
  const x0 = Math.floor(u0 * W);
  const y0 = Math.floor(v0 * H);
  const w = Math.max(1, Math.ceil(u1 * W) - x0);
  const h = Math.max(1, Math.ceil(v1 * H) - y0);
  const out = Buffer.alloc(w * h * 4);
  const peak = wall ? 0.1 : 0.16;
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      const u = (x0 + x + 0.5) / W;
      const v = (y0 + y + 0.5) / H;
      let a = 0;
      for (const b of boxes) a = Math.max(a, boxWeight(u, v, b, 0.018));
      a *= peak;
      const i = (y * w + x) * 4;
      // premultiplied-friendly: colour of the shadow tint, alpha = strength
      out[i] = 92;
      out[i + 1] = 78;
      out[i + 2] = 64;
      out[i + 3] = Math.round(a * 255);
    }
  const rel = `${roomDir}/slots/${slotId}/1.shadow.${W}`;
  await encode(sharp(out, { raw: { width: w, height: h, channels: 4 } }).blur(Math.max(1, W / 640)), rel);
  return { rect: [x0 / W, (x0 + w) / W, y0 / H, (y0 + h) / H] as Box, src: rel };
}

/** Warm glow (screen) around each lamp shade; identical pool per option, as the spec requires. */
async function makeLight(key: 'lo' | 'hi', slotId: string, t: TempSlot) {
  if (!t.glow?.length) return null;
  const W = WIDTHS[key];
  const H = Math.round((W * 9) / 16);
  const u0 = Math.max(0, Math.min(...t.glow.map((g) => g[0] - g[2])));
  const u1 = Math.min(1, Math.max(...t.glow.map((g) => g[0] + g[2])));
  const v0 = Math.max(0, Math.min(...t.glow.map((g) => g[1] - g[2] * (16 / 9))));
  const v1 = Math.min(1, Math.max(...t.glow.map((g) => g[1] + g[2] * (16 / 9))));
  const x0 = Math.floor(u0 * W);
  const y0 = Math.floor(v0 * H);
  const w = Math.ceil(u1 * W) - x0;
  const h = Math.ceil(v1 * H) - y0;
  const out = Buffer.alloc(w * h * 4);
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      const u = (x0 + x + 0.5) / W;
      const v = (y0 + y + 0.5) / H;
      let a = 0;
      for (const [gu, gv, gr] of t.glow) {
        const d = Math.hypot(u - gu, (v - gv) * (9 / 16)) / gr;
        a = Math.max(a, Math.exp(-d * d * 2.2) * 0.42);
      }
      const i = (y * w + x) * 4;
      out[i] = 255;
      out[i + 1] = 206;
      out[i + 2] = 148;
      out[i + 3] = Math.round(a * 255);
    }
  const rel = `${roomDir}/slots/${slotId}/1.light.${W}`;
  await encode(sharp(out, { raw: { width: w, height: h, channels: 4 } }), rel);
  return { rect: [x0 / W, (x0 + w) / W, y0 / H, (y0 + h) / H] as Box, src: rel };
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
    for (const key of ['lo', 'hi'] as const) {
      const layers = await makeSlotLayers(bases[key]!, key, slot.id, t, colors);
      const shadow = slot.has_shadow ? await makeShadow(key, slot.id, t, slot.placement) : null;
      const light = slot.has_light ? await makeLight(key, slot.id, t) : null;
      if (key === 'lo') {
        entry.product = layers ? { rect: layers.rect, src: slot.options.map((_, n) => `${roomDir}/slots/${slot.id}/${n + 1}.product`) } : null;
        entry.shadow = shadow ? { rect: shadow.rect, src: slot.options.map(() => `${roomDir}/slots/${slot.id}/1.shadow`) } : null;
        entry.light = light ? { rect: light.rect, src: slot.options.map(() => `${roomDir}/slots/${slot.id}/1.light`) } : null;
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
