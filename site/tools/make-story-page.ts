/**
 * The story-first prototype (briefs/site-story-prototype-2026-11-07.md; DIR1): a full story frame per room and style,
 * a quiet dot per starring product, "קנה את המראה" (the product, its card's photo, the price from the site's pricing
 * code, add to cart against an in-browser mock), "כל המוצרים בתמונה", and the way into "עצב בעצמך" (the room engine).
 * TEST ONLY, on /test/story/: the frames are editorial test frames, never site assets.
 *
 *   tsx tools/build-catalog.ts --rooms=living-room --products=tools/test-page/story-hotspots.json --out=story
 *   tsx tools/make-story-page.ts
 *
 * Reads
 *   tools/test-page/story.json            the frames, their story lines and crops, the QA gate
 *   tools/test-page/story-hotspots.json   the temporary points (by eye), one per starring product
 *   qa/reports/2026-11-07-editorial-fin2-ed4-country.json   the gate: a frame goes in only when QA called it ready or almost
 *   .generated/catalog.story.full.json    every product of the frames, priced by the site's pricing code
 *   .generated/catalog.public.json        the site's own catalog: a product page link, and the slot in the room engine
 *   .cache/supplier-images/               the card photos already downloaded by tools/supplier-images.ts (no network here)
 * Writes
 *   web/public/media/test/story/<frame>/{1280,1920,2720}.{avif,webp}   the frames
 *   web/public/media/test/story/products/<id>/<key>.{160,480,800}.webp  the card photo of each product shown
 *   .generated/test-page.story.json                                    the resolved items (what the page's data block holds)
 *   web/test/story/index.html                                          the page, from tools/test-page/story.template.html
 */
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import sharp from 'sharp';
import { formatIls } from '@hd/shared/money';
import { expandOptions, type FullCatalog, type FullProduct, type PublicCatalog } from '@hd/shared';
import { GENERATED, MEDIA_OUT, repoPath, sitePath } from './lib/paths';

type FrameSpec = {
  role: 'opening' | 'story' | 'other-style';
  n: string;
  room_he: string;
  style_he: string;
  u0: number;
  v0: number;
  mobile_window_u: number;
  title_he: string;
  line_he: string;
  alt_he: string;
  note_he: string;
  draft_he?: string;
};
type Manifest = {
  issue_he: string;
  mark_he: string;
  qa_record: string;
  allowed_verdicts: string[];
  hotspots: string;
  catalog: string;
  site_catalog: string;
  tool: { href: string; room: string };
  frames: Record<string, FrameSpec>;
  next_styles_he: string[];
};
type Point = { product: string; u: number; v: number; by_eye: boolean; option?: Record<string, string>; option_label_he?: string; in_frame_he?: string };
type Hotspots = { status: string; frames: Record<string, { src: string; qa_key: string; points: Point[] }> };
type QaRecord = { final_test: Record<string, string>; frames: Record<string, { rows: { card: string; present: boolean }[] }> };
type Card = {
  id: string;
  slot: string;
  colors: { dominant_hex: string };
  images: { urls: string[] };
  options?: { default_sku: string; skus: { id: string; values: Record<string, string>; image?: string }[] };
};
type Image = { src: string; srcset: string; w: number; h: number };
type StoryItem = {
  id: string;
  frame: string;
  n: number;
  product: string;
  u: number;
  v: number;
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

const read = <T>(p: string): T => JSON.parse(readFileSync(p, 'utf8')) as T;
const man = read<Manifest>(sitePath('tools/test-page/story.json'));
const hot = read<Hotspots>(sitePath(man.hotspots));
const qa = read<QaRecord>(repoPath(man.qa_record));
for (const p of [man.catalog, man.site_catalog])
  if (!existsSync(sitePath(p))) {
    console.error(`${p} is missing: run npm run catalog, then tsx tools/build-catalog.ts --rooms=living-room --products=${man.hotspots} --out=story`);
    process.exit(1);
  }
const story = read<FullCatalog>(sitePath(man.catalog));
const site = read<PublicCatalog>(sitePath(man.site_catalog));
const OUT = join(MEDIA_OUT, 'test', 'story');
const URL_BASE = '/media/test/story';
const WIDTHS = [1280, 1920, 2720];
const PHOTO_WIDTHS = [160, 480, 800];

// ---------- the gate: only the frames QA called "final test" or "almost" (QA report 2026-11-07 §4) ----------
for (const [id, f] of Object.entries(hot.frames)) {
  const verdict = qa.final_test[f.qa_key];
  if (!verdict || !man.allowed_verdicts.some((v) => verdict.startsWith(v)))
    throw new Error(`${id} (${f.qa_key}): QA verdict "${verdict ?? 'none'}" is not ${man.allowed_verdicts.join(' / ')}; it does not go on the page`);
  if (!man.frames[id]) throw new Error(`${id}: no entry in story.json`);
  // every card QA listed in the frame has a point (the fixed furniture has no card)
  const listed = qa.frames[f.qa_key]!.rows.filter((r) => r.present && !r.card.startsWith('fixed furniture')).map((r) => r.card.split(' ')[0]!);
  const missing = listed.filter((c) => !f.points.some((p) => p.product === c));
  if (missing.length) throw new Error(`${id}: QA lists ${missing.join(', ')} in the frame, and it has no point`);
}

// ---------- the cards (photos, options) and the slots' placement (the credit's defining size) ----------
function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    return statSync(p).isDirectory() ? walk(p) : p.endsWith('.json') ? [p] : [];
  });
}
const wanted = new Set(Object.values(hot.frames).flatMap((f) => f.points.map((p) => p.product)));
const cards = new Map<string, Card>();
for (const p of walk(repoPath('data/products'))) {
  const c = read<Card>(p);
  if (wanted.has(c.id)) cards.set(c.id, c);
}
const placement = new Map<string, string>(
  read<{ slots: { id: string; placement: string }[] }>(repoPath('data/slots/living-room.json')).slots.map((s) => [s.id, s.placement]),
);

// ---------- images ----------
const cacheOf = (url: string) => sitePath('.cache/supplier-images', `${createHash('sha256').update(url).digest('hex').slice(0, 24)}.bin`);
const fresh = (out: string, srcMtime: number) => existsSync(out) && statSync(out).mtimeMs > srcMtime;
async function lqip(img: sharp.Sharp): Promise<string> {
  const buf = await img.clone().resize(32, 18, { fit: 'fill' }).webp({ quality: 40 }).toBuffer();
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
    if (!fresh(out, statSync(file).mtimeMs)) await img.clone().resize({ width: w, withoutEnlargement: true }).webp({ quality: 78 }).toFile(out);
    srcs.push(`${URL_BASE}/products/${card.id}/${key}.${w}.webp ${Math.min(w, meta.width ?? w)}w`);
  }
  const w = Math.min(800, meta.width ?? 800);
  return { src: `${URL_BASE}/products/${card.id}/${key}.480.webp`, srcset: srcs.join(', '), w, h: Math.round((w * (meta.height ?? w)) / (meta.width ?? w)) };
}

// ---------- the credit (art direction §4.4–§4.5): material · the defining size · price ----------
function sizeHe(p: FullProduct, place: string): string | null {
  const { width: w, depth: d, height: h } = p.dimensions_cm;
  const x = (a: number, b: number) => `⁦${a}×${b}⁩ ס״מ`;
  if ((place === 'floor' || place === 'sofa') && w && d) return x(w, d);
  if (place === 'wall' && w && h) return x(w, h);
  if (h) return `גובה ⁦${h}⁩ ס״מ`;
  if (w && d) return x(w, d);
  if (w) return `רוחב ⁦${w}⁩ ס״מ`;
  return null;
}
const sitePages = new Set(site.products.map((p) => p.id));
const room = site.rooms.find((r) => r.id === man.tool.room);
/** the room engine opens on the slot, with this product on the wheel, when the product is one of the slot's options */
function tryHref(productId: string): string | null {
  for (const s of room?.slots ?? []) {
    const o = s.options.find((x) => x.product_id === productId);
    if (o) return `${man.tool.href}?slot=${encodeURIComponent(s.id)}&option=${o.position}`;
  }
  return null;
}
/** reading order in a right-to-left page: top to bottom in bands, right to left inside a band */
const readingOrder = (a: Point, b: Point) => Math.floor(a.v / 0.25) - Math.floor(b.v / 0.25) || b.u - a.u;

async function itemOf(frame: string, n: number, pt: Point): Promise<StoryItem> {
  const card = cards.get(pt.product);
  if (!card) throw new Error(`${frame}: no product card ${pt.product}`);
  const p = story.products.find((x) => x.id === pt.product) ?? null;
  const why = story.hidden.find((h) => h.id === pt.product)?.reason ?? null;
  if (!p && !why) throw new Error(`${pt.product} is not in ${man.catalog}: build it with --products=${man.hotspots}`);
  // the option the frame shows: the room's SKU with the point's values instead
  let optionHe: string | null = null;
  let skuImage: string | null = null;
  let price = p?.price_agorot ?? null;
  let variant = p?.variants[0]?.id ?? null;
  let available = p?.availability.status === 'available';
  if (pt.option) {
    const o = p?.options ? expandOptions(p.id, p.options) : null;
    const cardSku = card.options?.skus.find((s) => s.id === card.options!.default_sku);
    const want = { ...(cardSku?.values ?? {}), ...pt.option };
    const sku = o?.skus.find((s) => Object.entries(want).every(([k, v]) => s.values[k] === v));
    if (p && !sku) throw new Error(`${frame}: ${pt.product} has no option ${JSON.stringify(want)}`);
    if (sku) {
      price = sku.price_agorot;
      variant = sku.variant_id;
      available &&= sku.available;
    }
    const axis = Object.keys(pt.option)[0]!;
    optionHe = pt.option_label_he ?? o?.axes.find((a) => a.id === axis)?.values.find((v) => v.id === pt.option![axis])?.label_he ?? null;
    skuImage = card.options?.skus.find((s) => Object.entries(want).every(([k, v]) => s.values[k] === v))?.image ?? null;
  } else if (card.options) skuImage = card.options.skus.find((s) => s.id === card.options!.default_sku)?.image ?? null;
  // the name: the option the frame shows replaces the colour in the name, or follows it (art direction §4.5)
  let name = p?.name_he ?? pt.product;
  if (optionHe) name = pt.option?.color && name.includes(', ') ? `${name.slice(0, name.lastIndexOf(', '))}, ${optionHe}` : `${name} — ${optionHe}`;
  const place = placement.get(card.slot) ?? 'surface';
  const priceHe = price !== null ? formatIls(price) : null;
  const detail = p
    ? [p.materials_he[0] ?? null, sizeHe(p, place), priceHe].filter((x): x is string => !!x).join(' · ')
    : 'המחיר עוד לא נקבע';
  const img = await photo(card, skuImage);
  // the catalog's notes describe the room engine's frame ("בתמונה: ..."): the story frame brings its own caption
  const notes = [...(pt.in_frame_he ? [pt.in_frame_he] : []), ...(p?.notes_he.filter((x) => !x.startsWith('בתמונה')) ?? [])];
  if (p?.pack) notes.push(`נמכר כסט של ${p.pack.set_qty}.`);
  return {
    id: `${frame}-${n}`,
    frame,
    n,
    product: pt.product,
    u: pt.u,
    v: pt.v,
    name_he: name,
    detail_he: detail,
    price_he: priceHe,
    price_agorot: price,
    variant_id: p ? variant : null,
    option_he: optionHe,
    status: !p ? 'unpriced' : available ? 'available' : 'unavailable',
    set_qty: p?.pack?.set_qty ?? 1,
    notes_he: notes,
    image: img,
    thumb: img ? img.srcset.split(', ')[0]!.split(' ')[0]! : null,
    swatch: card.colors.dominant_hex,
    href: sitePages.has(pt.product) ? `/p/${pt.product}/` : null,
    try_href: tryHref(pt.product),
  };
}

// ---------- the frames ----------
type FrameOut = FrameSpec & { id: string; width: number; height: number; aspect: number; lqip: string; srcset: string[]; items: StoryItem[] };
const frames: FrameOut[] = [];
for (const [id, f] of Object.entries(hot.frames)) {
  const spec = man.frames[id]!;
  const src = repoPath(f.src);
  const mtime = statSync(src).mtimeMs;
  const img = sharp(src);
  const meta = await img.metadata();
  mkdirSync(join(OUT, id), { recursive: true });
  for (const w of WIDTHS) {
    const base = join(OUT, id, String(w));
    if (fresh(`${base}.avif`, mtime) && fresh(`${base}.webp`, mtime)) continue;
    const r = img.clone().resize({ width: w, withoutEnlargement: true });
    await r.clone().avif({ quality: 52, effort: 4 }).toFile(`${base}.avif`);
    await r.clone().webp({ quality: 74, effort: 4 }).toFile(`${base}.webp`);
  }
  const points = [...f.points].sort(readingOrder);
  const items: StoryItem[] = [];
  for (const [i, pt] of points.entries()) items.push(await itemOf(id, i + 1, pt));
  frames.push({
    ...spec,
    id,
    width: meta.width!,
    height: meta.height!,
    aspect: meta.width! / meta.height!,
    lqip: await lqip(img),
    srcset: WIDTHS.map((w) => `${URL_BASE}/${id}/${w}`),
    items,
  });
  const priced = items.filter((x) => x.status !== 'unpriced').length;
  console.log(`${id}: ${meta.width}×${meta.height}, ${items.length} products (${priced} priced, ${items.filter((x) => x.image).length} with the card photo)`);
}

// ---------- the page ----------
const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const F = (id: string) => frames.find((f) => f.id === id)!;
const head = (f: FrameOut) => `${f.n} · ${f.room_he} · ${f.style_he}`;
function picture(f: FrameOut, eager: boolean): string {
  const set = (ext: string) => f.srcset.map((s, i) => `${s}.${ext} ${Math.min(WIDTHS[i]!, f.width)}w`).join(', ');
  // the phone shows the frame at full height in a horizontal scroller (its aspect × the viewport height wide)
  const sizes = `(max-width: 719px) ${Math.round(f.aspect * 100)}svh, 100vw`;
  return `<img class="mag-lqip" src="${f.lqip}" alt="" aria-hidden="true" width="${f.width}" height="${f.height}" style="object-position: ${(f.u0 * 100).toFixed(1)}% ${(f.v0 * 100).toFixed(1)}%" />
<picture class="mag-pic">
  <source type="image/avif" srcset="${set('avif')}" sizes="${sizes}" />
  <img src="${f.srcset[1]}.webp" srcset="${set('webp')}" sizes="${sizes}" alt="${esc(f.alt_he)}" width="${f.width}" height="${f.height}" decoding="async" ${eager ? 'fetchpriority="high"' : 'loading="lazy"'} style="object-position: ${(f.u0 * 100).toFixed(1)}% ${(f.v0 * 100).toFixed(1)}%" />
</picture>`;
}
const status = (x: StoryItem) => (x.status === 'unavailable' ? '. המלאי אינו זמין כעת' : '');
const marks = (f: FrameOut) =>
  f.items
    .map(
      (x) =>
        `<button type="button" class="mag-mark st-mark" data-item="${x.id}" style="--u: ${x.u}; --v: ${x.v}" aria-haspopup="dialog" aria-label="${esc(`${x.name_he}. ${x.detail_he}${status(x)}. קנה את המראה`)}"><span class="mag-dot" aria-hidden="true"></span></button>`,
    )
    .join('\n');
const swatch = (x: StoryItem) =>
  x.thumb
    ? `<img class="st-thumb" src="${x.thumb}" alt="" width="64" height="64" loading="lazy" decoding="async" />`
    : `<span class="st-thumb st-swatch" style="--swatch: ${x.swatch}" aria-hidden="true"></span>`;
const rows = (f: FrameOut) =>
  f.items
    .map(
      (x) =>
        `<li class="mag-credit st-credit" data-item="${x.id}"><span class="mag-credit-n num">${String(x.n).padStart(2, '0')}</span>${swatch(x)}<span class="mag-credit-body"><button type="button" class="st-open" data-item="${x.id}" aria-haspopup="dialog"><span class="mag-credit-name">${esc(x.name_he)}</span></button><span class="mag-credit-detail">${esc(x.detail_he)}${x.status === 'unavailable' ? ' · המלאי אינו זמין כעת' : ''}</span></span></li>`,
    )
    .join('\n');
function spread(f: FrameOut, eager: boolean): string {
  const h = f.role === 'opening' ? 'h1' : 'h2';
  return `<section class="mag-spread st-spread" id="frame-${f.id}" data-head="${esc(head(f))}" data-role="${f.role}" aria-labelledby="title-${f.id}">
  <div class="mag-stage" data-frame="${f.id}" data-marks="off" role="group" aria-label="${esc(`${f.title_he}: ${f.items.length} מוצרים בתמונה`)}">
    <div class="mag-scroller">
      <div class="mag-frame" style="--aspect: ${f.aspect.toFixed(4)}">
        ${picture(f, eager)}
        ${marks(f)}
      </div>
    </div>
    <div class="mag-label" aria-hidden="true"></div>
  </div>
  <div class="st-text">
    <p class="st-kicker">${esc(f.role === 'other-style' ? `בסגנונות אחרים · ${f.style_he}` : head(f))}</p>
    <${h} id="title-${f.id}" class="st-title"><span class="st-title-line">${esc(f.title_he)}</span></${h}>
    <p class="st-line">${esc(f.line_he)}</p>
    <p class="st-to-list"><a class="st-link" href="#list-${f.id}">כל המוצרים בתמונה · <span class="num">${f.items.length}</span></a></p>
  </div>
  <p class="st-mark${f.draft_he ? ' is-draft' : ''}">${esc(f.draft_he ? `${man.mark_he} · ${f.draft_he}` : man.mark_he)}</p>
</section>
<section class="mag-paper st-list" id="list-${f.id}" data-head="${esc(head(f))}" aria-labelledby="list-title-${f.id}">
  <div class="mag-grid">
    <p class="mag-run-head mag-col-main" aria-hidden="true">${esc(head(f))}</p>
    <h2 id="list-title-${f.id}" class="mag-h2 mag-col-main">כל המוצרים בתמונה</h2>
    <p class="mag-cap mag-col-main">${esc(f.title_he)} · <span class="num">${f.items.length}</span> מוצרים. נגיעה בשם פותחת את "קנה את המראה".</p>
    <ol class="mag-credits st-credits mag-col-main">
${rows(f)}
    </ol>
  </div>
</section>`;
}
const others = `<ul class="st-styles mag-col-main">
  <li class="st-style"><a class="st-link" href="#frame-warm-modern-A">מודרני חם</a> <span class="mag-cap">טיוטה · כמעט מוכן</span></li>
${man.next_styles_he.map((s) => `  <li class="st-style is-next"><span>${esc(s)}</span> <span class="mag-cap">בגיליונות הבאים</span></li>`).join('\n')}
</ul>`;

const data = { mark_he: man.mark_he, items: Object.fromEntries(frames.flatMap((f) => f.items.map((x) => [x.id, x]))), frames: frames.map((f) => ({ id: f.id, u0: f.u0, v0: f.v0, aspect: f.aspect, window_u: f.mobile_window_u, title_he: f.title_he, items: f.items.map((x) => x.id) })) };
mkdirSync(GENERATED, { recursive: true });
writeFileSync(join(GENERATED, 'test-page.story.json'), JSON.stringify(data, null, 1));

let html = readFileSync(sitePath('tools/test-page/story.template.html'), 'utf8');
const fill: Record<string, string> = {
  ISSUE: esc(man.issue_he),
  MARK: esc(man.mark_he),
  OPENING: spread(F('nordic-A'), true),
  SECOND: spread(F('nordic-B'), false),
  TOOL_HREF: esc(man.tool.href),
  OTHERS: others,
  OTHER_FRAME: spread(F('warm-modern-A'), false),
  NOTES: esc(frames.map((f) => `${f.title_he}: ${f.note_he}`).join('. ')),
  DATA: JSON.stringify(data).replace(/</g, '\\u003c'),
};
for (const [k, v] of Object.entries(fill)) html = html.split(`{{${k}}}`).join(v);
const left = html.match(/\{\{[A-Z0-9_]+\}\}/g);
if (left) throw new Error(`template placeholders left: ${left.join(', ')}`);
mkdirSync(sitePath('web/test/story'), { recursive: true });
writeFileSync(sitePath('web/test/story/index.html'), html);
const all = frames.flatMap((f) => f.items);
console.log(
  `story page → web/test/story/index.html (${(html.length / 1024).toFixed(1)} KB): ${all.length} points, ${all.filter((x) => x.status === 'available').length} for sale, ${all.filter((x) => x.status === 'unavailable').length} not sold now, ${all.filter((x) => x.status === 'unpriced').length} without a price (${[...new Set(all.filter((x) => x.status === 'unpriced').map((x) => x.product))].join(', ') || 'none'}); ${all.filter((x) => !x.image).length} without a cached card photo`,
);
