/**
 * Layer 1, the story, as real routes (skeleton spec 2.0, "שלוש שכבות וזרימת האתר"; DIR1; briefs/site-interface-track
 * 2026-11-07, S1). One data file, data/story/story.json, makes:
 *   /story/                     the contents: every room × style, a frame where QA lets one in, a typographic tile else
 *   /story/<room>/<style>/      one page per declared pair: its frames (a dot per faithful product, "קנה את המראה",
 *                               "כל המוצרים בתמונה"), the way into "עצב בעצמך", and the same room in the other houses
 *                               (a style switch in the story is a cut between houses); a pair whose frames QA has not
 *                               let in is a typographic page, never an unapproved frame
 *   /test/story/                a redirect to the Nordic living room (the prototype's old address)
 * Built only without HD_PUBLIC=1 (web/vite.config.ts), until the frames pass "approved for the site" (G-ED).
 *
 *   tsx tools/build-catalog.ts --rooms=living-room --products=../data/story/story.json --out=story
 *   tsx tools/make-story.ts
 *
 * Reads
 *   data/story/story.json                 rooms, styles, pairs, frames, points, names; the QA records the gate reads
 *   qa/reports/…                          QA's records (tools/lib/qa-frames.ts reads both shapes; a newer one wins)
 *   .generated/catalog.story.full.json    every product of the frames, priced by the site's pricing code
 *   .generated/catalog.public.json        the site's own catalog: a product page link, and the slot in the room engine
 *   .cache/supplier-images/               the card photos already downloaded by tools/supplier-images.ts (no network)
 * Writes
 *   web/public/media/story/<room>/<style>/<frame>/{1280,1920,2720,m480,m800,m1224}.{avif,webp}
 *   web/public/media/story/products/<id>/<key>.{160,480,800}.webp
 *   web/story/index.html, web/story/<room>/<style>/index.html, web/test/story/index.html
 *   .generated/story.json                 the resolved pages (what each page's data block holds), for the evidence
 */
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import sharp from 'sharp';
import { formatIls } from '@hd/shared/money';
import { expandOptions, type FullCatalog, type FullProduct, type PublicCatalog } from '@hd/shared';
import { colorNameHe, materialsHe } from './lib/hebrew';
import { GENERATED, MEDIA_OUT, repoPath, sitePath } from './lib/paths';
import { cardOf, qaReader, type QaFrame, type QaState } from './lib/qa-frames';

type Box = [number, number, number, number];
type Point = {
  product: string;
  u: number;
  v: number;
  box: Box;
  by_eye: boolean;
  option?: Record<string, string>;
  option_label_he?: string;
  name_he?: string;
  phone_at?: [number, number];
  in_frame_he?: string;
};
type FrameSpec = {
  id: string;
  src: string;
  qa_key: string;
  role: 'wide' | 'second';
  u0?: number;
  v0?: number;
  phone_crop_u?: number;
  title_he?: string;
  line_he?: string;
  alt_he?: string;
  points: Point[];
};
type Pair = { concept_he: string; line_he?: string; tool: string | null; frames: FrameSpec[] };
type Story = {
  issue_he: string;
  qa_records: string[];
  allowed_states: QaState[];
  marks_he: Record<string, string>;
  tool_fallback: string;
  rooms: { id: string; n: string; name_he: string }[];
  styles: { id: string; name_he: string }[];
  names_he: Record<string, string>;
  pairs: Record<string, Pair>;
};
type Card = {
  id: string;
  slot: string;
  materials?: string[];
  dimensions_cm?: { width?: number | null; depth?: number | null; height?: number | null };
  colors: { dominant_hex: string };
  images: { urls: string[] };
  options?: { default_sku: string; skus: { id: string; values: Record<string, string>; image?: string }[] };
};
type Image = { src: string; srcset: string; w: number; h: number };
type Item = {
  id: string;
  frame: string;
  n: number;
  product: string;
  u: number;
  v: number;
  box: Box;
  /** QA's verdict on the product in this frame (G-ED.5): a dot only on "yes" */
  faithful: string;
  dot: boolean;
  /** the dot in the phone's 4:5 crop (u, v of the crop), or why there is none there (G-ED.17) */
  phone: { u: number; v: number } | null;
  phone_note: string | null;
  name_he: string;
  detail_he: string;
  price_he: string | null;
  price_agorot: number | null;
  variant_id: string | null;
  option_he: string | null;
  status: 'available' | 'unavailable' | 'unpriced';
  set_qty: number;
  notes_he: string[];
  image: Image | null;
  thumb: string | null;
  swatch: string;
  href: string | null;
  try_href: string | null;
};
type FrameOut = Required<Omit<FrameSpec, 'points'>> & {
  state: QaState;
  width: number;
  height: number;
  aspect: number;
  lqip: string;
  lqip_phone: string;
  srcset: string[];
  srcset_phone: string[];
  crop: [number, number];
  ver: string;
  items: Item[];
};
/** why a pair's frame is not on its page: QA's state, or the hotspot map still missing */
type Held = { id: string; qa_key: string; state: QaState | 'not_in_qa'; why_he: string };
type PageOut = { room: string; style: string; href: string; pair: Pair; frames: FrameOut[]; held: Held[] };

const read = <T>(p: string): T => JSON.parse(readFileSync(p, 'utf8')) as T;
const DATA = 'data/story/story.json';
const story = read<Story>(repoPath(DATA));
const qaOf = qaReader(story.qa_records);
for (const p of ['.generated/catalog.story.full.json', '.generated/catalog.public.json'])
  if (!existsSync(sitePath(p))) {
    console.error(`${p} is missing: run npm run catalog, then npm run story (it builds the story catalog first)`);
    process.exit(1);
  }
const catalog = read<FullCatalog>(sitePath('.generated/catalog.story.full.json'));
const site = read<PublicCatalog>(sitePath('.generated/catalog.public.json'));
const OUT = join(MEDIA_OUT, 'story');
const URL_BASE = '/media/story';
const WIDTHS = [1280, 1920, 2720];
const PHONE_WIDTHS = [480, 800, 1224];
const PHOTO_WIDTHS = [160, 480, 800];
/** G-ED.17 (proposal): the 4:5 crop at the full width of a 390 CSS phone; a product's visible part ≥ 44 × 24 CSS */
const PHONE_CSS = 390;
const MIN_LONG = 44;
const MIN_SHORT = 24;
const roomOf = (id: string) => story.rooms.find((r) => r.id === id)!;
const styleOf = (id: string) => story.styles.find((s) => s.id === id)!;
const pageHref = (room: string, style: string) => `/story/${room}/${style}/`;

// ---------- the cards and the slots' placement (the credit's defining size) ----------
function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    return statSync(p).isDirectory() ? walk(p) : p.endsWith('.json') ? [p] : [];
  });
}
const wanted = new Set(Object.values(story.pairs).flatMap((p) => p.frames.flatMap((f) => f.points.map((x) => x.product))));
const cards = new Map<string, Card>();
for (const p of walk(repoPath('data/products'))) {
  const c = read<Card>(p);
  if (wanted.has(c.id)) cards.set(c.id, c);
}
const livingSlots = read<{ slots: { id: string; placement: string; name_he: string }[] }>(repoPath('data/slots/living-room.json')).slots;
const placement = new Map<string, string>(livingSlots.map((s) => [s.id, s.placement]));
const hexOf = (card: Card): string | null => (/^#[0-9a-f]{6}$/i.test(card.colors?.dominant_hex ?? '') ? card.colors.dominant_hex : null);
/** a product without the designer's name nor the catalog's (no price yet, a draft card): named the catalog's way */
function nameFromCard(card: Card): string {
  const m = materialsHe(card.materials ?? [])[0];
  const hex = hexOf(card);
  const slot = livingSlots.find((s) => s.id === card.slot)?.name_he ?? card.slot;
  return `${slot}${m && !slot.includes(m) ? ` ${m}` : ''}${hex ? `, ${colorNameHe(hex)}` : ''}`;
}

// ---------- images ----------
const cacheOf = (url: string) => sitePath('.cache/supplier-images', `${createHash('sha256').update(url).digest('hex').slice(0, 24)}.bin`);
async function lqip(img: sharp.Sharp, w: number, h: number): Promise<string> {
  const buf = await img.clone().resize(w, h, { fit: 'fill' }).webp({ quality: 40 }).toBuffer();
  return `data:image/webp;base64,${buf.toString('base64')}`;
}
/** The card's photo for this point: the photo of the option the frame shows, else the card's first photo; cached only. */
async function photo(card: Card, skuImage: string | null): Promise<Image | null> {
  const url = [skuImage, card.images.urls[0]].find((u): u is string => !!u && /^https:\/\//.test(u) && existsSync(cacheOf(u)));
  if (!url) return null;
  const file = cacheOf(url);
  const key = createHash('sha256').update(url).digest('hex').slice(0, 10);
  const dir = join(OUT, 'products', card.id);
  mkdirSync(dir, { recursive: true });
  const img = sharp(readFileSync(file)).rotate();
  const meta = await img.metadata();
  const srcs: string[] = [];
  for (const w of PHOTO_WIDTHS) {
    const out = join(dir, `${key}.${w}.webp`);
    if (!existsSync(out)) await img.clone().resize({ width: w, withoutEnlargement: true }).webp({ quality: 78 }).toFile(out);
    srcs.push(`${URL_BASE}/products/${card.id}/${key}.${w}.webp ${Math.min(w, meta.width ?? w)}w`);
  }
  const w = Math.min(800, meta.width ?? 800);
  return { src: `${URL_BASE}/products/${card.id}/${key}.480.webp`, srcset: srcs.join(', '), w, h: Math.round((w * (meta.height ?? w)) / (meta.width ?? w)) };
}

// ---------- the credit (art direction §4.4–§4.5): material · the defining size · price ----------
function sizeHe(dims: FullProduct['dimensions_cm'] | Card['dimensions_cm'], place: string): string | null {
  const { width: w, depth: d, height: h } = dims ?? {};
  const x = (a: number, b: number) => `⁦${a}×${b}⁩ ס״מ`;
  // a textile or a floor piece is its two flat sides (a throw, a cushion, a rug); a wall piece its width and height
  if ((place === 'floor' || place === 'sofa') && w && (d || h)) return x(w, (d || h)!);
  if (place === 'wall' && w && h) return x(w, h);
  if (h) return `גובה ⁦${h}⁩ ס״מ`;
  if (w && d) return x(w, d);
  if (w) return `רוחב ⁦${w}⁩ ס״מ`;
  return null;
}
const sitePages = new Set(site.products.map((p) => p.id));
/** the room engine opens on the slot, with this product on the wheel, when the product is one of the slot's options */
function tryHref(tool: string | null, roomId: string, productId: string): string | null {
  if (!tool) return null;
  for (const s of site.rooms.find((r) => r.id === roomId)?.slots ?? []) {
    const o = s.options.find((x) => x.product_id === productId);
    if (o) return `${tool}?slot=${encodeURIComponent(s.id)}&option=${o.position}`;
  }
  return null;
}
/** reading order in a right-to-left page: top to bottom in bands, right to left inside a band */
const readingOrder = (a: Point, b: Point) => Math.floor(a.v / 0.25) - Math.floor(b.v / 0.25) || b.u - a.u;
/** QA's verdict, and whether it lets a dot on: "yes", or "yes, as the listing's … option" (the point names the option) */
const faithfulOf = (q: QaFrame, product: string): string => q.rows.find((r) => cardOf(r) === product)?.faithful ?? 'not checked';
const isFaithful = (verdict: string) => /^yes\b/.test(verdict);

/**
 * The phone's dot (G-ED.17): the crop [c0, c1] of the frame's width is shown 390 CSS wide. The product's part inside the
 * crop must be ≥ 44 CSS on its long side and ≥ 24 on its short side; the dot is the point (or the hand-placed
 * phone_at) when its whole target is in the crop, else the middle of the visible part, at the point's height.
 */
function phoneDot(pt: Point, c0: number, c1: number, fw: number, fh: number): { at: { u: number; v: number } | null; note: string | null } {
  const css = PHONE_CSS / ((c1 - c0) * fw);
  const [x0, x1, y0, y1] = pt.box;
  const a = Math.max(x0, c0);
  const b = Math.min(x1, c1);
  if (b <= a) return { at: null, note: 'מחוץ לחיתוך הטלפון' };
  const w = (b - a) * fw * css;
  const h = (y1 - y0) * fh * css;
  if (Math.max(w, h) < MIN_LONG || Math.min(w, h) < MIN_SHORT) return { at: null, note: `בטלפון ${Math.round(w)}×${Math.round(h)} CSS, פחות מ-${MIN_LONG}×${MIN_SHORT}` };
  const margin = 23 / PHONE_CSS;
  if (pt.phone_at) {
    const cu = (pt.phone_at[0] - c0) / (c1 - c0);
    if (cu < margin || cu > 1 - margin) throw new Error(`${pt.product}: the phone dot u ${pt.phone_at[0]} is not inside the crop ${c0.toFixed(3)}–${c1.toFixed(3)}`);
    return { at: { u: Math.round(cu * 10000) / 10000, v: pt.phone_at[1] }, note: null };
  }
  const cu = (pt.u - c0) / (c1 - c0);
  const u = cu >= margin && cu <= 1 - margin ? cu : ((a + b) / 2 - c0) / (c1 - c0);
  return { at: { u: Math.round(Math.min(1 - margin, Math.max(margin, u)) * 10000) / 10000, v: pt.v }, note: null };
}

async function itemOf(roomId: string, tool: string | null, frame: string, q: QaFrame, n: number, pt: Point, crop: [number, number], fw: number, fh: number): Promise<Item> {
  const card = cards.get(pt.product);
  if (!card) throw new Error(`${frame}: no product card ${pt.product}`);
  const p = catalog.products.find((x) => x.id === pt.product) ?? null;
  if (!p && !catalog.hidden.some((h) => h.id === pt.product)) throw new Error(`${pt.product} is not in the story catalog: npm run story builds it`);
  // the option the frame shows: the room's SKU with the point's values instead
  let optionHe: string | null = null;
  let optionSize: string | null = null;
  let skuImage: string | null = null;
  let price = p?.price_agorot ?? null;
  let variant = p?.variants[0]?.id ?? null;
  let available = p?.availability.status === 'available';
  const cardSku = card.options?.skus.find((s) => s.id === card.options!.default_sku);
  if (pt.option) {
    const o = p?.options ? expandOptions(p.id, p.options) : null;
    const want = { ...(cardSku?.values ?? {}), ...pt.option };
    const sku = o?.skus.find((s) => Object.entries(want).every(([k, v]) => s.values[k] === v));
    if (p && o && !sku) throw new Error(`${frame}: ${pt.product} has no option ${JSON.stringify(want)}`);
    if (p && !o) console.warn(`${frame}: ${pt.product}: the card's options did not reach the catalog (see build-catalog's warnings); the product's own price is used`);
    if (sku) {
      price = sku.price_agorot;
      variant = sku.variant_id;
      available &&= sku.available;
    }
    // the colour or the style of the option names it; a size goes to the credit
    const labelOf = (axis: string) => o?.axes.find((a) => a.id === axis)?.values.find((v) => v.id === pt.option![axis])?.label_he ?? null;
    const named = Object.keys(pt.option).find((a) => a !== 'size');
    optionHe = pt.option_label_he ?? (named ? labelOf(named) : null);
    const size = pt.option.size ? labelOf('size') : null;
    const m = size?.match(/^([\d.]+)×([\d.]+) ס["״]מ$/);
    optionSize = m ? `⁦${m[1]}×${m[2]}⁩ ס״מ` : size;
    skuImage = card.options?.skus.find((s) => Object.entries(want).every(([k, v]) => s.values[k] === v))?.image ?? null;
  } else skuImage = cardSku?.image ?? null;
  // the name: the option's own, else the product's (the designer's table), else the catalog's with the option's colour
  const own = pt.name_he ?? story.names_he[pt.product] ?? null;
  let name = own ?? p?.name_he ?? nameFromCard(card);
  if (!own && optionHe) name = name.includes(', ') ? `${name.slice(0, name.lastIndexOf(', '))}, ${optionHe}` : `${name} — ${optionHe}`;
  // an option that is a style (a curtain's heading) is said in the credit: the frame shows that one
  const styleNote = pt.option?.style && optionHe ? `בתמונה: האפשרות "${optionHe}".` : null;
  const place = placement.get(card.slot) ?? 'surface';
  const priceHe = price !== null ? formatIls(price) : null;
  const material = p ? (p.materials_he[0] ?? null) : (materialsHe(card.materials ?? [])[0] ?? null);
  const detail = [material, optionSize ?? sizeHe(p ? p.dimensions_cm : card.dimensions_cm, place), priceHe ?? 'המחיר עוד לא נקבע']
    .filter((x): x is string => !!x)
    .join(' · ');
  const img = await photo(card, skuImage);
  // the catalog's notes describe the room engine's frame ("בתמונה: …"): the story frame brings its own caption
  const notes = [
    ...(pt.in_frame_he ? [pt.in_frame_he] : []),
    ...(styleNote ? [styleNote] : []),
    ...(p?.notes_he.filter((x) => !x.startsWith('בתמונה')) ?? []),
  ];
  if (p?.pack) notes.push(`נמכר כסט של ${p.pack.set_qty}.`);
  const faithful = faithfulOf(q, pt.product);
  const dot = isFaithful(faithful);
  const ph = dot ? phoneDot(pt, crop[0], crop[1], fw, fh) : { at: null, note: null };
  return {
    id: `${frame}-${n}`,
    frame,
    n,
    product: pt.product,
    u: pt.u,
    v: pt.v,
    box: pt.box,
    faithful,
    dot,
    phone: ph.at,
    phone_note: ph.note,
    name_he: name,
    detail_he: detail,
    price_he: priceHe,
    price_agorot: price,
    variant_id: p ? variant : null,
    option_he: pt.option?.style ? null : optionHe,
    status: !p ? 'unpriced' : available ? 'available' : 'unavailable',
    set_qty: p?.pack?.set_qty ?? 1,
    notes_he: notes,
    image: img,
    thumb: img ? img.srcset.split(', ')[0]!.split(' ')[0]! : null,
    // a draft card (DS API) has no colour yet: the rule's hairline grey
    swatch: hexOf(card) ?? '#d9d6d0',
    href: sitePages.has(pt.product) ? `/p/${pt.product}/` : null,
    try_href: tryHref(tool, roomId, pt.product),
  };
}

// ---------- the frames, pair by pair, through the gate ----------
const pages: PageOut[] = [];
const encodedDirs = new Set<string>();
for (const [key, pair] of Object.entries(story.pairs)) {
  const [room, style] = key.split('/') as [string, string];
  if (!roomOf(room) || !styleOf(style)) throw new Error(`${DATA}: pair ${key} names a room or a style that is not listed`);
  const frames: FrameOut[] = [];
  const held: Held[] = [];
  for (const f of pair.frames) {
    const q = qaOf(f.qa_key);
    if (!q || !story.allowed_states.includes(q.state)) {
      held.push({ id: f.id, qa_key: f.qa_key, state: q?.state ?? 'not_in_qa', why_he: 'הפריים עוד בבדיקת QA' });
      continue;
    }
    const listed = q.rows.filter((r) => r.present && !r.card.startsWith('fixed furniture')).map(cardOf);
    const missing = listed.filter((c) => !f.points.some((p) => p.product === c));
    if (!f.points.length || missing.length || !f.title_he || !f.alt_he) {
      // a frame QA let in, but without its hotspot map (or its words): held, said, and the build goes on
      held.push({ id: f.id, qa_key: f.qa_key, state: q.state, why_he: 'הפריים עבר QA, ומחכה למפת הנקודות' });
      console.warn(`${key} ${f.id} (${f.qa_key}, ${q.state}): held: ${missing.length ? `no point for ${missing.join(', ')}` : 'no points or words'}`);
      continue;
    }
    const src = repoPath(f.src);
    const mtime = statSync(src).mtimeMs;
    const img = sharp(src);
    const meta = await img.metadata();
    const W = meta.width!;
    const H = meta.height!;
    const dir = join(OUT, room, style, f.id);
    mkdirSync(dir, { recursive: true });
    encodedDirs.add(dir);
    // the phone: the 4:5 crop at full height, centred on phone_crop_u (clamped to the frame)
    const cw = Math.round(H * 0.8);
    const cl = Math.round(Math.min(W - cw, Math.max(0, (f.phone_crop_u ?? 0.5) * W - cw / 2)));
    const phone = img.clone().extract({ left: cl, top: 0, width: cw, height: H });
    // the encodes are reused only for the same source file and the same crop (the stamp lives with the build's state)
    const stampFile = join(GENERATED, `story-stamp.${room}.${style}.${f.id}.json`);
    const stamp = JSON.stringify({ src: f.src, mtime, crop_left: cl });
    const same = existsSync(stampFile) && readFileSync(stampFile, 'utf8') === stamp;
    for (const [w, base, source] of [
      ...WIDTHS.map((w) => [w, join(dir, String(w)), img] as const),
      ...PHONE_WIDTHS.map((w) => [w, join(dir, `m${w}`), phone] as const),
    ]) {
      if (same && existsSync(`${base}.avif`) && existsSync(`${base}.webp`)) continue;
      const r = source.clone().resize({ width: w, withoutEnlargement: true });
      await r.clone().avif({ quality: 52, effort: 4 }).toFile(`${base}.avif`);
      await r.clone().webp({ quality: 74, effort: 4 }).toFile(`${base}.webp`);
    }
    writeFileSync(stampFile, stamp);
    const crop: [number, number] = [cl / W, (cl + cw) / W];
    const points = [...f.points].sort(readingOrder);
    const items: Item[] = [];
    for (const [i, pt] of points.entries()) items.push(await itemOf(room, pair.tool, f.id, q, i + 1, pt, crop, W, H));
    // no two phone targets of 44 CSS may overlap (G-ED.17 (4)); a pair that does is reported, to be grouped
    const css = PHONE_CSS / ((crop[1] - crop[0]) * W);
    for (const a of items)
      for (const b of items)
        if (a.n < b.n && a.phone && b.phone) {
          const d = Math.hypot((a.phone.u - b.phone.u) * PHONE_CSS, (a.phone.v - b.phone.v) * H * css);
          if (d < 44) console.warn(`${key} ${f.id}: the phone dots of ${a.product} and ${b.product} are ${Math.round(d)} CSS apart`);
        }
    const ver = createHash('sha256').update(stamp).digest('hex').slice(0, 8);
    const base = `${URL_BASE}/${room}/${style}/${f.id}`;
    frames.push({
      id: f.id,
      src: f.src,
      qa_key: f.qa_key,
      role: f.role,
      u0: f.u0 ?? 0.5,
      v0: f.v0 ?? 0.5,
      phone_crop_u: f.phone_crop_u ?? 0.5,
      title_he: f.title_he,
      line_he: f.line_he ?? '',
      alt_he: f.alt_he,
      state: q.state,
      width: W,
      height: H,
      aspect: W / H,
      lqip: await lqip(img, 32, 18),
      lqip_phone: await lqip(phone, 16, 20),
      srcset: WIDTHS.map((w) => `${base}/${w}`),
      srcset_phone: PHONE_WIDTHS.map((w) => `${base}/m${w}`),
      crop,
      ver,
      items,
    });
    console.log(
      `${key} ${f.id} (${f.qa_key}, ${q.state}): ${items.length} products, ${items.filter((x) => x.status !== 'unpriced').length} priced, ${items.filter((x) => x.image).length} with the card photo; dots ${items.filter((x) => x.dot).length}, on the phone ${items.filter((x) => x.phone).length}${
        items.some((x) => x.dot && !x.phone)
          ? ` (not there: ${items
              .filter((x) => x.dot && !x.phone)
              .map((x) => `${x.product} ${x.phone_note}`)
              .join('; ')})`
          : ''
      }`,
    );
  }
  for (const h of held) console.log(`${key} ${h.id} (${h.qa_key}): held, ${h.state}`);
  pages.push({ room, style, href: pageHref(room, style), pair, frames, held });
}

// ---------- the pages ----------
const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const headOf = (pg: PageOut) => `${roomOf(pg.room).n} · ${roomOf(pg.room).name_he} · ${styleOf(pg.style).name_he}`;
const markOf = (state: string) => story.marks_he[state] ?? story.marks_he.final_test!;
function picture(f: FrameOut, eager: boolean): string {
  const set = (ext: string) => f.srcset.map((s, i) => `${s}.${ext}?v=${f.ver} ${Math.min(WIDTHS[i]!, f.width)}w`).join(', ');
  const cw = Math.round(f.height * 0.8);
  const pset = (ext: string) => f.srcset_phone.map((s, i) => `${s}.${ext}?v=${f.ver} ${Math.min(PHONE_WIDTHS[i]!, cw)}w`).join(', ');
  const pos = `object-position: ${(f.u0 * 100).toFixed(1)}% ${(f.v0 * 100).toFixed(1)}%`;
  // the phone shows the 4:5 crop at full width (Bible 1.9; G-ED.17); the desktop covers the screen with the whole frame
  return `<img class="mag-lqip st-lqip-desk" src="${f.lqip}" alt="" aria-hidden="true" width="${f.width}" height="${f.height}" style="${pos}" />
<img class="mag-lqip st-lqip-phone" src="${f.lqip_phone}" alt="" aria-hidden="true" width="${cw}" height="${f.height}" />
<picture class="mag-pic">
  <source media="(max-width: 719px)" type="image/avif" srcset="${pset('avif')}" sizes="100vw" />
  <source media="(max-width: 719px)" type="image/webp" srcset="${pset('webp')}" sizes="100vw" />
  <source type="image/avif" srcset="${set('avif')}" sizes="100vw" />
  <img src="${f.srcset[1]}.webp?v=${f.ver}" srcset="${set('webp')}" sizes="100vw" alt="${esc(f.alt_he)}" width="${f.width}" height="${f.height}" decoding="async" ${eager ? 'fetchpriority="high"' : 'loading="lazy"'} style="${pos}" />
</picture>`;
}
/** a small 4:5 picture of a pair's opening frame, for the contents and the other houses */
function thumb(f: FrameOut, alt: string): string {
  const cw = Math.round(f.height * 0.8);
  const set = (ext: string) => f.srcset_phone.map((s, i) => `${s}.${ext}?v=${f.ver} ${Math.min(PHONE_WIDTHS[i]!, cw)}w`).join(', ');
  return `<picture class="st-tile-pic">
  <source type="image/avif" srcset="${set('avif')}" sizes="(max-width: 719px) 44vw, 14rem" />
  <img src="${f.srcset_phone[0]}.webp?v=${f.ver}" srcset="${set('webp')}" sizes="(max-width: 719px) 44vw, 14rem" alt="${esc(alt)}" width="${cw}" height="${f.height}" loading="lazy" decoding="async" style="background-image: url(${f.lqip_phone})" />
</picture>`;
}
const statusOf = (x: Item) => (x.status === 'unavailable' ? '. המלאי אינו זמין כעת' : '');
const marks = (f: FrameOut) =>
  f.items
    .filter((x) => x.dot)
    .map(
      (x) =>
        `<button type="button" class="mag-mark st-mark${x.phone ? '' : ' st-no-phone'}" data-item="${x.id}" style="--u: ${x.u}; --v: ${x.v}${x.phone ? `; --pu: ${x.phone.u}; --pv: ${x.phone.v}` : ''}" aria-haspopup="dialog" aria-label="${esc(`${x.name_he}. ${x.detail_he}${statusOf(x)}. קנה את המראה`)}"><span class="mag-dot" aria-hidden="true"></span></button>`,
    )
    .join('\n');
const swatch = (x: Item) =>
  x.thumb
    ? `<img class="st-thumb" src="${x.thumb}" alt="" width="64" height="64" loading="lazy" decoding="async" />`
    : `<span class="st-thumb st-swatch" style="--swatch: ${x.swatch}" aria-hidden="true"></span>`;
const rows = (f: FrameOut) =>
  f.items
    .map(
      (x) =>
        `<li class="mag-credit st-credit" data-item="${x.id}"><span class="mag-credit-n num">${String(x.n).padStart(2, '0')}</span>${swatch(x)}<span class="mag-credit-body"><button type="button" class="st-open" data-item="${x.id}" aria-haspopup="dialog"><span class="mag-credit-name">${esc(x.name_he)}</span></button><span class="mag-credit-detail">${esc(x.detail_he)}${x.status === 'unavailable' ? ' · המלאי אינו זמין כעת' : ''}</span>${x.dot ? '' : '<span class="mag-credit-detail st-no-dot">בלי נקודה בתמונה: כאן הוא עוד לא נאמן לכרטיס במלואו.</span>'}</span></li>`,
    )
    .join('\n');
function spread(pg: PageOut, f: FrameOut, first: boolean): string {
  const h = first ? 'h1' : 'h2';
  const head = headOf(pg);
  return `<section class="mag-spread st-spread" id="frame-${f.id}" data-head="${esc(head)}" data-role="${f.role}" aria-labelledby="title-${f.id}">
  <div class="mag-stage" data-frame="${f.id}" data-marks="off" role="group" aria-label="${esc(`${f.title_he}: ${f.items.length} מוצרים בתמונה, ${f.items.filter((x) => x.dot).length} עם נקודה`)}">
    <div class="mag-scroller">
      <div class="mag-frame" style="--aspect: ${f.aspect.toFixed(4)}">
        ${picture(f, first)}
        ${marks(f)}
      </div>
    </div>
    <div class="mag-label" aria-hidden="true"></div>
    <p class="st-draft${f.state === 'almost' ? ' is-almost' : ''}">${esc(markOf(f.state))}</p>
  </div>
  <div class="st-text">
    <p class="st-kicker">${esc(head)}</p>
    <${h} id="title-${f.id}" class="st-title"><span class="st-title-line">${esc(f.title_he)}</span></${h}>
    <p class="st-line">${esc(f.line_he)}</p>
    <p class="st-to-list"><a class="st-link" href="#list-${f.id}">כל המוצרים בתמונה · <span class="num">${f.items.length}</span></a></p>
  </div>
</section>
<section class="mag-paper st-list" id="list-${f.id}" data-head="${esc(head)}" aria-labelledby="list-title-${f.id}">
  <div class="mag-grid">
    <p class="mag-run-head mag-col-main" aria-hidden="true">${esc(head)}</p>
    <h2 id="list-title-${f.id}" class="mag-h2 mag-col-main">כל המוצרים בתמונה</h2>
    <p class="mag-cap mag-col-main">${esc(f.title_he)} · <span class="num">${f.items.length}</span> מוצרים. נגיעה בשם פותחת את "קנה את המראה".</p>
    <ol class="mag-credits st-credits mag-col-main">
${rows(f)}
    </ol>
  </div>
</section>`;
}
/** a pair without a frame on its page: typographic, its concept and why the frame is not here (never the frame) */
function placeholderCover(pg: PageOut): string {
  const why = pg.held[0]?.why_he ?? 'הפריים של הבית הזה עוד לא צולם';
  return `<section class="mag-paper st-cover-type" id="cover" data-head="${esc(headOf(pg))}" aria-labelledby="cover-title">
  <div class="mag-grid">
    <p class="st-kicker mag-col-main">${esc(headOf(pg))}</p>
    <h1 id="cover-title" class="mag-display st-type-title mag-col-main">${esc(pg.pair.concept_he)}</h1>
    ${pg.pair.line_he ? `<p class="mag-lead mag-col-main">${esc(pg.pair.line_he)}</p>` : ''}
    <p class="st-type-status mag-col-main"><span class="st-type-rule" aria-hidden="true"></span>${esc(why)}.</p>
  </div>
</section>`;
}
const tile = (room: string, style: string, here: boolean): string => {
  const pg = pages.find((p) => p.room === room && p.style === style);
  const name = styleOf(style).name_he;
  if (!pg) return `<li class="st-tile is-next"><span class="st-tile-type" aria-hidden="true"></span><span class="st-tile-style">${esc(name)}</span><span class="mag-cap">בגיליונות הבאים</span></li>`;
  const f = pg.frames[0];
  const inner = `${f ? thumb(f, `${roomOf(room).name_he} ב${name}: ${f.title_he}`) : `<span class="st-tile-type" aria-hidden="true"><span>${esc(pg.pair.concept_he)}</span></span>`}<span class="st-tile-style">${esc(name)}</span><span class="st-tile-title">${esc(pg.pair.concept_he)}</span><span class="mag-cap">${esc(f ? markOf(f.state) : 'בהכנה')}</span>`;
  return here
    ? `<li class="st-tile is-here" aria-current="page">${inner}</li>`
    : `<li class="st-tile"><a class="st-tile-link" href="${pg.href}">${inner}</a></li>`;
};
function housesSection(pg: PageOut): string {
  return `<section class="mag-paper st-houses" id="houses" data-head="באותו חדר, בבתים אחרים" aria-labelledby="houses-title">
  <div class="mag-grid">
    <h2 id="houses-title" class="mag-h2 mag-col-main">${esc(roomOf(pg.room).name_he)}, בבתים אחרים</h2>
    <p class="mag-lead mag-col-main">אותו חדר, בית אחר: לכל סגנון אדריכלות, אור ושעה משלו. מעבר בין הבתים הוא חיתוך, כמו בדפדוף בגיליון.</p>
    <ol class="st-tiles st-tiles-wide">
${story.styles.map((s) => tile(pg.room, s.id, s.id === pg.style)).join('\n')}
    </ol>
  </div>
</section>`;
}
function toolSection(pg: PageOut): string {
  const tool = pg.pair.tool;
  return `<section class="mag-paper st-tool" id="tool" data-head="עצב בעצמך" aria-labelledby="tool-title">
  <div class="mag-grid">
    <p class="mag-run-head mag-col-main" aria-hidden="true">הכלי</p>
    <h2 id="tool-title" class="mag-h1 mag-col-main">עצב בעצמך</h2>
    ${
      tool
        ? `<p class="mag-lead mag-col-main">רוצים לראות את הספה עם כיסוי אחר, או כרית בגוון אחר? כאן כל פריט מתחלף במקום, והחדר מתעדכן איתו. משם ממשיכים בהליכה אל שאר הבית.</p>
    <p class="mag-col-main st-tool-row"><a class="mag-btn mag-btn-primary st-btn-link" id="st-tool" href="${esc(tool)}">לעיצוב ${esc(roomOf(pg.room).name_he)}</a></p>
    <p class="mag-cap mag-col-main">בגרסת הבדיקה הכלי פותח את הסלון של היום, בבית המשותף.</p>`
        : `<p class="mag-lead mag-col-main">הכלי של הבית הזה עוד בבנייה: באותה תוכנית, באדריכלות של הסגנון. בינתיים אפשר להחליף פריטים בסלון בבית הנורדי.</p>
    <p class="mag-col-main st-tool-row"><a class="mag-btn mag-btn-secondary st-btn-link" id="st-tool" href="${esc(story.tool_fallback)}">לסלון בבית הנורדי</a></p>`
    }
  </div>
</section>`;
}
const footer = (notes: string) => `<footer class="mag-paper mag-foot st-foot" data-head="">
  <div class="mag-grid">
    <p class="mag-cap mag-col-main">${esc(story.marks_he.final_test!)}: הפריימים הם פריימי מבחן ולא נכסי האתר, והם מופיעים רק בגרסת הבדיקה של האתר. הנקודות זמניות, ממוקמות בעין. המחירים לפי קוד התמחור של האתר, והסל הוא סל בדיקה בדפדפן.${notes ? ` ${esc(notes)}` : ''}</p>
    <p class="mag-cap mag-col-main"><a class="mag-link" href="/story/">תוכן הגיליון</a> · <a class="mag-link" href="/">לאתר</a> · <a class="mag-link" href="/accessibility/">הצהרת נגישות</a></p>
  </div>
</footer>`;
function indexBody(): string {
  const roomsHtml = story.rooms
    .map((r) => {
      const has = pages.some((p) => p.room === r.id);
      return `<li class="st-room${has ? '' : ' is-next'}" id="room-${r.id}">
  <h2 class="st-room-head"><span class="st-room-n num">${r.n}</span><span class="st-room-name">${esc(r.name_he)}</span>${has ? '' : '<span class="mag-cap">בגיליונות הבאים</span>'}</h2>
  ${has ? `<ol class="st-tiles">\n${story.styles.map((s) => tile(r.id, s.id, false)).join('\n')}\n  </ol>` : ''}
</li>`;
    })
    .join('\n');
  return `<section class="mag-paper st-index" id="contents" data-head="תוכן הגיליון" aria-labelledby="index-title">
  <div class="mag-grid">
    <p class="st-kicker mag-col-main">תוכן הגיליון</p>
    <h1 id="index-title" class="mag-display mag-col-main">הבית</h1>
    <p class="mag-lead mag-col-main">חדר אחרי חדר, בית אחרי בית. כל פריים הוא סיפור, וכל פריט בו אפשר לקנות. לכל סגנון בית משלו, באדריכלות, באור ובשעה של היום.</p>
    <ol class="st-rooms mag-col-wide">
${roomsHtml}
    </ol>
  </div>
</section>`;
}

const template = readFileSync(sitePath('tools/story/page.template.html'), 'utf8');
function render(file: string, fill: Record<string, string>): string {
  let html = template;
  for (const [k, v] of Object.entries(fill)) html = html.split(`{{${k}}}`).join(v);
  const left = html.match(/\{\{[A-Z0-9_]+\}\}/g);
  if (left) throw new Error(`${file}: template placeholders left: ${left.join(', ')}`);
  mkdirSync(dirname(sitePath(file)), { recursive: true });
  writeFileSync(sitePath(file), html);
  return html;
}
// the pages of a previous build that the data no longer declares go, so nothing stale is built
rmSync(sitePath('web/story'), { recursive: true, force: true });
const resolved: Record<string, unknown> = {};
for (const pg of pages) {
  const data = {
    page: { room: pg.room, style: pg.style, href: pg.href, tool: pg.pair.tool ?? story.tool_fallback },
    items: Object.fromEntries(pg.frames.flatMap((f) => f.items.map((x) => [x.id, x]))),
    frames: pg.frames.map((f) => ({ id: f.id, u0: f.u0, v0: f.v0, aspect: f.aspect, crop: f.crop, title_he: f.title_he, items: f.items.map((x) => x.id) })),
  };
  resolved[pg.href] = { ...data, held: pg.held, states: pg.frames.map((f) => [f.id, f.qa_key, f.state]) };
  const title = pg.frames[0]?.title_he ?? pg.pair.concept_he;
  const body = [
    ...(pg.frames.length ? pg.frames.map((f, i) => spread(pg, f, i === 0)) : [placeholderCover(pg)]),
    toolSection(pg),
    housesSection(pg),
    footer(pg.frames.map((f) => `${f.title_he}: ${f.qa_key}, QA ${f.state === 'almost' ? 'כמעט' : 'מבחן סופי'}`).join('. ')),
  ].join('\n');
  const html = render(`web${pg.href}index.html`, {
    TITLE: esc(`${roomOf(pg.room).name_he} · ${styleOf(pg.style).name_he} · ${title}`),
    DESCRIPTION: esc(`${roomOf(pg.room).name_he} בבית ה${styleOf(pg.style).name_he}: ${title}. גרסת בדיקה.`),
    ISSUE: esc(story.issue_he),
    KIND: pg.frames.length ? 'pair' : 'type',
    HEAD_ON: pg.frames.length ? 'stage' : 'paper',
    CONTENTS_CURRENT: '',
    NAV_TOOL: '#tool',
    SKIP: pg.frames.length ? `#list-${pg.frames[0]!.id}` : '#houses',
    SKIP_HE: pg.frames.length ? 'דילוג לרשימת המוצרים' : 'דילוג לבתים האחרים',
    TOOL_HREF: esc(pg.pair.tool ?? story.tool_fallback),
    BODY: body,
    DATA: JSON.stringify(data).replace(/</g, '\\u003c'),
  });
  console.log(`${pg.href} → web${pg.href}index.html (${(html.length / 1024).toFixed(1)} KB): ${pg.frames.length ? pg.frames.map((f) => `${f.id} ${f.state}`).join(', ') : 'typographic'}`);
}
const indexHtml = render('web/story/index.html', {
  TITLE: esc(`${story.issue_he} · תוכן הגיליון`),
  DESCRIPTION: esc('תוכן הגיליון: כל חדר בכל בית, פריים סיפור לכל חדר וסגנון. גרסת בדיקה.'),
  ISSUE: esc(story.issue_he),
  KIND: 'index',
  HEAD_ON: 'paper',
  CONTENTS_CURRENT: ' aria-current="page"',
  NAV_TOOL: esc(story.tool_fallback),
  SKIP: '#contents',
  SKIP_HE: 'דילוג לתוכן',
  TOOL_HREF: esc(story.tool_fallback),
  BODY: [indexBody(), footer('')].join('\n'),
  DATA: JSON.stringify({ page: { room: null, style: null, href: '/story/', tool: story.tool_fallback }, items: {}, frames: [] }),
});
console.log(`/story/ → web/story/index.html (${(indexHtml.length / 1024).toFixed(1)} KB): ${story.rooms.length} rooms × ${story.styles.length} styles, ${pages.length} pages`);
// the prototype's address goes on to its real page
mkdirSync(sitePath('web/test/story'), { recursive: true });
const to = pageHref('living-room', 'nordic');
writeFileSync(
  sitePath('web/test/story/index.html'),
  `<!doctype html>
<html lang="he" dir="rtl">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="robots" content="noindex, nofollow" />
    <meta http-equiv="refresh" content="0; url=${to}" />
    <title>הסיפור עבר לכתובת חדשה</title>
  </head>
  <body>
    <p><a href="${to}">הסיפור עבר: הסלון בבית הנורדי</a></p>
  </body>
</html>
`,
);
mkdirSync(GENERATED, { recursive: true });
writeFileSync(join(GENERATED, 'story.json'), JSON.stringify(resolved, null, 1));
const all = pages.flatMap((p) => p.frames.flatMap((f) => f.items));
console.log(
  `story: ${pages.length} pages (${pages.filter((p) => p.frames.length).length} with frames, ${pages.filter((p) => !p.frames.length).length} typographic); ${all.length} points, ${all.filter((x) => x.status === 'available').length} for sale, ${all.filter((x) => x.status === 'unavailable').length} not sold now, ${all.filter((x) => x.status === 'unpriced').length} without a price; ${all.filter((x) => !x.image).length} without a cached card photo`,
);
