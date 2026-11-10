/**
 * S10: a house of the room engine (DIR2: every style its own house in the tool) from its manifest,
 * tools/house/<room>.<style>.json. Writes:
 *
 *   .generated/house.<room>.<style>.json   the house as the engine reads it (a lazy chunk of the room page): its scene
 *                                          (layers, camera, the slot's silhouette), its room (the slots on the wheel),
 *                                          the sets on the wheel with the SKU of every piece, and the shop's records
 *                                          of those products (public catalog fields only: no card id, no supplier)
 *   web/public/media/house/<room>/<style>/  the layers, AVIF + WebP at the room's widths (the layers WebP only:
 *                                          lossless alpha), a thumbnail per set for the wheel, and a flat depth map
 *
 * The layers come from the render folder (`pilot`): `layers_dir`/ when render-agent's export is there (base.png,
 * cushions-set-X.png, optional cushions-set-X-shadow.png, manifest.json), else the approved display files themselves:
 * the default set's composite as the base and, per set, its composite cut to the one rectangle where the sets differ
 * (the swap changes nothing outside it: measured here and printed). Both are the approved v3c pixels.
 *
 * The sets and their order are checked against the designer's selection (data/selections/…): the same sets, the same
 * cards, the default first. A product the shop does not sell (no price, a draft card) stays in its set without a
 * price: it is listed, and never offered for sale.
 */
import sharp from 'sharp';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { expandOptions, type CatalogRoom, type CatalogSlot, type PublicCatalog, type PublicProduct } from '@hd/shared';
import { publicId } from '@hd/shared/product-url';
import { GENERATED, MEDIA_OUT, repoPath, sitePath } from './lib/paths';

type Point = { product: string; option?: Record<string, string> };
type Manifest = {
  room: string;
  style: string;
  selection: string;
  status_he: string;
  alt_he: string;
  frame: string;
  mobile_center_u: number;
  pilot: string;
  approved: { base: string; composites: Record<string, string> };
  layers_dir: string;
  slot: { id: string; depth: number };
  sets: { id: string; label_he: string; points: Point[] }[];
};
type Selection = { slots: Record<string, { picks: { set_id?: string; items?: string[] }[] }> };
type Box = [number, number, number, number];

const MANIFEST = process.argv[2] ?? 'tools/house/living-room.warm-modern.json';
const m = JSON.parse(readFileSync(sitePath(MANIFEST), 'utf8')) as Manifest;
const read = <T>(p: string): T => JSON.parse(readFileSync(p, 'utf8')) as T;
const fail = (msg: string): never => {
  console.error(`make-house: ${msg}`);
  process.exit(1);
};

// ---------- the sets agree with the designer's selection ----------
const picks = read<Selection>(repoPath(m.selection)).slots[m.slot.id]?.picks ?? [];
const selIds = picks.map((p) => p.set_id);
if (selIds.join() !== m.sets.map((s) => s.id).join()) fail(`sets ${m.sets.map((s) => s.id)} differ from ${m.selection} (${selIds})`);
for (const [i, s] of m.sets.entries()) {
  const cards = (picks[i]!.items ?? []).map((x) => x.split(' ')[0]);
  if (cards.join() !== s.points.map((p) => p.product).join()) fail(`set ${s.id}: cards ${s.points.map((p) => p.product)} differ from the selection (${cards})`);
}

// ---------- the pieces: the shop's records (the story catalog, the same pricing path) ----------
const storyCatalog = read<PublicCatalog>(join(GENERATED, 'catalog.story.public.json'));
const site = read<PublicCatalog>(join(GENERATED, 'catalog.public.json'));
const byId = new Map(storyCatalog.products.map((p) => [p.id, p]));
const names = read<{ names_he?: Record<string, string> }>(repoPath('data/story/story.json')).names_he ?? {};
const used = new Map<string, PublicProduct>();
type Piece = { product_id: string | null; variant_id: string | null; name_he: string; option_he: string | null };
const sets = m.sets.map((s, i) => {
  const items: Piece[] = s.points.map((pt) => {
    const p = byId.get(publicId(pt.product));
    if (!p) return { product_id: null, variant_id: null, name_he: names[pt.product] ?? 'פריט בסט', option_he: null };
    used.set(p.id, p);
    if (!p.options) return { product_id: p.id, variant_id: p.variants[0]!.id, name_he: p.name_he, option_he: null };
    const o = expandOptions(p.id, p.options);
    const room = o.skus.find((x) => x.in_room)!;
    const want = { ...room.values, ...pt.option };
    for (const [k, v] of Object.entries(pt.option ?? {}))
      if (!o.axes.find((a) => a.id === k)?.values.some((x) => x.id === v)) fail(`set ${s.id}: ${pt.product} has no ${k}=${v}`);
    const sku = o.skus.find((x) => o.axes.every((a) => x.values[a.id] === want[a.id]));
    if (!sku) return fail(`set ${s.id}: ${pt.product} sells no SKU ${JSON.stringify(want)}`);
    const option_he = o.axes.map((a) => a.values.find((v) => v.id === sku.values[a.id])!.label_he).join(', ');
    return { product_id: p.id, variant_id: sku.variant_id, name_he: p.name_he, option_he };
  });
  return { position: i + 1, id: s.id, label_he: s.label_he, items };
});

// ---------- layers ----------
const pilot = repoPath(m.pilot);
const W = 2720;
const H = 1530;
const lay = join(pilot, m.layers_dir);
const layered =
  existsSync(join(lay, 'manifest.json')) && existsSync(join(lay, 'base.png')) && m.sets.every((s) => existsSync(join(lay, `cushions-set-${s.id}.png`)));
const def = m.sets[0]!.id;
const files = {
  base: layered ? join(lay, 'base.png') : join(pilot, m.approved.composites[def]!),
  product: (id: string) => (layered ? join(lay, `cushions-set-${id}.png`) : join(pilot, m.approved.composites[id]!)),
  shadow: (id: string) => (layered && existsSync(join(lay, `cushions-set-${id}-shadow.png`)) ? join(lay, `cushions-set-${id}-shadow.png`) : null),
};
const sources = [files.base, ...m.sets.flatMap((s) => [files.product(s.id), files.shadow(s.id)].filter((x): x is string => !!x))];
const raw = async (f: string) => {
  const { data, info } = await sharp(f).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  if (info.width !== W || info.height !== H) fail(`${f} is ${info.width}×${info.height}, not ${W}×${H}`);
  return data;
};

/** the rectangle (px) the swap may touch: the layers' alpha, or where the approved composites differ from the default */
async function swapRect(): Promise<{ rect: [number, number, number, number]; outsideMax: number }> {
  let x0 = W;
  let y0 = H;
  let x1 = -1;
  let y1 = -1;
  const grow = (x: number, y: number) => {
    if (x < x0) x0 = x;
    if (x > x1) x1 = x;
    if (y < y0) y0 = y;
    if (y > y1) y1 = y;
  };
  if (layered) {
    // a set's region: its layer's alpha, and its shadow wherever the shadow darkens (an opaque multiply, white = none)
    for (const f of sources.slice(1)) {
      const d = await raw(f);
      const shadow = f.endsWith('-shadow.png');
      for (let i = 0; i < W * H; i++) {
        const k = i * 4;
        if (shadow ? d[k]! < 255 || d[k + 1]! < 255 || d[k + 2]! < 255 : d[k + 3]! > 0) grow(i % W, (i / W) | 0);
      }
    }
  } else {
    const base = await raw(files.base);
    for (const s of m.sets.slice(1)) {
      const d = await raw(files.product(s.id));
      for (let i = 0; i < W * H; i++) {
        const k = i * 4;
        if (Math.abs(d[k]! - base[k]!) > 2 || Math.abs(d[k + 1]! - base[k + 1]!) > 2 || Math.abs(d[k + 2]! - base[k + 2]!) > 2) grow(i % W, (i / W) | 0);
      }
    }
  }
  if (x1 < 0) fail('the sets do not differ anywhere');
  const pad = 8;
  const rect: [number, number, number, number] = [Math.max(0, x0 - pad), Math.min(W, x1 + 1 + pad), Math.max(0, y0 - pad), Math.min(H, y1 + 1 + pad)];
  // the check the cut stands on: outside the rectangle every set is the base (≤ 2 levels; 0 with layers by construction)
  let outsideMax = 0;
  if (!layered) {
    const base = await raw(files.base);
    for (const s of m.sets.slice(1)) {
      const d = await raw(files.product(s.id));
      for (let y = 0; y < H; y++)
        for (let x = 0; x < W; x++) {
          if (x >= rect[0] && x < rect[1] && y >= rect[2] && y < rect[3]) continue;
          const k = (y * W + x) * 4;
          outsideMax = Math.max(outsideMax, Math.abs(d[k]! - base[k]!), Math.abs(d[k + 1]! - base[k + 1]!), Math.abs(d[k + 2]! - base[k + 2]!));
        }
    }
  }
  return { rect, outsideMax };
}

const REL = `house/${m.room}/${m.style}/M0`;
const OUT = join(MEDIA_OUT, REL);
const BASE_WIDTHS = [1280, 1920, W];
const WIDTHS = { lo: 1920, hi: W };
const THUMB = 360;
const stamp = createHash('sha256')
  .update(JSON.stringify({ m, tool: readFileSync(new URL(import.meta.url), 'utf8'), sources: sources.map((f) => [f, statSync(f).size, statSync(f).mtimeMs]) }))
  .digest('hex')
  .slice(0, 16);
const STAMP = join(OUT, 'stamp.json');
const cached = existsSync(STAMP) ? read<{ stamp: string; rect: [number, number, number, number]; outsideMax: number }>(STAMP) : null;
const { rect, outsideMax } = cached?.stamp === stamp ? cached : await swapRect();
if (cached?.stamp !== stamp) {
  rmSync(OUT, { recursive: true, force: true });
  mkdirSync(OUT, { recursive: true });
  const out = (rel: string) => {
    const f = join(OUT, rel);
    mkdirSync(dirname(f), { recursive: true });
    return f;
  };
  const base = sharp(files.base).removeAlpha();
  for (const w of BASE_WIDTHS) {
    const r = base.clone().resize({ width: w });
    await r
      .clone()
      .avif({ quality: 52, effort: 4 })
      .toFile(out(`base/shell.${w}.avif`));
    await r
      .clone()
      .webp({ quality: 80, effort: 5 })
      .toFile(out(`base/shell.${w}.webp`));
  }
  const [x0, x1, y0, y1] = rect;
  const cut = { left: x0, top: y0, width: x1 - x0, height: y1 - y0 };
  for (const [i, s] of m.sets.entries()) {
    for (const [kind, f] of [
      ['product', files.product(s.id)],
      ['shadow', files.shadow(s.id)],
    ] as const) {
      if (!f) continue;
      const img = sharp(f).ensureAlpha().extract(cut);
      for (const w of Object.values(WIDTHS))
        await img
          .clone()
          .resize({ width: Math.round((cut.width * w) / W) })
          // a shadow multiplies the room: lossless, or the codec's noise near white would darken around the set
          .webp(kind === 'shadow' ? { lossless: true, effort: 5 } : { quality: 86, alphaQuality: 100, smartSubsample: true, effort: 5 })
          .toFile(out(`slots/${m.slot.id}/${i + 1}.${kind}.${w}.webp`));
    }
    // the wheel's card: the set on the sofa, from the approved display file (never a layer on its own)
    await sharp(join(pilot, m.approved.composites[s.id]!))
      .extract(cut)
      .resize({ width: THUMB, height: THUMB, fit: 'cover' })
      .webp({ quality: 80 })
      .toFile(out(`slots/${m.slot.id}/${i + 1}.thumb.${THUMB}.webp`));
  }
  // no depth render for this house yet: a flat map, so the zoom moves without parallax rather than with a wrong one
  await sharp({ create: { width: 480, height: 270, channels: 3, background: { r: 82, g: 82, b: 82 } } })
    .webp({ quality: 90 })
    .toFile(out('depth.480.webp'));
  writeFileSync(STAMP, JSON.stringify({ stamp, rect, outsideMax }));
}

// ---------- the slot's silhouette (the default set's outlines, frame coordinates) ----------
type Polys = Record<string, { origin: [number, number] } & Record<string, unknown>>;
const polys = read<Polys>(join(pilot, 'cushion-polys.json'));
const outlineOf = (id: string): [number, number][][] => {
  const o = polys[id]!.origin;
  return Object.entries(polys[id]!)
    .filter(([k]) => k !== 'origin')
    .map(([, pts]) => (pts as [number, number][]).map(([x, y]) => [+((o[0] + x) / W).toFixed(4), +((o[1] + y) / H).toFixed(4)] as [number, number]));
};
const all = m.sets.flatMap((s) => outlineOf(s.id)).flat();
const ring: Box = [Math.min(...all.map((p) => p[0])), Math.max(...all.map((p) => p[0])), Math.min(...all.map((p) => p[1])), Math.max(...all.map((p) => p[1]))];
const outline = outlineOf(def);
const area = (p: [number, number][]) => Math.abs(p.reduce((s, [u, v], i) => s + u * p[(i + 1) % p.length]![1] - p[(i + 1) % p.length]![0] * v, 0)) / 2;
// the resting mark: the middle of the biggest piece that is a cushion (the throw is split around the arm)
const big = [...outline].sort((a, b) => area(b) - area(a))[1]!;
const anchor: [number, number] = [+(big.reduce((s, p) => s + p[0], 0) / big.length).toFixed(4), +(big.reduce((s, p) => s + p[1], 0) / big.length).toFixed(4)];
const pad = 0.04;
const zoom: Box = [Math.max(0, ring[0] - pad), Math.min(1, ring[1] + pad), Math.max(0, ring[2] - pad), Math.min(1, ring[3] + pad)];
const frameRect: Box = [rect[0] / W, rect[1] / W, rect[2] / H, rect[3] / H];

// ---------- the scene and the room ----------
const nordicScene = read<{ hall: unknown }>(join(GENERATED, `scene.${m.room}.nordic.json`));
const src = (kind: string) => m.sets.map((_, i) => `${REL}/slots/${m.slot.id}/${i + 1}.${kind}`);
const scene = {
  room: m.room,
  style: m.style,
  frame: 'M0',
  temporary: false,
  source: layered ? `${m.layers_dir} (render-agent)` : 'v3c display files',
  aspect: W / H,
  mobile_center_u: m.mobile_center_u,
  widths: WIDTHS,
  // QA on the layers (2026-11-10, finding 1): composed at the files' own width, resampled once on display
  native: W,
  formats: ['avif', 'webp'],
  base: [{ id: 'shell', z: 0, blend: 'normal', src: `${REL}/base/shell`, widths: BASE_WIDTHS, temporary: false }],
  slots: {
    [m.slot.id]: {
      z: 55,
      depth: m.slot.depth,
      temporary: false,
      ring: ring.map((x) => +x.toFixed(4)),
      anchor,
      outline,
      product: { rect: frameRect, src: src('product') },
      shadow: m.sets.some((s) => files.shadow(s.id)) ? { rect: frameRect, src: src('shadow') } : null,
      light: null,
    },
  },
  depth: { src: `${REL}/depth.480`, width: 480 },
  hall: nordicScene.hall,
  transitions: {},
};
const living = site.rooms.find((r) => r.id === m.room)!;
const template = living.slots.find((s) => s.id === m.slot.id)!;
const slot: CatalogSlot = {
  ...template,
  has_shadow: !!scene.slots[m.slot.id]!.shadow,
  has_light: false,
  hotspot: { u: anchor[0], v: anchor[1], provisional: false, visible: true },
  zoom_frame: zoom.map((x) => +x.toFixed(4)) as Box,
  options: sets.map((s) => ({ position: s.position, product_id: null, placeholder: false, label_he: s.label_he, is_default: s.position === 1 })),
  on_hold: null,
};
const room: CatalogRoom = { ...living, style: m.style, frame: m.frame, base_layers: [{ id: 'shell', z: 0, blend: 'normal' }], light_slots: [], slots: [slot] };
const style = site.styles.find((s) => s.id === m.style);
const house = {
  style: m.style,
  name_he: style?.name_he ?? m.style,
  status_he: m.status_he,
  alt_he: m.alt_he,
  scene,
  room,
  sets: sets.map((s) => ({ ...s, thumb: `${REL}/slots/${m.slot.id}/${s.position}.thumb.${THUMB}.webp` })),
  products: [...used.values()],
};
mkdirSync(GENERATED, { recursive: true });
const outFile = join(GENERATED, `house.${m.room}.${m.style}.json`);
writeFileSync(outFile, JSON.stringify(house));
const kb = (f: string) => (existsSync(f) ? statSync(f).size / 1024 : 0);
const firstKb =
  kb(join(OUT, 'base/shell.1920.avif')) + kb(join(OUT, `slots/${m.slot.id}/1.product.1920.webp`)) + kb(join(OUT, `slots/${m.slot.id}/1.shadow.1920.webp`));
console.log(
  `house ${m.room}/${m.style}: ${layered ? `layers from ${m.layers_dir}/` : `the approved composites (no ${m.layers_dir}/ yet), the default set ${def} as the base`}; ` +
    `the swap rectangle ${rect.join(',')} px (outside it the sets differ by ≤ ${outsideMax} levels); ` +
    `${sets.length} sets, ${sets.reduce((n, s) => n + s.items.length, 0)} pieces (${sets.flatMap((s) => s.items).filter((x) => !x.product_id).length} not sold); ` +
    `the default composition ≈ ${firstKb.toFixed(0)} KB at 1920; ${(JSON.stringify(house).length / 1024).toFixed(1)} KB of data → ${outFile}`,
);
