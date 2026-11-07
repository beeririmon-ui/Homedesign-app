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
import { availableValues, selectionOf } from '@hd/shared/picker';
import { colorNameHe, materialsHe } from './lib/hebrew';
import { GENERATED, MEDIA_OUT, repoPath, sitePath } from './lib/paths';
import { cardOf, registerReader, rowOf, type QaFrame, type QaState } from './lib/qa-frames';

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
/** a close-up of layer 2 ("הפרט"): one product, in one option, in the house's light; let in by the same QA gate */
type CloseupSpec = { product: string; option?: Record<string, string>; src: string; qa_key: string; alt_he: string };
/** S3: the house's own tool, a draft from the render pilot (TEST): its layers at the tool's camera, and the house to compare */
type ToolDraft = {
  frame: string;
  mobile_center_u: number;
  layers: { id: string; src: string; blend: 'normal' | 'multiply' | 'screen' }[];
  status_he: string;
  /** the other house at the same camera (a draft too): its layers, encoded the same way */
  compare: { house: string; layers: ToolDraft['layers']; alt_he: string };
};
type Pair = { concept_he: string; line_he?: string; tool: string | null; tool_draft?: ToolDraft; frames: FrameSpec[]; closeups?: CloseupSpec[] };
type Story = {
  issue_he: string;
  /** QA's register: the highest version of qa/reports/ged-register-*.json (tools/lib/qa-frames.ts) */
  qa_register: string;
  allowed_states: QaState[];
  marks_he: Record<string, string>;
  tool_fallback: string;
  rooms: { id: string; n: string; name_he: string }[];
  styles: { id: string; name_he: string }[];
  names_he: Record<string, string>;
  /** a shape that an option gives the product its own name for (design notes §6): product → "axis:value" → base name */
  option_names_he?: Record<string, Record<string, string>>;
  /** the designer's colour word for an option's value, before the supplier's label: product → "axis:value" → word */
  colours_he?: Record<string, Record<string, string>>;
  /** a set made of one SKU per value of an axis (a triptych's three prints): sold as the set only, the axis not offered */
  set_axes?: Record<string, { axis: string; note_he: string }>;
  pairs: Record<string, Pair>;
};
type Card = {
  id: string;
  slot: string;
  materials?: string[];
  dimensions_cm?: { width?: number | null; depth?: number | null; height?: number | null };
  colors: { dominant_hex: string };
  images: { urls: string[] };
  options?: {
    default_sku: string;
    axes: { id: string; values: { id: string; label_he: string }[] }[];
    skus: { id: string; values: Record<string, string>; image?: string }[];
  };
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
  /** the detail page (layer 2) of this product in this house */
  href: string | null;
  try_href: string | null;
  /** the values of the SKU the frame shows (the card's default with the point's option), or null without options */
  values: Record<string, string> | null;
  in_frame_he: string | null;
  /** the product's part of the frame, as a small 4:5 crop: "בחדר הזה" on the detail page */
  crop_image: Image | null;
  /** the product alone, centred, at least half the crop's width, never enlarged: stands in for a missing photo (§6) */
  product_crop: Image | null;
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
const register = registerReader();
const qaOf = register.read;
console.log(`QA register ${register.path}, version ${register.version}`);
for (const [key, pair] of Object.entries(story.pairs))
  for (const f of pair.frames) {
    const by = register.supersededBy(f.qa_key);
    if (by) console.warn(`${key} ${f.id}: ${f.qa_key} is superseded by ${by} in the register: the frame stays out until the data names ${by}`);
  }
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
/**
 * The product alone, for a detail page without a supplier photo (design notes §6, Q3): centred on its box, the product
 * at least half the crop's width (0.62 of it), 4:5; a tall product shows its part around the point. One file at the
 * crop's own size up to 640, shown at that size or smaller, never enlarged.
 */
async function productCrop(img: sharp.Sharp, W: number, H: number, box: Box, v: number, dir: string, url: string): Promise<Image> {
  const [x0, x1, y0, y1] = box;
  const w = Math.round(Math.min(W, Math.max(64, ((x1 - x0) * W) / 0.62)));
  const h = Math.round(Math.min(H, w / 0.8));
  const left = Math.round(Math.min(W - w, Math.max(0, ((x0 + x1) / 2) * W - w / 2)));
  const cy = (y1 - y0) * H <= h ? ((y0 + y1) / 2) * H : v * H;
  const top = Math.round(Math.min(H - h, Math.max(0, cy - h / 2)));
  const key = createHash('sha256')
    .update(JSON.stringify(['product', box, v, W, H]))
    .digest('hex')
    .slice(0, 10);
  mkdirSync(dir, { recursive: true });
  const ow = Math.min(640, w);
  const out = join(dir, `${key}.p${ow}.webp`);
  if (!existsSync(out)) await img.clone().extract({ left, top, width: w, height: h }).resize({ width: ow }).webp({ quality: 80 }).toFile(out);
  return { src: `${url}/${key}.p${ow}.webp`, srcset: '', w: ow, h: Math.round((ow * h) / w) };
}
/** layer 2, "הפרט": a product's page in one house (its close-ups are in that house's light) */
const detailHref = (room: string, style: string, product: string) => `/story/${room}/${style}/p/${product}/`;
/**
 * The product's part of the frame as a 4:5 crop around its box (at least 0.3 of the frame's height, so a small product
 * keeps its surroundings), at 320 and 640 wide, never enlarged: "בחדר הזה" on the detail page. Named by the box, so a
 * moved point makes a new crop.
 */
async function itemCrop(img: sharp.Sharp, W: number, H: number, box: Box, dir: string, url: string): Promise<Image> {
  const [x0, x1, y0, y1] = box;
  const h = Math.round(Math.min(H, Math.max(0.3 * H, (y1 - y0) * H * 1.5, ((x1 - x0) * W * 1.5) / 0.8)));
  const w = Math.min(W, Math.round(h * 0.8));
  const left = Math.round(Math.min(W - w, Math.max(0, ((x0 + x1) / 2) * W - w / 2)));
  const top = Math.round(Math.min(H - h, Math.max(0, ((y0 + y1) / 2) * H - h / 2)));
  const key = createHash('sha256')
    .update(JSON.stringify([box, W, H]))
    .digest('hex')
    .slice(0, 10);
  mkdirSync(dir, { recursive: true });
  const srcs: string[] = [];
  for (const cw of [320, 640]) {
    const out = join(dir, `${key}.${cw}.webp`);
    if (!existsSync(out))
      await img.clone().extract({ left, top, width: w, height: h }).resize({ width: cw, withoutEnlargement: true }).webp({ quality: 78 }).toFile(out);
    srcs.push(`${url}/${key}.${cw}.webp ${Math.min(cw, w)}w`);
  }
  const dw = Math.min(640, w);
  return { src: `${url}/${key}.320.webp`, srcset: srcs.join(', '), w: dw, h: Math.round((dw * h) / w) };
}

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
  return url ? photoOf(card, url) : null;
}
/** One cached supplier photo at 160, 480 and 800 (never downloaded here: tools/supplier-images.ts fills the cache). */
async function photoOf(card: Card, url: string | null | undefined): Promise<Image | null> {
  if (!url || !/^https:\/\//.test(url) || !existsSync(cacheOf(url))) return null;
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
const faithfulOf = (q: QaFrame, product: string, values: Record<string, string> | null): string => rowOf(q, product, values)?.faithful ?? 'not checked';
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
  if (Math.max(w, h) < MIN_LONG || Math.min(w, h) < MIN_SHORT)
    return { at: null, note: `בטלפון ${Math.round(w)}×${Math.round(h)} CSS, פחות מ-${MIN_LONG}×${MIN_SHORT}` };
  const margin = 23 / PHONE_CSS;
  if (pt.phone_at) {
    const cu = (pt.phone_at[0] - c0) / (c1 - c0);
    if (cu < margin || cu > 1 - margin)
      throw new Error(`${pt.product}: the phone dot u ${pt.phone_at[0]} is not inside the crop ${c0.toFixed(3)}–${c1.toFixed(3)}`);
    return { at: { u: Math.round(cu * 10000) / 10000, v: pt.phone_at[1] }, note: null };
  }
  const cu = (pt.u - c0) / (c1 - c0);
  const u = cu >= margin && cu <= 1 - margin ? cu : ((a + b) / 2 - c0) / (c1 - c0);
  return { at: { u: Math.round(Math.min(1 - margin, Math.max(margin, u)) * 10000) / 10000, v: pt.v }, note: null };
}

async function itemOf(
  roomId: string,
  tool: string | null,
  frame: string,
  q: QaFrame,
  n: number,
  pt: Point,
  crop: [number, number],
  fw: number,
  fh: number,
  closeups: CloseupSpec[] = [],
): Promise<Item> {
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
    if (p && !o)
      console.warn(`${frame}: ${pt.product}: the card's options did not reach the catalog (see build-catalog's warnings); the product's own price is used`);
    if (sku) {
      price = sku.price_agorot;
      variant = sku.variant_id;
      available &&= sku.available;
    }
    // the colour or the style of the option names it; a size goes to the credit (a product not priced yet: the card's own labels)
    const axes = o?.axes ?? card.options?.axes ?? [];
    const labelOf = (axis: string) => axes.find((a) => a.id === axis)?.values.find((v) => v.id === pt.option![axis])?.label_he ?? null;
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
  const notes = [...(pt.in_frame_he ? [pt.in_frame_he] : []), ...(styleNote ? [styleNote] : []), ...(p?.notes_he.filter((x) => !x.startsWith('בתמונה')) ?? [])];
  if (p?.pack) notes.push(`נמכר כסט של ${p.pack.set_qty}.`);
  const values = card.options ? { ...(cardSku?.values ?? {}), ...(pt.option ?? {}) } : null;
  const row = rowOf(q, pt.product, values);
  const faithful = row?.faithful ?? 'not checked';
  // G-ED.5: "partly" in the frame gets its dot when the product's close-up in this house passed G-ED as "yes"
  // QA on S2 (2026-11-07): a close-up lights a "partly" dot only when it is at least final test (almost is not enough),
  // shows the same option as the frame, and its own row for the product says "yes"
  const closeupYes = closeups.some((c) => {
    if (c.product !== pt.product) return false;
    const sameOption = Object.entries(c.option ?? {}).every(([k, v]) => values?.[k] === v) && (!!c.option || !pt.option);
    const cq = sameOption ? qaOf(c.qa_key) : null;
    return !!cq && FINAL.has(cq.state) && isFaithful(faithfulOf(cq, pt.product, values));
  });
  // the register says where a dot goes (yes | no | closeup_only); an older record only gives the verdict
  const dot = row?.dot ? row.dot === 'yes' || (row.dot === 'closeup_only' && closeupYes) : isFaithful(faithful) || (/^partly\b/.test(faithful) && closeupYes);
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
    href: null,
    try_href: tryHref(tool, roomId, pt.product),
    values,
    in_frame_he: pt.in_frame_he ?? null,
    crop_image: null,
    product_crop: null,
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
      held.push({ id: f.id, qa_key: f.qa_key, state: q?.state ?? 'not_in_qa', why_he: 'הפריים עוד בבדיקה' });
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
    for (const [i, pt] of points.entries()) items.push(await itemOf(room, pair.tool, f.id, q, i + 1, pt, crop, W, H, pair.closeups));
    for (const x of items) {
      x.href = detailHref(room, style, x.product);
      x.crop_image = await itemCrop(img, W, H, x.box, join(dir, 'items'), `${URL_BASE}/${room}/${style}/${f.id}/items`);
      x.product_crop = await productCrop(img, W, H, x.box, x.v, join(dir, 'items'), `${URL_BASE}/${room}/${style}/${f.id}/items`);
    }
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

// ---------- layer 2, "הפרט": a page per product per house ----------
/** a close-up as the page shows it: QA's state rides with it (the same gate as the frames) */
type Closeup = Image & { alt_he: string; state: QaState; qa_key: string };
type DetailSku = {
  /** the value ids in axis order, joined by "+" (the variant id's suffix), or "default" for a product without options */
  key: string;
  values: Record<string, string>;
  label_he: string | null;
  variant_id: string | null;
  price_agorot: number | null;
  price_he: string | null;
  /** the single piece of a product sold as a set (SET1), where the supplier offers one; an estimate when marked */
  unit_price_agorot: number | null;
  unit_price_he: string | null;
  unit_estimated: boolean;
  /** the page's title for this option (design notes §6): the base name and the option's colour, never its size */
  title_he: string;
  /** offered in the picker (a product without a price yet still shows its options) */
  available: boolean;
  /** for sale: priced, in stock, the product sold */
  sellable: boolean;
  size_he: string | null;
  days: [number, number] | null;
  image: Image | null;
  /** the photo is this option's own (else the listing's main photo, for the option the story shows) */
  image_of_option: boolean;
  closeup: Closeup | null;
};
type DetailAxis = { id: string; name_he: string; values: { id: string; label_he: string; hex: string | null }[] };
type DetailHere = { item: string; frame: string; title_he: string; n: number; href: string; image: Image | null; note_he: string | null; dot: boolean };
type DetailOut = {
  room: string;
  style: string;
  href: string;
  product: string;
  name_he: string;
  material_he: string | null;
  materials_he: string[];
  status: 'available' | 'unavailable' | 'unpriced';
  set_qty: number;
  swatch: string;
  notes_he: string[];
  axes: DetailAxis[];
  skus: DetailSku[];
  story_key: string;
  here: DetailHere[];
  elsewhere: { house_he: string; href: string; image: Image | null }[];
  try_href: string | null;
  /** close-ups declared for this product in this house that QA has not let in yet */
  closeups_held: number;
  /** the product's crop from the story frame and its caption: stands in for a missing photo, on the story's option only */
  crop: Image | null;
  crop_caption_he: string | null;
};
const keyOf = (axes: { id: string }[], values: Record<string, string> | null): string =>
  axes.length && values ? axes.map((a) => values[a.id] ?? '').join('+') : 'default';
const sizeLabel = (label: string | null | undefined): string | null => {
  const m = label?.match(/^([\d.]+)×([\d.]+) ס["״]מ$/);
  return m ? `⁦${m[1]}×${m[2]}⁩ ס״מ` : (label ?? null);
};
const closeupsSeen = new Map<string, Closeup>();
/** the states that let a close-up light a "partly" dot (QA on S2: almost is not enough) */
const FINAL = new Set<QaState>(['final_test', 'approved_for_site']);
async function closeupOf(room: string, style: string, c: CloseupSpec): Promise<Closeup | null> {
  const q = qaOf(c.qa_key);
  if (!q || !story.allowed_states.includes(q.state)) return null;
  const key = createHash('sha256').update(JSON.stringify(c)).digest('hex').slice(0, 10);
  if (closeupsSeen.has(key)) return closeupsSeen.get(key)!;
  const src = repoPath(c.src);
  const img = sharp(src);
  const meta = await img.metadata();
  const dir = join(OUT, room, style, 'closeups', c.product);
  mkdirSync(dir, { recursive: true });
  const url = `${URL_BASE}/${room}/${style}/closeups/${c.product}`;
  const srcs: string[] = [];
  for (const w of [640, 1024, 1600]) {
    const out = join(dir, `${key}.${w}.webp`);
    if (!existsSync(out)) await img.clone().resize({ width: w, withoutEnlargement: true }).webp({ quality: 78 }).toFile(out);
    srcs.push(`${url}/${key}.${w}.webp ${Math.min(w, meta.width!)}w`);
  }
  const w = Math.min(1600, meta.width!);
  const out: Closeup = {
    src: `${url}/${key}.1024.webp`,
    srcset: srcs.join(', '),
    w,
    h: Math.round((w * meta.height!) / meta.width!),
    alt_he: c.alt_he,
    state: q.state,
    qa_key: c.qa_key,
  };
  closeupsSeen.set(key, out);
  return out;
}
async function detailOf(pg: PageOut, product: string, items: Item[]): Promise<DetailOut> {
  const card = cards.get(product)!;
  const p = catalog.products.find((x) => x.id === product) ?? null;
  const first = items[0]!;
  const place = placement.get(card.slot) ?? 'surface';
  const o = p?.options ? expandOptions(p.id, p.options) : null;
  const productOk = p?.availability.status === 'available';
  const imageOf = (values: Record<string, string>) =>
    card.options?.skus.find((s) => Object.entries(values).every(([k, v]) => s.values[k] === v))?.image ?? null;
  const axes: DetailAxis[] = o
    ? o.axes
    : p
      ? []
      : (card.options?.axes.map((a) => ({
          id: a.id,
          name_he: (a as { name_he?: string }).name_he ?? a.id,
          values: a.values.map((v) => ({ id: v.id, label_he: v.label_he, hex: (v as { hex?: string }).hex ?? null })),
        })) ?? []);
  const labelOf = (values: Record<string, string>) => axes.map((a) => a.values.find((v) => v.id === values[a.id])?.label_he ?? values[a.id]).join(', ') || null;
  const sizeOf = (values: Record<string, string>) =>
    axes.some((a) => a.id === 'size')
      ? sizeLabel(axes.find((a) => a.id === 'size')!.values.find((v) => v.id === values.size)?.label_he)
      : sizeHe(p ? p.dimensions_cm : card.dimensions_cm, place);
  // QA on S4: a set of distinct SKUs (one per value of an axis) is sold as the set only; the axis is not a choice
  const setAxis = story.set_axes?.[product] ?? null;
  const unitOk = !!p?.pack && p.pack.set_qty > 1 && !setAxis;
  const unitOf = (u: number | null | undefined) => ({
    unit_price_agorot: unitOk && u != null ? u : null,
    unit_price_he: unitOk && u != null ? formatIls(u) : null,
    unit_estimated: unitOk && !!p?.pack?.unit_price_estimated,
  });
  const raw: Omit<DetailSku, 'image' | 'image_of_option' | 'closeup' | 'title_he'>[] = o
    ? o.skus.map((k) => ({
        key: keyOf(axes, k.values),
        values: k.values,
        label_he: labelOf(k.values),
        variant_id: k.variant_id,
        price_agorot: k.price_agorot,
        price_he: formatIls(k.price_agorot),
        available: k.available && productOk,
        sellable: k.available && productOk,
        size_he: sizeOf(k.values),
        days: k.shipping_days ?? p!.shipping_days ?? null,
        ...unitOf(k.unit_price_agorot ?? p!.pack?.unit_price_agorot),
      }))
    : p
      ? [
          {
            key: 'default',
            values: {},
            label_he: null,
            variant_id: p.variants[0]?.id ?? null,
            price_agorot: p.price_agorot,
            price_he: formatIls(p.price_agorot),
            available: productOk,
            sellable: productOk && !!p.variants[0],
            size_he: sizeOf({}),
            days: p.shipping_days ?? null,
            ...unitOf(p.pack?.unit_price_agorot),
          },
        ]
      : axes.length
        ? card.options!.skus.map((k) => ({
            key: keyOf(axes, k.values as Record<string, string>),
            values: k.values as Record<string, string>,
            label_he: labelOf(k.values as Record<string, string>),
            variant_id: null,
            price_agorot: null,
            price_he: null,
            available: true,
            sellable: false,
            size_he: sizeOf(k.values as Record<string, string>),
            days: null,
            ...unitOf(null),
          }))
        : [
            {
              key: 'default',
              values: {},
              label_he: null,
              variant_id: null,
              price_agorot: null,
              price_he: null,
              available: true,
              sellable: false,
              size_he: sizeOf({}),
              days: null,
              ...unitOf(null),
            },
          ];
  if (setAxis) {
    const at = axes.findIndex((a) => a.id === setAxis.axis);
    if (at < 0) throw new Error(`${product}: set_axes names ${setAxis.axis}, which the card does not have`);
    const keep = first.values?.[setAxis.axis];
    for (let i = raw.length - 1; i >= 0; i--) if (raw[i]!.values[setAxis.axis] !== keep) raw.splice(i, 1);
    axes.splice(at, 1);
    for (const k of raw) {
      k.values = Object.fromEntries(Object.entries(k.values).filter(([a]) => a !== setAxis.axis));
      k.key = keyOf(axes, k.values);
      k.label_he = labelOf(k.values);
    }
  }
  const story_key = keyOf(axes, setAxis ? Object.fromEntries(Object.entries(first.values ?? {}).filter(([a]) => a !== setAxis.axis)) : first.values);
  if (!raw.some((k) => k.key === story_key)) throw new Error(`${pg.href}: ${product}: the frame's option ${story_key} is not one of its SKUs`);
  // the close-ups this house declares for the product: on their option, else on the option the story shows
  const declared = (pg.pair.closeups ?? []).filter((c) => c.product === product);
  const closeups = new Map<string, Closeup>();
  let held = 0;
  for (const c of declared) {
    const cu = await closeupOf(pg.room, pg.style, c);
    if (!cu) held++;
    else closeups.set(c.option ? keyOf(axes, { ...(first.values ?? {}), ...c.option }) : story_key, cu);
  }
  // the title (design notes §6): the story's name on the story's option; else the base name (or the option's own shape
  // name) and the colour of the option, readable colours only (a supplier's "2" or "c-3" names nothing), never a size
  const NAMING = new Set(['color', 'style', 'pattern', 'finish', 'other']);
  // an axis whose values carry their own shape name (option_names_he) names the shape, not the colour
  const shapeAxes = new Set(axes.filter((a) => a.values.some((v) => story.option_names_he?.[product]?.[`${a.id}:${v.id}`])).map((a) => a.id));
  const naming = axes.filter((a) => NAMING.has(a.id) && !shapeAxes.has(a.id));
  // a readable colour is a Hebrew word that is not a size: a supplier's "2", "c-3", "Curry" or "35x37 cm" names nothing here
  const readable = (l: string) => /[\u0590-\u05FF]/.test(l) && !/\d+\s*[×x]\s*\d+/.test(l);
  const shapeOf = (values: Record<string, string>) =>
    Object.entries(values)
      .map(([a, v]) => story.option_names_he?.[product]?.[`${a}:${v}`])
      .find(Boolean) ?? null;
  const storyValues = first.values ?? {};
  const base = naming.length && first.name_he.includes(', ') ? first.name_he.slice(0, first.name_he.lastIndexOf(', ')) : first.name_he;
  const titleOf = (values: Record<string, string>): string => {
    const shape = shapeOf(values);
    const sameColour = naming.every((a) => values[a.id] === storyValues[a.id]);
    if (sameColour && shape === shapeOf(storyValues)) return first.name_he;
    // the story's own colour word when the colour is the story's ("פחם", not the supplier's "אפור כהה")
    if (sameColour && naming.length && first.name_he.includes(', ')) return `${shape ?? base}, ${first.name_he.slice(first.name_he.lastIndexOf(', ') + 2)}`;
    // the designer's colour word for a value (colours_he, the §4 table) before the supplier's label
    const colour = naming
      .map((a) => story.colours_he?.[product]?.[`${a.id}:${values[a.id]}`] ?? a.values.find((v) => v.id === values[a.id])?.label_he ?? '')
      .filter((l) => l && readable(l))
      .join(', ');
    return colour ? `${shape ?? base}, ${colour}` : (shape ?? base);
  };
  const skus: DetailSku[] = [];
  for (const k of raw) {
    // the option's own photo; an option the card lists no photo for shows the listing's main photo, for the story's option only
    const own = imageOf(k.values);
    const image = await photoOf(card, own ?? (k.key === story_key ? card.images.urls[0] : null));
    skus.push({ ...k, title_he: titleOf(k.values), image, image_of_option: !!image && !!own, closeup: closeups.get(k.key) ?? null });
  }
  const elsewhere = pages
    .filter((x) => x !== pg && x.frames.some((f) => f.items.some((it) => it.product === product)))
    .map((x) => ({
      house_he: `${roomOf(x.room).name_he} בבית ה${styleOf(x.style).name_he}`,
      href: detailHref(x.room, x.style, product),
      image: x.frames.flatMap((f) => f.items).find((it) => it.product === product)!.crop_image,
    }));
  return {
    room: pg.room,
    style: pg.style,
    href: detailHref(pg.room, pg.style, product),
    product,
    name_he: first.name_he,
    material_he: p ? (p.materials_he[0] ?? null) : (materialsHe(card.materials ?? [])[0] ?? null),
    materials_he: p ? p.materials_he : materialsHe(card.materials ?? []),
    status: first.status,
    set_qty: first.set_qty,
    swatch: first.swatch,
    // the product's own notes (the frame's own captions go with "בחדר הזה")
    notes_he: [
      ...(setAxis ? [setAxis.note_he] : []),
      ...new Set(items.flatMap((x) => x.notes_he.filter((n) => n !== x.in_frame_he && !n.startsWith('בתמונה')))),
    ],
    axes,
    skus,
    story_key,
    here: items.map((x) => ({
      item: x.id,
      frame: x.frame,
      title_he: pg.frames.find((f) => f.id === x.frame)!.title_he,
      n: x.n,
      href: `${pg.href}#frame-${x.frame}`,
      image: x.crop_image,
      note_he:
        [
          x.in_frame_he,
          x.notes_he.find((n) => n.startsWith('בתמונה: האפשרות')),
          // another option of the same product in this house: the tile says which
          keyOf(axes, x.values) !== story_key && !x.notes_he.some((n) => n.startsWith('בתמונה: האפשרות'))
            ? `כאן באפשרות ${labelOf(x.values ?? {}) ?? ''}.`
            : null,
        ]
          .filter(Boolean)
          .join(' ') || null,
      dot: x.dot,
    })),
    elsewhere,
    try_href: first.try_href,
    closeups_held: held,
    crop: first.product_crop,
    crop_caption_he: (() => {
      const named = naming.map((a) => a.values.find((v) => v.id === storyValues[a.id])?.label_he ?? '').filter((l) => l && readable(l));
      const title = pg.frames.find((f) => f.id === first.frame)!.title_he;
      return named.length
        ? `מתוך הסיפור, בפריים "${title}". בתמונה: האפשרות "${named.join(', ')}". זו לא תמונת מוצר.`
        : `מתוך הסיפור, בפריים "${title}". זו לא תמונת מוצר.`;
    })(),
  };
}
const details: DetailOut[] = [];
for (const pg of pages) {
  const byProduct = new Map<string, Item[]>();
  for (const it of pg.frames.flatMap((f) => f.items)) byProduct.set(it.product, [...(byProduct.get(it.product) ?? []), it]);
  for (const [product, items] of byProduct) details.push(await detailOf(pg, product, items));
}
// QA on S2: a dot's link opens the detail page on the option that dot shows (the second bouclé of warm modern is white)
for (const pg of pages)
  for (const x of pg.frames.flatMap((f) => f.items)) {
    const d = details.find((y) => y.room === pg.room && y.style === pg.style && y.product === x.product)!;
    const k = keyOf(d.axes, x.values);
    if (k !== d.story_key) x.href = `${d.href}?${new URLSearchParams(d.axes.map((a) => [a.id, x.values?.[a.id] ?? ''])).toString()}`;
  }
for (const d of details)
  if (!d.skus.some((k) => k.image) && !d.skus.some((k) => k.closeup))
    console.log(`${d.href}: no cached card photo and no close-up: the frame's crop stands in`);

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
/**
 * "קנה את המראה" whole (S4): every product of the frame that is for sale, once, in the option the frame shows; what is
 * not for sale is named, never added (no price yet, PRE1)
 */
function lookHtml(f: FrameOut): string {
  // QA on S4: only a product with a dot (QA called it faithful here); a "partly" one is never added with the look
  const sold = [...new Map(f.items.filter((x) => x.status === 'available' && x.variant_id && x.dot).map((x) => [x.variant_id!, x])).values()];
  if (!sold.length) return '';
  const total = sold.reduce((n, x) => n + (x.price_agorot ?? 0), 0);
  const unpriced = f.items.filter((x) => x.status === 'unpriced').length;
  const out = f.items.filter((x) => x.status === 'unavailable').length;
  const left = [
    unpriced ? `${unpriced === 1 ? 'מוצר אחד' : `${unpriced} מוצרים`} בלי מחיר עדיין` : null,
    out ? `${out === 1 ? 'מוצר אחד' : `${out} מוצרים`} שהמלאי שלהם אינו זמין כעת` : null,
  ]
    .filter(Boolean)
    .join(', ');
  return `<div class="st-look mag-col-main">
      <button type="button" class="mag-btn mag-btn-secondary st-look-btn" id="look-${f.id}" data-frame="${f.id}" data-variants="${esc(sold.map((x) => x.variant_id).join(' '))}">המראה כולו לסל · <span class="num">${sold.length}</span> מוצרים · ${formatIls(total)}</button>
      ${left ? `<p class="mag-cap st-look-left">לא נכללים: ${esc(left)}.</p>` : ''}
    </div>`;
}
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
    ${lookHtml(f)}
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
  if (!pg)
    return `<li class="st-tile is-next"><span class="st-tile-type" aria-hidden="true"></span><span class="st-tile-style">${esc(name)}</span><span class="mag-cap">בגיליונות הבאים</span></li>`;
  const f = pg.frames[0];
  // a typographic tile carries its concept in the box (said once: the box is the tile's title for every reader)
  const inner = f
    ? `${thumb(f, `${roomOf(room).name_he} ב${name}: ${f.title_he}`)}<span class="st-tile-style">${esc(name)}</span><span class="st-tile-title">${esc(pg.pair.concept_he)}</span><span class="mag-cap">${esc(markOf(f.state))}</span>`
    : `<span class="st-tile-type"><span class="st-tile-title">${esc(pg.pair.concept_he)}</span></span><span class="st-tile-style">${esc(name)}</span><span class="mag-cap">בהכנה: הפריים עוד בבדיקה</span>`;
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
    <p class="mag-col-main st-tool-row"><a class="mag-btn mag-btn-primary st-btn-link" id="st-tool" href="${esc(`${tool}?from=${encodeURIComponent(pg.href)}`)}">לעיצוב ${esc(roomOf(pg.room).name_he)}</a></p>
    <p class="mag-cap mag-col-main">בגרסת הבדיקה הכלי פותח את הסלון של היום, בבית המשותף.</p>`
        : `<p class="mag-lead mag-col-main">הכלי של הבית הזה עוד בבנייה: באותה תוכנית, באדריכלות של הסגנון. בינתיים אפשר להחליף פריטים בסלון בבית הנורדי.</p>
    <p class="mag-col-main st-tool-row"><a class="mag-btn mag-btn-secondary st-btn-link" id="st-tool" href="${esc(`${story.tool_fallback}?from=${encodeURIComponent(pg.href)}`)}">לסלון בבית הנורדי</a>${
      pg.pair.tool_draft ? ` <a class="mag-link st-tool-draft-link" id="st-tool-draft" href="${pg.href}tool/">טיוטת הכלי של הבית הזה</a>` : ''
    }</p>`
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

// ---------- the detail page (layer 2) ----------
const CHIPS_MAX = 8;
const SWATCHES_MAX = 16;
const imgTag = (im: Image, alt: string, sizes: string, id = '', eager = false) =>
  `<img${id ? ` id="${id}"` : ''} src="${im.src}" srcset="${im.srcset}" sizes="${sizes}" alt="${esc(alt)}" width="${im.w}" height="${im.h}" decoding="async"${eager ? ' fetchpriority="high"' : ' loading="lazy"'} />`;
/** the supplier options, as the site's product page draws them (web/src/components/OptionPicker.tsx): a fieldset per axis */
function pickerHtml(d: DetailOut, sku: DetailSku): string {
  if (!d.axes.length) return '';
  // the picker's rules (@hd/shared/options) see a SKU by its key: a product without a price has no variant id yet
  const pool = d.skus.map((k) => ({ variant_id: k.key, values: k.values, available: k.available }));
  const sel = selectionOf(d.axes, { variant_id: sku.key, values: sku.values, available: sku.available });
  return `<div class="st-pd-options" id="st-pd-options">
${d.axes
  .map((a, i) => {
    const ok = availableValues(d.axes, pool, sel, i);
    const fid = `st-opt-${a.id}`;
    const swatches = a.id === 'color' && a.values.length <= SWATCHES_MAX && a.values.every((v) => v.hex);
    const current = a.values.find((v) => v.id === sel[a.id])?.label_he ?? '';
    if (!swatches && a.values.length > CHIPS_MAX)
      return `<div class="st-pd-axis" data-axis="${a.id}"><label class="st-pd-legend" for="${fid}">${esc(a.name_he)}</label>
<select id="${fid}" class="st-pd-select" data-axis="${a.id}">${a.values
        .map(
          (v) =>
            `<option value="${esc(v.id)}"${sel[a.id] === v.id ? ' selected' : ''}${ok.has(v.id) ? '' : ' disabled'}>${esc(v.label_he)}${ok.has(v.id) ? '' : ' (לא זמין בבחירה הזו)'}</option>`,
        )
        .join('')}</select></div>`;
    return `<fieldset class="st-pd-axis" data-axis="${a.id}"><legend class="st-pd-legend">${esc(a.name_he)}: <span class="st-pd-current">${esc(current)}</span></legend>
<div class="st-pd-values${swatches ? ' is-swatches' : ''}">${a.values
      .map((v) => {
        const off = !ok.has(v.id);
        return `<label class="st-pd-value${off ? ' is-off' : ''}"${swatches ? ` title="${esc(v.label_he)}"` : ''}><input type="radio" name="${fid}" value="${esc(v.id)}" data-axis="${a.id}"${sel[a.id] === v.id ? ' checked' : ''}${off ? ' disabled' : ''} />${v.hex ? `<span class="st-pd-swatch" style="--swatch: ${v.hex}" aria-hidden="true"></span>` : ''}<span class="${swatches ? 'st-sr' : 'st-pd-text'}">${esc(v.label_he)}</span>${off ? '<span class="st-sr"> (לא זמין בבחירה הזו)</span>' : ''}</label>`;
      })
      .join('')}</div></fieldset>`;
  })
  .join('\n')}
</div>`;
}
const whyHe = (d: DetailOut, sku: DetailSku): string =>
  d.status === 'unpriced' ? 'המחיר עוד לא נקבע, ולכן המוצר עוד לא במכירה.' : d.status === 'unavailable' || !sku.available ? 'המלאי אינו זמין כעת.' : '';
function detailBody(d: DetailOut, pg: PageOut): string {
  const sku = d.skus.find((k) => k.key === d.story_key)!;
  const head = headOf(pg);
  const crop = d.crop;
  const photo = sku.image ?? crop;
  const photoCap = sku.image
    ? sku.label_he && d.axes.length && sku.image_of_option
      ? `צילום הספק, באפשרות ${sku.label_he}.`
      : 'צילום הספק.'
    : crop
      ? d.crop_caption_he!
      : 'צילום הספק עוד לא הורד לגרסת הבדיקה.';
  // the crop is shown at its own size, never enlarged (§6); a close-up replaces it (the crop is not a second picture)
  const photoTag = sku.image
    ? imgTag(sku.image, `צילום הספק: ${d.name_he}`, '(max-width: 719px) calc(100vw - 48px), 36rem', 'st-pd-img', true)
    : crop
      ? `<img id="st-pd-img" class="is-frame" src="${crop.src}" alt="${esc(`${d.name_he}, מתוך הסיפור`)}" width="${crop.w}" height="${crop.h}" decoding="async" fetchpriority="high" />`
      : '<img id="st-pd-img" alt="" hidden />';
  const units = d.skus.some((k) => k.unit_price_agorot !== null);
  const packHtml =
    units && d.set_qty > 1
      ? `<fieldset class="st-pd-axis st-pd-pack" id="st-pd-pack"><legend class="st-pd-legend">איך לקנות</legend>
<div class="st-pd-values"><label class="st-pd-value"><input type="radio" name="st-pack" value="set" checked /><span class="st-pd-text">סט של ${d.set_qty} · <span class="num" data-pack-price="set">${sku.price_he ?? ''}</span></span></label>
<label class="st-pd-value"><input type="radio" name="st-pack" value="unit" /><span class="st-pd-text">יחידה בודדת · <span class="num" data-pack-price="unit">${sku.unit_price_he ?? ''}</span>${sku.unit_estimated ? ' (מחיר משוער)' : ''}</span></label></div></fieldset>`
      : '';
  const credit = [d.material_he, sku.size_he, sku.price_he ?? 'המחיר עוד לא נקבע'].filter(Boolean).join(' · ');
  const why = whyHe(d, sku);
  const specs = [
    d.materials_he.length ? ['חומרים', d.materials_he.join(', ')] : null,
    sku.size_he ? ['מידות', `${sku.size_he} (לפי הספק)`] : null,
    d.set_qty > 1 ? ['נמכר', `כסט של ${d.set_qty}`] : null,
    sku.days ? ['זמן אספקה', `⁦${sku.days[0]}–${sku.days[1]}⁩ ימים במשלוח החסכוני (הערכה של הספק)`] : null,
  ].filter((x): x is string[] => !!x);
  const here = d.here
    .map(
      (h) =>
        `<li class="st-tile"><a class="st-tile-link" href="${h.href}">${h.image ? `<span class="st-tile-pic">${imgTag(h.image, `${d.name_he}, בפריים "${h.title_he}"`, '(max-width: 719px) 44vw, 14rem')}</span>` : ''}<span class="st-tile-style">פריים ${esc(h.frame)} · <span class="num">${String(h.n).padStart(2, '0')}</span></span><span class="st-tile-title">${esc(h.title_he)}</span>${h.note_he ? `<span class="mag-cap">${esc(h.note_he)}</span>` : ''}${h.dot ? '' : '<span class="mag-cap">בלי נקודה בפריים הזה: כאן הוא עוד לא נאמן לכרטיס במלואו.</span>'}</a></li>`,
    )
    .join('\n');
  const elsewhere = d.elsewhere
    .map(
      (e) =>
        `<li class="st-tile"><a class="st-tile-link" href="${e.href}">${e.image ? `<span class="st-tile-pic">${imgTag(e.image, `${d.name_he}, ${e.house_he}`, '(max-width: 719px) 44vw, 14rem')}</span>` : ''}<span class="st-tile-title">${esc(e.house_he)}</span></a></li>`,
    )
    .join('\n');
  return `<nav class="mag-paper st-crumbs" aria-label="פירורי לחם"><div class="mag-grid"><ol class="mag-col-main">
  <li><a class="mag-link" href="/story/">תוכן</a></li>
  <li><a class="mag-link" href="${pg.href}">${esc(`${roomOf(pg.room).name_he} · ${styleOf(pg.style).name_he}`)}</a></li>
  <li aria-current="page">${esc(d.name_he)}</li>
</ol></div></nav>
<section class="mag-paper st-pd" id="detail" data-head="${esc(head)}" aria-labelledby="st-pd-title">
  <div class="mag-grid">
    <div class="st-pd-media${sku.closeup ? ' has-closeup' : ''}" id="st-pd-media">
      <figure class="st-pd-photo" id="st-pd-photo">
        ${photoTag}
        <span class="st-pd-none" id="st-pd-none"${photo ? ' hidden' : ''} style="--swatch: ${d.swatch}"><span class="st-swatch-lg" aria-hidden="true"></span><span>צילום הספק עוד לא הורד לגרסת הבדיקה.</span></span>
        <figcaption class="mag-cap" id="st-pd-photo-cap">${photo ? esc(photoCap) : ''}</figcaption>
      </figure>
      <figure class="st-pd-closeup" id="st-pd-closeup">
        ${sku.closeup ? imgTag(sku.closeup, sku.closeup.alt_he, '(max-width: 719px) calc(100vw - 48px), 36rem', 'st-pd-cu', true) : '<img id="st-pd-cu" alt="" hidden />'}
        <span class="st-pd-empty" id="st-pd-cu-empty"${sku.closeup ? ' hidden' : ''}><span class="st-type-rule" aria-hidden="true"></span><span class="st-pd-empty-title">תקריב באור של הבית</span><span class="mag-cap">בהכנה: התקריב של המוצר${d.axes.length ? ' ושל כל אפשרות שלו' : ''} עוד לא צולם.</span></span>
        <figcaption class="mag-cap" id="st-pd-cu-cap">${sku.closeup ? esc(`תקריב בבית ה${styleOf(d.style).name_he}. ${markOf(sku.closeup.state)}.`) : esc(`תקריב בבית ה${styleOf(d.style).name_he}`)}</figcaption>
      </figure>
    </div>
    <div class="st-pd-info">
      <p class="st-kicker">${esc(head)}</p>
      <h1 id="st-pd-title" class="mag-h1 st-pd-title" tabindex="-1">${esc(sku.title_he)}</h1>
      <p class="mag-credit-detail st-pd-credit" id="st-pd-credit">${esc(credit)}</p>
      <p class="st-pd-price num" id="st-pd-price" aria-live="polite"${sku.price_he ? '' : ' hidden'}>${sku.price_he ?? ''}</p>
      ${pickerHtml(d, sku)}
      ${packHtml}
      <p class="mag-cap st-pd-story-note" id="st-pd-story-note" hidden><span id="st-pd-story-text"></span> <button type="button" class="st-link-btn" id="st-pd-back">חזרה לאפשרות שבסיפור</button></p>
      <div class="st-actions">
        <button type="button" class="mag-btn mag-btn-primary" id="st-pd-add"${sku.sellable ? '' : ' hidden'}>הוספה לסל</button>
        <p class="mag-cap st-why" id="st-pd-why"${why ? '' : ' hidden'}>${esc(why)}</p>
        <p class="mag-cap st-in-cart num" id="st-pd-in-cart" hidden></p>
      </div>
      ${d.notes_he.length ? `<ul class="st-notes">${d.notes_he.map((n) => `<li>${esc(n)}</li>`).join('')}</ul>` : ''}
      ${specs.length ? `<dl class="st-pd-specs" id="st-pd-specs">${specs.map(([k, v]) => `<div><dt>${esc(k!)}</dt><dd data-spec="${esc(k!)}">${esc(v!)}</dd></div>`).join('')}</dl>` : ''}
      <p class="st-links">${d.try_href ? `<a class="mag-link" id="st-pd-try" href="${esc(d.try_href)}">לנסות בחדר: עצב בעצמך</a>` : `<span class="mag-cap" id="st-pd-try-none">בכלי "עצב בעצמך" המוצר הזה עוד לא על הגלגל${pg.pair.tool ? '' : ': הכלי של הבית הזה בבנייה'}.</span>`}</p>
      <p class="mag-cap">ביטול עסקה והחזרות לפי חוק הגנת הצרכן. <a class="mag-link" href="/returns/">פרטים</a></p>
    </div>
  </div>
</section>
<section class="mag-paper st-houses st-pd-here" id="here" data-head="בחדר הזה" aria-labelledby="here-title">
  <div class="mag-grid">
    <h2 id="here-title" class="mag-h2 mag-col-main">בחדר הזה</h2>
    <p class="mag-lead mag-col-main">${esc(`${d.here.length === 1 ? 'פעם אחת' : `${d.here.length} פעמים`} בסיפור של ${roomOf(pg.room).name_he} בבית ה${styleOf(pg.style).name_he}. נגיעה חוזרת לפריים.`)}</p>
    <ol class="st-tiles">
${here}
    </ol>
  </div>
</section>
${
  d.elsewhere.length
    ? `<section class="mag-paper st-houses st-pd-elsewhere" id="elsewhere" data-head="בבתים אחרים" aria-labelledby="elsewhere-title">
  <div class="mag-grid">
    <h2 id="elsewhere-title" class="mag-h2 mag-col-main">גם בבתים אחרים</h2>
    <ol class="st-tiles">
${elsewhere}
    </ol>
  </div>
</section>`
    : ''
}`;
}
const template = readFileSync(sitePath('tools/story/page.template.html'), 'utf8');
function render(file: string, fill: Record<string, string>): string {
  let html = template;
  for (const [k, v] of Object.entries({ ...fill, REGISTER: `${register.version}` })) html = html.split(`{{${k}}}`).join(v);
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
    // the frame's crop of each product serves the detail page only
    items: Object.fromEntries(pg.frames.flatMap((f) => f.items.map((x) => [x.id, { ...x, crop_image: undefined }]))),
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
  console.log(
    `${pg.href} → web${pg.href}index.html (${(html.length / 1024).toFixed(1)} KB): ${pg.frames.length ? pg.frames.map((f) => `${f.id} ${f.state}`).join(', ') : 'typographic'}`,
  );
}
for (const d of details) {
  const pg = pages.find((x) => x.room === d.room && x.style === d.style)!;
  // the SKUs of one picture share it: the picture is listed once and named by its index
  const images: Image[] = [];
  const ix = (im: Image | null): number | null => {
    if (!im) return null;
    const at = images.findIndex((x) => x.src === im.src);
    return at >= 0 ? at : images.push(im) - 1;
  };
  const skus = d.skus.map((k) => ({ ...k, image: ix(k.image) }));
  const data = {
    page: { room: d.room, style: d.style, href: d.href, tool: pg.pair.tool ?? story.tool_fallback },
    items: {},
    frames: [],
    detail: {
      product: d.product,
      name_he: d.name_he,
      material_he: d.material_he,
      status: d.status,
      set_qty: d.set_qty,
      style_he: styleOf(d.style).name_he,
      axes: d.axes,
      skus,
      images,
      story_key: d.story_key,
      crop: d.crop,
      crop_caption_he: d.crop_caption_he,
      swatch: d.swatch,
      marks_he: story.marks_he,
    },
  };
  resolved[d.href] = {
    detail: {
      ...data.detail,
      skus: d.skus.length,
      here: d.here.map((h) => h.item),
      elsewhere: d.elsewhere.map((e) => e.href),
      try_href: d.try_href,
      closeups_held: d.closeups_held,
    },
  };
  const html = render(`web${d.href}index.html`, {
    TITLE: esc(`${d.name_he} · ${roomOf(d.room).name_he} · ${styleOf(d.style).name_he}`),
    DESCRIPTION: esc(`${d.name_he}, ב${roomOf(d.room).name_he} של הבית ה${styleOf(d.style).name_he}. גרסת בדיקה.`),
    ISSUE: esc(story.issue_he),
    KIND: 'detail',
    HEAD_ON: 'paper',
    CONTENTS_CURRENT: '',
    NAV_TOOL: esc(d.try_href ?? pg.pair.tool ?? story.tool_fallback),
    SKIP: '#detail',
    SKIP_HE: 'דילוג לפרטי המוצר',
    TOOL_HREF: esc(d.try_href ?? pg.pair.tool ?? story.tool_fallback),
    BODY: [detailBody(d, pg), footer('')].join('\n'),
    DATA: JSON.stringify(data).replace(/</g, '\\u003c'),
  });
  if (html.length > 120_000) console.warn(`${d.href}: ${(html.length / 1024).toFixed(0)} KB of HTML`);
}
console.log(
  `layer 2: ${details.length} detail pages (${details.filter((d) => d.status === 'available').length} for sale, ${details.filter((d) => d.status === 'unpriced').length} without a price, ${details.filter((d) => d.status === 'unavailable').length} not sold now); ${details.filter((d) => d.skus.some((k) => k.image)).length} with a card photo; close-ups shown ${details.reduce((n, d) => n + d.skus.filter((k) => k.closeup).length, 0)}, held ${details.reduce((n, d) => n + d.closeups_held, 0)}`,
);
// ---------- S3: the house's own tool, a draft (DIR2), with the soft switch between two houses ----------
const TOOL_WIDTHS = [1280, 1920, 2720];
async function toolLayers(room: string, house: string, frame: string, list: ToolDraft['layers']) {
  const dir = join(OUT, 'tool', room, house, frame);
  const url = `${URL_BASE}/tool/${room}/${house}/${frame}`;
  mkdirSync(dir, { recursive: true });
  const layers: { id: string; blend: string; base: string; w: number; h: number }[] = [];
  for (const l of list) {
    const src = repoPath(l.src);
    // named by the source's content time: a new render makes new files
    const key = createHash('sha256')
      .update(`${l.src}:${statSync(src).mtimeMs}`)
      .digest('hex')
      .slice(0, 8);
    const img = sharp(src);
    const meta = await img.metadata();
    for (const w of TOOL_WIDTHS) {
      const b = join(dir, `${l.id}.${key}.${w}`);
      if (existsSync(`${b}.webp`) && existsSync(`${b}.avif`)) continue;
      const r = img.clone().resize({ width: w, withoutEnlargement: true });
      await r.clone().avif({ quality: 55, effort: 4 }).toFile(`${b}.avif`);
      await r.clone().webp({ quality: 78, effort: 4 }).toFile(`${b}.webp`);
    }
    layers.push({ id: l.id, blend: l.blend, base: `${url}/${l.id}.${key}`, w: meta.width!, h: meta.height! });
  }
  return layers;
}
async function toolDraftPage(pg: PageOut, t: ToolDraft): Promise<void> {
  const layers = await toolLayers(pg.room, pg.style, t.frame, t.layers);
  const others = await toolLayers(pg.room, t.compare.house, t.frame, t.compare.layers);
  const sizes = '(max-width: 719px) 160vw, 100vw';
  const pic = (base: string, widths: number[], w: number, h: number, cls: string, eager: boolean) =>
    `<picture class="st-td-layer ${cls}"><source type="image/avif" srcset="${widths.map((x) => `${base}.${x}.avif ${Math.min(x, w)}w`).join(', ')}" sizes="${sizes}" /><img src="${base}.${widths[1]}.webp" srcset="${widths.map((x) => `${base}.${x}.webp ${Math.min(x, w)}w`).join(', ')}" sizes="${sizes}" alt="" width="${w}" height="${h}" decoding="async"${eager ? ' fetchpriority="high"' : ' loading="lazy"'} /></picture>`;
  const house = styleOf(pg.style).name_he;
  const other = styleOf(t.compare.house).name_he;
  const head = `${roomOf(pg.room).n} · ${roomOf(pg.room).name_he} · ${house} · הכלי`;
  const body = `<section class="st-td" id="tool-draft" data-head="${esc(head)}" aria-labelledby="td-title" style="--td-cu: ${t.mobile_center_u}">
  <div class="st-td-stage" id="td-stage">
    <div class="st-td-house is-on" data-house="${pg.style}" role="img" aria-label="${esc(`${roomOf(pg.room).name_he} בבית ה${house}, במצלמה של הכלי: טיוטה מהפיילוט`)}">
      ${layers.map((l, i) => pic(l.base, TOOL_WIDTHS, l.w, l.h, `is-${l.blend}`, i === 0)).join('\n      ')}
    </div>
    <div class="st-td-house" data-house="${t.compare.house}" role="img" aria-label="${esc(t.compare.alt_he)}" aria-hidden="true">
      ${others.map((l) => pic(l.base, TOOL_WIDTHS, l.w, l.h, `is-${l.blend}`, false)).join('\n      ')}
    </div>
    <p class="st-draft is-almost">טיוטה / בדיקה · הכלי בבנייה</p>
  </div>
  <div class="mag-paper st-td-text">
    <div class="mag-grid">
      <div class="st-td-switch mag-col-main" role="group" aria-label="הבית">
        <button type="button" class="st-td-btn" aria-pressed="true" data-house="${pg.style}">${esc(house)}</button>
        <button type="button" class="st-td-btn" aria-pressed="false" data-house="${t.compare.house}">${esc(other)}</button>
      </div>
      <p class="st-kicker mag-col-main">${esc(head)}</p>
      <h1 id="td-title" class="mag-h1 mag-col-main">עצב בעצמך, בבית ה${esc(house)}</h1>
      <p class="mag-lead mag-col-main">אותה מצלמה ואותן עמדות כמו בבית ה${esc(other)}, אדריכלות אחרת. מעבר בין הבתים בכלי הוא מעבר רך של כל השכבות באותו פריים, כשנייה.</p>
      <p class="st-type-status mag-col-main"><span class="st-type-rule" aria-hidden="true"></span>${esc(t.status_he)}</p>
      <p class="mag-cap mag-col-main">הבית ה${esc(other)} במתג: המעטפת בלבד, מאותה מצלמה (M0 1.2), מהצינור הנעול של הבית הנורדי. גם היא טיוטה, ועוד לא אושרה לאתר.</p>
      <p class="mag-col-main st-tool-row"><a class="mag-btn mag-btn-secondary st-btn-link" href="${esc(`${story.tool_fallback}?from=${encodeURIComponent(pg.href)}`)}">לכלי הפעיל: הסלון בבית הנורדי</a> <a class="mag-link" href="${pg.href}">חזרה לסיפור של הבית</a></p>
    </div>
  </div>
</section>`;
  const href = `${pg.href}tool/`;
  render(`web${href}index.html`, {
    TITLE: esc(`עצב בעצמך · ${roomOf(pg.room).name_he} · ${house} · טיוטה`),
    DESCRIPTION: esc(`טיוטת הכלי של ${roomOf(pg.room).name_he} בבית ה${house}. גרסת בדיקה.`),
    ISSUE: esc(story.issue_he),
    KIND: 'tool-draft',
    HEAD_ON: 'stage',
    CONTENTS_CURRENT: '',
    NAV_TOOL: '#tool-draft',
    SKIP: '#td-title',
    SKIP_HE: 'דילוג להסבר',
    TOOL_HREF: esc(story.tool_fallback),
    BODY: [body, footer('הכלי של הבית הוא טיוטה מפיילוט הרינדור, שעוד לא עבר QA.')].join('\n'),
    DATA: JSON.stringify({ page: { room: pg.room, style: pg.style, href, tool: story.tool_fallback, kind: 'tool-draft' }, items: {}, frames: [] }),
  });
  console.log(
    `${href} → the house's draft tool: ${layers.map((l) => `${l.id} (${l.blend})`).join(', ')}; the soft switch to the ${t.compare.house} house: ${others.map((l) => l.id).join(', ')}`,
  );
}
for (const pg of pages) if (pg.pair.tool_draft) await toolDraftPage(pg, pg.pair.tool_draft);

// ---------- the test checkout (S4): the site's fields and rules, nothing charged, nothing sent ----------
const field = (k: string, label: string, attrs: string, hint = '') =>
  `<div class="st-co-field"><label for="f-${k}">${label}</label><input id="f-${k}" name="${k}" ${attrs} aria-describedby="err-${k}${hint ? ` hint-${k}` : ''}" />${hint ? `<p class="mag-cap" id="hint-${k}">${hint}</p>` : ''}<p class="st-co-err" id="err-${k}" hidden></p></div>`;
const shipping = site.shipping;
const checkoutBody = `<section class="mag-paper st-co" id="checkout" data-head="תשלום" aria-labelledby="co-title">
  <div class="mag-grid">
    <div class="st-co-main">
      <p class="st-kicker">סל הבדיקה</p>
      <h1 id="co-title" class="mag-h1">תשלום</h1>
      <p class="mag-cap">תשלום בדיקה: לא ייגבה כסף, וההזמנה לא תישלח לספק.</p>
      <p class="mag-lead" id="co-empty" hidden>הסל ריק. <a class="mag-link" href="/story/">לתוכן הגיליון</a></p>
      <form id="co-form" class="st-co-form" novalidate>
        <div id="co-errors" class="st-co-errors" role="alert" tabindex="-1" hidden></div>
        <fieldset class="st-co-set"><legend class="mag-h3">פרטים</legend>
          ${field('full_name', 'שם מלא', 'autocomplete="name" required')}
          ${field('email', 'אימייל', 'type="email" autocomplete="email" inputmode="email" dir="ltr" required', 'לשם נשלחים אישור ההזמנה והחשבונית.')}
          ${field('phone', 'טלפון', 'type="tel" autocomplete="tel" inputmode="tel" dir="ltr" required', 'לשליח, למשל 050-1234567.')}
        </fieldset>
        <fieldset class="st-co-set"><legend class="mag-h3">כתובת למשלוח</legend>
          ${field('city', 'עיר', 'autocomplete="address-level2" required')}
          ${field('street', 'רחוב', 'autocomplete="address-line1" required')}
          ${field('house', 'מספר בית', 'inputmode="numeric" required')}
          <div class="st-co-field"><label for="f-apartment">דירה (רשות)</label><input id="f-apartment" name="apartment" autocomplete="address-line2" /></div>
          ${field('zip', 'מיקוד (רשות)', 'inputmode="numeric" autocomplete="postal-code" dir="ltr"')}
          <div class="st-co-field"><label for="f-notes">הערות לשליח (רשות)</label><textarea id="f-notes" name="notes" rows="2" maxlength="200"></textarea></div>
        </fieldset>
        <fieldset class="st-co-set"><legend class="mag-h3">משלוח</legend>
          ${shipping
            .map(
              (m) =>
                `<label class="st-co-choice"><input type="radio" name="shipping" value="${m.id}"${m.is_default ? ' checked' : ''} /><span><strong>${esc(m.label_he)}</strong> · <span class="num" data-ship-price="${m.id}">${formatIls(m.price_agorot)}</span><span class="mag-cap"> ${esc(m.days_he)}${m.free_over_agorot !== null ? `. חינם מעל ${formatIls(m.free_over_agorot)}` : ''}</span></span></label>`,
            )
            .join('\n          ')}
        </fieldset>
        <div class="st-co-field"><label class="st-co-check"><input type="checkbox" id="f-terms" name="terms" aria-describedby="err-terms" /> <span>קראתי ואני מאשר/ת את <a class="mag-link" href="/terms/">התקנון</a> ואת <a class="mag-link" href="/returns/">מדיניות הביטולים</a></span></label><p class="st-co-err" id="err-terms" hidden></p></div>
        <div class="st-co-field"><label class="st-co-check"><input type="checkbox" id="f-marketing" name="marketing" /> <span>אשמח לקבל עדכונים על מוצרים חדשים במייל (רשות, אפשר להסיר בכל עת).</span></label></div>
        <p><button type="submit" class="mag-btn mag-btn-primary" id="co-pay">לתשלום (בדיקה)</button></p>
      </form>
    </div>
    <aside class="st-co-summary" aria-labelledby="co-sum-title">
      <h2 id="co-sum-title" class="mag-h2">ההזמנה</h2>
      <ol class="mag-credits" id="co-lines"></ol>
      <p class="mag-cap" id="co-held" hidden></p>
      <dl class="st-pd-specs st-co-totals">
        <div><dt>סכום ביניים</dt><dd id="co-subtotal" class="num"></dd></div>
        <div><dt>משלוח</dt><dd id="co-shipping" class="num"></dd></div>
        <div><dt>סה״כ לתשלום</dt><dd id="co-total" class="num"></dd></div>
      </dl>
      <p class="mag-cap" id="co-free"></p>
      <p class="mag-cap">המחירים כוללים מע״מ.</p>
    </aside>
  </div>
</section>`;
const orderBody = `<section class="mag-paper st-co" id="order" data-head="הזמנת בדיקה" aria-labelledby="or-title">
  <div class="mag-grid">
    <div class="st-co-main">
      <p class="st-kicker">הזמנת בדיקה</p>
      <h1 id="or-title" class="mag-h1" tabindex="-1">ההזמנה התקבלה</h1>
      <div id="or-found" hidden>
        <p class="mag-lead"><span id="or-greeting"></span> מספר ההזמנה: <strong class="num" id="or-number"></strong>. <span id="or-city"></span></p>
        <ol class="mag-credits" id="or-lines"></ol>
        <p class="st-total" id="or-sum"></p>
      </div>
      <p class="mag-lead" id="or-missing" hidden>לא מצאנו את ההזמנה בדפדפן הזה. הזמנות הבדיקה נשמרות רק בדפדפן שבו הן נעשו.</p>
      <p class="mag-cap">זו הזמנת בדיקה: לא נגבה כסף, ושום דבר לא נשלח לספק.</p>
      <p><a class="mag-link" href="/story/">חזרה לתוכן הגיליון</a></p>
    </div>
  </div>
</section>`;
const sellTable: Record<string, [number, number | null, 0 | 1, number]> = {};
for (const x of pages.flatMap((pg) => pg.frames.flatMap((f) => f.items)))
  if (x.variant_id && x.price_agorot !== null) sellTable[x.variant_id] = [x.price_agorot, null, x.status === 'available' ? 1 : 0, x.set_qty];
for (const d of details)
  for (const k of d.skus)
    if (k.variant_id && k.price_agorot !== null) sellTable[k.variant_id] = [k.price_agorot, k.unit_price_agorot, k.sellable ? 1 : 0, d.set_qty];
for (const [kind, href, title, body, skip] of [
  ['checkout', '/story/checkout/', 'תשלום', checkoutBody, '#co-form'],
  ['order', '/story/order/', 'הזמנת בדיקה', orderBody, '#order'],
] as const)
  render(`web${href}index.html`, {
    TITLE: esc(`${title} · ${story.issue_he}`),
    DESCRIPTION: esc(`${title} בסל הבדיקה של הגיליון. גרסת בדיקה: לא נגבה כסף.`),
    ISSUE: esc(story.issue_he),
    KIND: kind,
    HEAD_ON: 'paper',
    CONTENTS_CURRENT: '',
    NAV_TOOL: esc(story.tool_fallback),
    SKIP: skip,
    SKIP_HE: 'דילוג לתוכן העמוד',
    TOOL_HREF: esc(story.tool_fallback),
    BODY: [body, footer('')].join('\n'),
    // QA on S4: the checkout re-checks every line against the story as built now (price, sold or not), never the
    // snapshot a line kept from the page it was added on: variant → [price, single-piece price, for sale, set size]
    DATA: JSON.stringify({ page: { room: null, style: null, href, tool: story.tool_fallback, kind }, items: {}, frames: [], shipping, v: sellTable }).replace(
      /</g,
      '\\u003c',
    ),
  });
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
console.log(
  `/story/ → web/story/index.html (${(indexHtml.length / 1024).toFixed(1)} KB): ${story.rooms.length} rooms × ${story.styles.length} styles, ${pages.length} pages`,
);
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
