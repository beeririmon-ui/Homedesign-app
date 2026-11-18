/**
 * MOCK4 (2026-11-18): a room of the tour built from a render folder's own layers (the bedroom MB0 and the bathroom B2,
 * stage one with FB10), behind HD_PUBLIC=0. The same engine as the living room (web/src/tour/): the base, then every
 * product in z order with its shadow under it (multiply), then the light (screen). Reads tools/tour/<room>.<style>.json
 * and the folder's layers/manifest.json; never changes either. Writes:
 *
 *   .generated/tour.<room>.<style>.json      the room as the tour's engine reads it (the shape of tools/make-tour.ts's),
 *                                            with what is new here: the light, the atlas pages, the cards' sheet, the
 *                                            sample slot, the furniture that is not sold, and the rights box (×1 only)
 *   web/public/media/tour/<room>/<style>/    the base at two widths (`lo` a phone's, `hi` the layers' own); the sample
 *                                            slot's options one file each (the wheel swaps them); every other product,
 *                                            its shadow and the light packed in atlas pages (two files a room instead
 *                                            of forty: the Artifact holds 255 files a publish); the cards' sheet
 *
 * The rest of a layer's rules are tools/make-tour.ts's: a layer is cut to its slot's rectangle (its alpha and wherever
 * its shadow darkens, 8 px round it), rounded per width exactly as the engine rounds it, the product near-lossless and
 * the shadow lossless. Before anything is written, the source layers composed in this order by the manifest's own
 * formula must give the folder's approved composite (mb0-defaults.png, b2-defaults.png) to the pixel.
 *
 * A product's name and price are the shop's own record of its card (.generated/catalog.tour-rooms.full.json, the same
 * pricing path as every product; npm run tour builds it first). A card the shop cannot price yet keeps its slot's name.
 */
import sharp, { type OverlayOptions } from 'sharp';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { basename, join } from 'node:path';
import { GENERATED, MEDIA_OUT, repoPath, sitePath } from './lib/paths';

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
};
type Cfg = {
  room: string;
  style: string;
  name_he: string;
  layers: string;
  manifest: string;
  truth: string;
  plan: string;
  camera: string;
  room_plan: string;
  slots_file: string;
  sample: string;
  avoid: string | null;
  zoom: boolean;
  slots: Record<string, SlotCfg>;
  variant_cards?: Record<string, string>;
};
type Light = { file: string; blend: string; slot?: string; product?: string };
type MLayer = { slot: string; product: string; z: number; layer: string; shadow: string; card?: string; sold?: boolean; fixed?: boolean };
type MVariant = { slot: string; product: string; default: boolean; layer: string; shadow: string; card?: string };
type Manifest = {
  id: string;
  canvas: [number, number];
  frame_box: [number, number, number, number];
  layers: MLayer[];
  light: Light | Light[];
  variants: MVariant[];
};

const CFG = process.argv[2] ?? 'tools/tour/master.warm-modern.json';
const read = <T>(p: string): T => JSON.parse(readFileSync(p, 'utf8')) as T;
const fail = (msg: string): never => {
  console.error(`make-tour-room: ${msg}`);
  process.exit(1);
};
const c = read<Cfg>(sitePath(CFG));
const dir = repoPath(c.layers);
const m = read<Manifest>(join(dir, c.manifest));
const [W, H] = m.canvas;
const sha = (f: string) => createHash('sha256').update(readFileSync(f)).digest('hex');

// ---------- the order: z, and the manifest's own order where two share a z (checked against the composite below) ----------
const layers = m.layers
  .map((l, i) => ({ l, i }))
  .sort((a, b) => a.l.z - b.l.z || a.i - b.i)
  .map((x) => x.l);
for (const l of layers) if (!c.slots[l.slot]) fail(`${CFG} has no slot ${l.slot}`);
for (const id of Object.keys(c.slots)) if (!layers.some((l) => l.slot === id)) fail(`${CFG} names slot ${id}, which the manifest does not compose`);
const lightEntries = (Array.isArray(m.light) ? m.light : [m.light]).map((x) => {
  if (x.blend !== 'screen') fail(`light ${x.file} is ${x.blend}, not screen`);
  // a light is its product's: it goes with that slot (the slot the manifest names, or the layer of its product)
  const slot = x.slot ?? layers.find((l) => l.product === x.product)?.slot ?? fail(`light ${x.file}: no slot`);
  return { file: x.file, slot };
});
const lights = lightEntries.map((x) => x.file);
const sampleOpts: { product: string; layer: string; shadow: string; card: string | null }[] = [];
{
  const d = layers.find((l) => l.slot === c.sample) ?? fail(`no sample slot ${c.sample}`);
  sampleOpts.push({ product: d.product, layer: d.layer, shadow: d.shadow, card: c.slots[c.sample]!.card });
  for (const v of m.variants.filter((x) => x.slot === c.sample && !x.default))
    sampleOpts.push({
      product: v.product,
      layer: v.layer,
      shadow: v.shadow,
      card: c.variant_cards?.[v.product] ?? (v.card ? basename(v.card, '.json') : c.slots[c.sample]!.card),
    });
  if (sampleOpts.length !== 3) fail(`the sample slot ${c.sample} has ${sampleOpts.length} options, not 3`);
}

// ---------- raw pixels ----------
const cache = new Map<string, Buffer>();
const raw = async (f: string, ch: 1 | 3 | 4): Promise<Buffer> => {
  const k = `${f}:${ch}`;
  let b = cache.get(k);
  if (b) return b;
  const img = sharp(join(dir, f));
  const pipe = ch === 4 ? img.ensureAlpha() : ch === 3 ? img.removeAlpha().toColourspace('srgb') : img.removeAlpha().toColourspace('b-w');
  const { data, info } = await pipe.raw().toBuffer({ resolveWithObject: true });
  if (info.width !== W || info.height !== H || info.channels !== ch) fail(`${f} is ${info.width}×${info.height}×${info.channels}, not ${W}×${H}×${ch}`);
  cache.set(k, (b = data));
  return b;
};

// ---------- the gate: the source layers in this order give the approved composite, to the pixel ----------
{
  const out = new Float64Array(W * H * 3);
  const plate = await raw('plate.png', 3);
  for (let i = 0; i < out.length; i++) out[i] = plate[i]!;
  for (const l of layers) {
    const p = await raw(l.layer, 4);
    const s = await raw(l.shadow, 1);
    for (let i = 0; i < W * H; i++) {
      const a = p[i * 4 + 3]! / 255;
      const sh = s[i]! / 255;
      if (a === 0 && sh === 1) continue;
      for (let k = 0; k < 3; k++) out[i * 3 + k] = Math.round(out[i * 3 + k]! * sh * (1 - a) + p[i * 4 + k]! * a);
    }
  }
  for (const f of lights) {
    const L = await raw(f, 3);
    for (let i = 0; i < out.length; i++) if (L[i]) out[i] = 255 - Math.round(((255 - out[i]!) * (255 - L[i]!)) / 255);
  }
  const truth = await raw(c.truth, 3);
  let bad = 0;
  for (let i = 0; i < out.length; i++) if (out[i] !== truth[i]) bad++;
  if (bad) fail(`the layers in this order miss ${c.truth} on ${bad} channel values`);
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

// ---------- the plan: each product's depth along the camera's axis (the mask's code, the reveal's plane) ----------
type Plan = {
  cameras: { id: string; loc: [number, number, number]; yaw_deg_left: number; u0: number; v0: number }[];
  rooms: { id: string; x: [number, number]; y: [number, number]; h: number }[];
};
const plan = read<Plan>(repoPath(c.plan));
const cam = plan.cameras.find((x) => x.id === c.camera) ?? fail(`no camera ${c.camera}`);
const box = plan.rooms.find((r) => r.id === c.room_plan) ?? fail(`no room ${c.room_plan}`);
const yaw = (cam.yaw_deg_left * Math.PI) / 180;
const fwd: [number, number] = [-Math.sin(yaw), -Math.cos(yaw)];
const depthOf = (x: number, y: number) => +((x - cam.loc[0]) * fwd[0] + (y - cam.loc[1]) * fwd[1]).toFixed(3);
type SlotsFile = { slots: { id: string; name_he: string; plan_m?: Record<string, unknown> }[] };
const slotsFile = read<SlotsFile>(repoPath(c.slots_file));
const mid = (r: unknown): number | null => (Array.isArray(r) && typeof r[0] === 'number' ? ((r[0] as number) + (r[1] as number)) / 2 : null);
function planDepth(id: string): number | null {
  const p = slotsFile.slots.find((s) => s.id === id)?.plan_m;
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
  return depthOf(pts.reduce((a, q) => a + q[0], 0) / pts.length, pts.reduce((a, q) => a + q[1], 0) / pts.length);
}

// ---------- the shop's record of a card ----------
type Shop = {
  id: string;
  card_id?: string;
  name_he: string;
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
  const suffix = product.startsWith(`${card}-`) ? product.slice(card.length + 1) : '';
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
const REL = `tour/${c.room}/${c.style}`;
const OUT = join(MEDIA_OUT, REL);
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
  let img = sharp(join(dir, f));
  img = kind === 'product' ? img.ensureAlpha() : kind === 'shadow' ? img.removeAlpha().toColourspace('srgb') : img.removeAlpha();
  img = img.extract(cut(r));
  if (Wt !== W) img = img.resize(size);
  const { data, info } = await img.raw().toBuffer({ resolveWithObject: true });
  if (info.width !== size.width || info.height !== size.height) fail(`${f}: ${info.width}×${info.height} at ${Wt}, not ${size.width}×${size.height}`);
  return { data, w: info.width, h: info.height, ch: info.channels as 3 | 4 };
}
/** shelf packing in pages of at most `max` × `max`, 2 px apart; returns where each piece goes */
function pack(sizes: { w: number; h: number }[], max: number): { page: number; x: number; y: number }[] {
  const order = sizes.map((s, i) => ({ ...s, i })).sort((a, b) => b.h - a.h || b.w - a.w);
  const at: { page: number; x: number; y: number }[] = [];
  let page = 0;
  let x = 0;
  let y = 0;
  let row = 0;
  for (const s of order) {
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
  pieces: { data: Buffer; w: number; h: number; ch: 3 | 4 }[],
  at: { page: number; x: number; y: number }[],
  page: number,
  ch: 3 | 4,
): Promise<sharp.Sharp> {
  const mine = pieces.map((p, i) => ({ p, a: at[i]! })).filter((x) => x.a.page === page);
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

// ---------- build (cached by a stamp of the inputs and this file) ----------
const sources = ['plate.png', c.truth, ...layers.flatMap((l) => [l.layer, l.shadow]), ...sampleOpts.flatMap((o) => [o.layer, o.shadow]), ...lights, c.manifest];
const stamp = createHash('sha256')
  .update(
    JSON.stringify({
      c,
      tool: readFileSync(new URL(import.meta.url), 'utf8'),
      sources: [...new Set(sources)].map((f) => [f, statSync(join(dir, f)).size, statSync(join(dir, f)).mtimeMs]),
    }),
  )
  .digest('hex')
  .slice(0, 16);
const STAMP = join(OUT, 'stamp.json');
type AtlasRef = [number, number, number, number, number];
type Built = {
  rects: Record<string, Px>;
  alpha: Record<string, Px>;
  lights: Px[];
  atlas: Record<number, { product: AtlasRef[]; shadow: AtlasRef[]; light: AtlasRef[]; pages: { product: [number, number][]; shadow: [number, number][] } }>;
  cards: { at: Record<string, [number, number, number, number]>; sheet: [number, number] };
  shadowOf: number[];
};
let built: Built;
const others = layers.filter((l) => l.slot !== c.sample);
const cached = existsSync(STAMP) ? read<{ stamp: string; built: Built }>(STAMP) : null;
if (cached?.stamp === stamp) built = cached.built;
else {
  rmSync(OUT, { recursive: true, force: true });
  mkdirSync(OUT, { recursive: true });
  const rects: Record<string, Px> = {};
  const alpha: Record<string, Px> = {};
  for (const l of others) {
    rects[l.slot] = await region([l]);
    alpha[`${l.slot}:1`] = await alphaBox(l.layer);
  }
  rects[c.sample] = await region(sampleOpts);
  for (const [n, o] of sampleOpts.entries()) alpha[`${c.sample}:${n + 1}`] = await alphaBox(o.layer);
  const lightRects = await Promise.all(lights.map(lightRegion));
  // the sample's shadows: one file for options that share it to the byte (the throw's three, the linen towel's two)
  const shadowOf: number[] = [];
  const shaOf = sampleOpts.map((o) => sha(join(dir, o.shadow)));
  sampleOpts.forEach((_, n) => shadowOf.push(shaOf.indexOf(shaOf[n]!) + 1));
  const atlas: Built['atlas'] = {};
  for (const Wt of new Set(Object.values(WIDTHS))) {
    // every other product and its shadow, and the light, in pages no wider than the composition (the engine already
    // needs a texture that wide, so every card that runs the tour holds one)
    const prods = await Promise.all(others.map((l) => piece(l.layer, 'product', rects[l.slot]!, Wt)));
    const shads = [
      ...(await Promise.all(others.map((l) => piece(l.shadow, 'shadow', rects[l.slot]!, Wt)))),
      ...(await Promise.all(lights.map((f, i) => piece(f, 'light', lightRects[i]!, Wt)))),
    ];
    const pa = pack(prods, Wt);
    const sa = pack(shads, Wt);
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
    atlas[Wt] = {
      product: prods.map((p, i) => [pa[i]!.page + 1, pa[i]!.x, pa[i]!.y, p.w, p.h]),
      shadow: others.map((_, i) => [sa[i]!.page + 1, sa[i]!.x, sa[i]!.y, shads[i]!.w, shads[i]!.h]),
      light: lights.map((_, i) => {
        const k = others.length + i;
        return [sa[k]!.page + 1, sa[k]!.x, sa[k]!.y, shads[k]!.w, shads[k]!.h];
      }),
      pages,
    };
    // the sample's options, a file each (the wheel swaps them)
    for (const [n, o] of sampleOpts.entries()) {
      const r = rects[c.sample]!;
      const t = tierRect(r, Wt);
      const size = { width: t.x1 - t.x0, height: t.y1 - t.y0 };
      const lay = sharp(join(dir, o.layer)).ensureAlpha().extract(cut(r));
      mkdirSync(join(OUT, `slots/${c.sample}`), { recursive: true });
      await (Wt === W ? lay : lay.resize(size))
        .webp({ nearLossless: true, quality: 60, effort: 5 })
        .toFile(join(OUT, `slots/${c.sample}/${n + 1}.product.${Wt}.webp`));
      if (shadowOf[n] !== n + 1) continue;
      const sh = sharp(join(dir, o.shadow)).removeAlpha().toColourspace('srgb').extract(cut(r));
      await (Wt === W ? sh : sh.resize(size)).webp({ lossless: true, effort: 5 }).toFile(join(OUT, `slots/${c.sample}/${n + 1}.shadow.${Wt}.webp`));
    }
  }
  // the base: the plate, byte for byte (the folder's own), at both widths
  for (const Wt of new Set(Object.values(WIDTHS))) {
    const b = sharp(join(dir, 'plate.png')).removeAlpha();
    // the house's own base setting (tools/make-house.ts BASE_WEBP_Q: lossy q90 shows on plaster at 1:1)
    await (Wt === W ? b : b.resize({ width: Wt })).webp({ quality: 95, effort: 5 }).toFile(join(OUT, `base.${Wt}.webp`));
  }
  // the cards: every product on its own (its layer trimmed to it, FB1), one sheet for the room
  const cardPieces: { data: Buffer; w: number; h: number; ch: 4 }[] = [];
  const cardSrc: [string, string][] = [
    ...others.filter((l) => !c.slots[l.slot]!.fixed).map((l): [string, string] => [`${l.slot}:1`, l.layer]),
    ...sampleOpts.map((o, n): [string, string] => [`${c.sample}:${n + 1}`, o.layer]),
  ];
  for (const [, f] of cardSrc) {
    const a = await alphaBox(f);
    const pad = Math.round(Math.max(a.x1 - a.x0, a.y1 - a.y0) * 0.03) + 2;
    const left = Math.max(0, a.x0 - pad);
    const top = Math.max(0, a.y0 - pad);
    const bx = { left, top, width: Math.min(W, a.x1 + 1 + pad) - left, height: Math.min(H, a.y1 + 1 + pad) - top };
    const k = Math.min(1, CARD / Math.max(bx.width, bx.height));
    const { data, info } = await sharp(join(dir, f))
      .ensureAlpha()
      .extract(bx)
      .resize({ width: Math.max(1, Math.round(bx.width * k)), height: Math.max(1, Math.round(bx.height * k)) })
      .raw()
      .toBuffer({ resolveWithObject: true });
    cardPieces.push({ data, w: info.width, h: info.height, ch: 4 });
  }
  const ca = pack(cardPieces, 2048);
  if (ca.some((a) => a.page)) fail('the cards do not fit one sheet');
  const cs = await sheet(cardPieces, ca, 0, 4);
  const cmeta = await cs.metadata();
  await cs.webp({ quality: 88, alphaQuality: 100, effort: 5 }).toFile(join(OUT, `cards.${CARD}.webp`));
  built = {
    rects,
    alpha,
    lights: lightRects,
    atlas,
    cards: { at: Object.fromEntries(cardPieces.map((p, i) => [cardSrc[i]![0], [ca[i]!.x, ca[i]!.y, p.w, p.h]])), sheet: [cmeta.width!, cmeta.height!] },
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
  kx: 0.6667,
  ky: 1.1852,
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
const placeholder = `data:image/webp;base64,${(await sharp(join(dir, 'plate.png')).removeAlpha().resize({ width: 48 }).webp({ quality: 60, effort: 6 }).toBuffer()).toString('base64')}`;
const slotName = (id: string) => c.slots[id]!.name_he ?? slotsFile.slots.find((s) => s.id === id)?.name_he ?? fail(`no name for slot ${id}`);
// the mask's code is a product's depth × 40: two products a code apart are told apart (a nudge of 2.5 cm where they tie)
const codes = new Set<number>();
const depth = (id: string): number => {
  let d = planDepth(id) ?? c.slots[id]!.depth_m ?? fail(`no depth for slot ${id}: give it depth_m`);
  while (codes.has(Math.round(d * 40))) d += 0.025;
  codes.add(Math.round(d * 40));
  return +d.toFixed(3);
};
const cardsSrc = `${REL}/cards.${CARD}`;
const option = (slot: string, n: number, product: string, card: string | null) => {
  const p = card ? shop.get(card) : undefined;
  const at = built.cards.at[`${slot}:${n}`]!;
  const a = built.alpha[`${slot}:${n}`]!;
  return {
    position: n,
    card: { src: cardsSrc, w: at[2], h: at[3], source: 'layer' as const, sprite: at, sheet: built.cards.sheet },
    box: uv({ ...a, x1: a.x1 + 1, y1: a.y1 + 1 }),
    product_id: p?.id ?? null,
    card_id: card,
    name_he: p ? shopName(p, product, card!) : null,
    price_agorot: p?.price_agorot ?? null,
    price_provisional: p?.price_provisional ?? false,
    available: !!p && p.availability.status === 'available',
    dims_he: p ? dimsHe(p.dimensions_cm, c.slots[slot]!.kind) : null,
    set: false,
  };
};
const ordered = layers.map((l) => l.slot);
const at = (Wt: number) => built.atlas[Wt]!;
const slots = ordered.map((id, i) => {
  const cfg = c.slots[id]!;
  const l = layers.find((x) => x.slot === id)!;
  const sample = id === c.sample;
  const k = others.findIndex((x) => x.slot === id);
  const opts = sample ? [] : cfg.fixed ? [] : [option(id, 1, l.product, cfg.card)];
  if (sample) sampleOpts.forEach((o, n) => opts.push(option(id, n + 1, o.product, o.card)));
  const a0 = built.alpha[`${id}:1`]!;
  return {
    id,
    name_he: slotName(id),
    z: l.z,
    rect: uv(built.rects[id]!),
    depth_m: depth(id),
    kind: cfg.kind,
    order_a: i + 1,
    hero: !!cfg.hero,
    ground: cfg.kind === 'floor' || cfg.kind === 'surface',
    anchors: (cfg.anchors ?? [[0.5, 0.5]]).map(([x, y]) => [+((a0.x0 + (a0.x1 - a0.x0) * x) / W).toFixed(4), +((a0.y0 + (a0.y1 - a0.y0) * y) / H).toFixed(4)]),
    src: `${REL}/slots/${id}`,
    fixed: !!cfg.fixed,
    closeup: cfg.closeup ?? true,
    shadows: sample ? built.shadowOf : undefined,
    // the atlas: [page, x, y, w, h] of this product and of its shadow, per width (absent: a file per option)
    atlas: sample ? undefined : Object.fromEntries(Object.values(WIDTHS).map((Wt) => [Wt, { product: at(Wt).product[k]!, shadow: at(Wt).shadow[k]! }])),
    // a fixed piece of furniture is composed like any layer and has no option to show: one, with no card
    options: cfg.fixed
      ? [
          {
            position: 1,
            card: { src: cardsSrc, w: 1, h: 1, source: 'layer' as const, sprite: [0, 0, 1, 1], sheet: built.cards.sheet },
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
});
const avoid = c.avoid ? uv(built.alpha[`${c.avoid}:1`]!) : null;
const data = {
  room: c.room,
  style: c.style,
  name_he: 'מודרני חם',
  room_he: c.name_he,
  source: m.id,
  native: W,
  widths: { lo: Math.min(WIDTHS.lo, W), hi: W },
  card_width: CARD,
  aspect: W / H,
  mobile_center_u: 0.5,
  base: { src: `${REL}/base`, widths: [WIDTHS.lo, W], placeholder, formats: ['webp'] },
  camera,
  cover: 0,
  sample: c.sample,
  zoom: c.zoom,
  avoid,
  atlas: Object.fromEntries(
    Object.values(WIDTHS).map((Wt) => [
      Wt,
      {
        product: at(Wt).pages.product.map(([w, h], i) => ({ src: `${REL}/atlas.product.${i + 1}`, w, h })),
        shadow: at(Wt).pages.shadow.map(([w, h], i) => ({ src: `${REL}/atlas.shadow.${i + 1}`, w, h })),
      },
    ]),
  ),
  lights: lights.map((f, i) => ({
    id: basename(f, '.png'),
    slot: lightEntries[i]!.slot,
    rect: uv(built.lights[i]!),
    atlas: Object.fromEntries(Object.values(WIDTHS).map((Wt) => [Wt, at(Wt).light[i]!])),
  })),
  for_sale: slots.filter((s) => !s.fixed).length,
  slots,
};
// how much of the frame the products fill (the counter's line): their alpha boxes would overstate it, so it is left
// out here (0) and the page shows the count alone
mkdirSync(GENERATED, { recursive: true });
const outFile = join(GENERATED, `tour.${c.room}.${c.style}.json`);
writeFileSync(outFile, JSON.stringify(data));

const kb = (f: string) => statSync(join(OUT, f)).size / 1024;
const lo = WIDTHS.lo;
const loFiles = [
  `base.${lo}.webp`,
  ...data.atlas[lo]!.product.map((p) => `${basename(p.src)}.${lo}.webp`),
  ...data.atlas[lo]!.shadow.map((p) => `${basename(p.src)}.${lo}.webp`),
  `slots/${c.sample}/1.product.${lo}.webp`,
  `slots/${c.sample}/1.shadow.${lo}.webp`,
  `cards.${CARD}.webp`,
];
const unsold = slots.filter((s) => !s.fixed).flatMap((s) => s.options.filter((o) => !o.product_id).map((o) => `${s.id} ${o.position}`));
console.log(
  `tour ${c.room}/${c.style}: ${m.id}; ${slots.length} layers (${data.for_sale} for sale, ${slots.length - data.for_sale} fixed), ${lights.length} light; ` +
    `the order gives ${c.truth} to the pixel; a phone's first load ${loFiles.reduce((n, f) => n + kb(f), 0).toFixed(0)} KB in ${loFiles.length} files ` +
    `(atlas pages ${data.atlas[lo]!.product.length}+${data.atlas[lo]!.shadow.length}); ${unsold.length} not priced by the shop yet (${unsold.join(', ')}) → ${outFile}`,
);
