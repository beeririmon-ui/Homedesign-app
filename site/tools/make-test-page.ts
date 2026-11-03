/**
 * The Nordic test page in the magazine language (briefs/site-test-page-2026-11-03.md; docs/site-art-direction-2026-11-02.md
 * §12). Everything the page shows comes from one manifest, tools/test-page/nordic.json: the temporary frames, their
 * principal points and phone windows, the clay-measured product boxes, the P-D pan clip, and the catalog the credits
 * are read from. Swapping to QA'd assets is a change of those paths only.
 *
 *   tsx tools/make-test-page.ts
 *
 * Writes
 *   web/public/media/test/<frame>/{1280,1920,2736}.{avif,webp}   the frame, cover-fitted on desktop
 *   web/public/media/test/<frame>/m{780,1170}.{avif,webp}          the phone 3:5 window of the frame (art direction §5.2)
 *   web/public/media/test/p-d/{1920,mobile}/NNNN.{avif,webp}       the P-D pan clip (copied as it is)
 *   .generated/test-page.nordic.json                               the resolved manifest (LQIPs, credits, boxes)
 *   web/test/index.html                                            the page, from tools/test-page/index.template.html,
 *                                                                  with the LQIPs and the credits inlined (phone-first:
 *                                                                  the cover is there before any script runs)
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync, copyFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import sharp from 'sharp';
import { formatIls } from '@hd/shared/money';
import type { PublicCatalog, PublicProduct, SupplierImageManifest } from '@hd/shared';
import { GENERATED, MEDIA_OUT, repoPath, sitePath } from './lib/paths';

type Frame = { src: string; u0: number; v0: number; mobile_window_u: number; qa: boolean; note_he: string; boxes?: string; room?: string; box_room_key?: string };
type Source = {
  style: string;
  issue_he: string;
  label_he: string;
  frames: Record<string, Frame>;
  pan: { id: string; from: string; to: string; dir: string; manifest: string; qa: boolean; note_he: string };
  catalog: string;
  supplier_images: string;
  rooms: { n: string; id: string; name_he: string; frame?: string }[];
  styles: { id: string; name_he: string; available: boolean }[];
  focus_phone_closeup: string;
};
type Box = [number, number, number, number];
type Fidelity = { frame: string; products: Record<string, { box_uv: Box; visible_pct_clay: number | null }> };

const src = JSON.parse(readFileSync(sitePath('tools/test-page/nordic.json'), 'utf8')) as Source;
const OUT = join(MEDIA_OUT, 'test');
mkdirSync(OUT, { recursive: true });
const WIDTHS = [1280, 1920, 2736];
const PHONE_WIDTHS = [780, 1170];
const WINDOW_W = 0.3375; // the 3:5 window of a 16:9 frame (skeleton spec, "mobile")

const catalogPath = sitePath(src.catalog);
if (!existsSync(catalogPath)) {
  console.error(`${src.catalog} is missing: run tsx tools/build-catalog.ts --rooms=living-room,dining-room --out=test-page`);
  process.exit(1);
}
const catalog = JSON.parse(readFileSync(catalogPath, 'utf8')) as PublicCatalog;
const supplier = existsSync(sitePath(src.supplier_images)) ? (JSON.parse(readFileSync(sitePath(src.supplier_images), 'utf8')) as SupplierImageManifest) : null;

async function lqip(img: sharp.Sharp, w: number, h: number): Promise<string> {
  const buf = await img.clone().resize(w, h, { fit: 'fill' }).webp({ quality: 40 }).toBuffer();
  return `data:image/webp;base64,${buf.toString('base64')}`;
}
async function encode(img: sharp.Sharp, rel: string, width: number): Promise<void> {
  const base = join(OUT, rel);
  mkdirSync(join(base, '..'), { recursive: true });
  const r = img.clone().resize({ width, withoutEnlargement: true });
  await r.clone().avif({ quality: 52, effort: 4 }).toFile(`${base}.avif`);
  await r.clone().webp({ quality: 74, effort: 4 }).toFile(`${base}.webp`);
}

/** The defining size of a product, in words (art direction §4.4): the one that defines it, the rest on the product page. */
function sizeHe(p: PublicProduct, placement: string): string | null {
  const { width: w, depth: d, height: h } = p.dimensions_cm;
  const x = (a: number, b: number) => `⁦${a}×${b}⁩ ס״מ`;
  if ((placement === 'floor' || placement === 'sofa') && w && d) return x(w, d);
  if (placement === 'wall' && w && h) return x(w, h);
  if (h) return `גובה ⁦${h}⁩ ס״מ`;
  if (w && d) return x(w, d);
  if (w) return `רוחב ⁦${w}⁩ ס״מ`;
  return null;
}
type Credit = { id: string; name_he: string; detail_he: string; price_he: string; unavailable: boolean; thumb: string | null };
function credit(p: PublicProduct, placement: string): Credit {
  const parts = [p.materials_he[0] ?? null, sizeHe(p, placement), formatIls(p.price_agorot)].filter((x): x is string => !!x);
  const img = supplier?.products[p.id];
  return {
    id: p.id,
    name_he: p.name_he,
    detail_he: parts.join(' · '),
    price_he: formatIls(p.price_agorot),
    unavailable: p.availability.status !== 'available',
    thumb: img ? `/media/${img.src}.webp` : null,
  };
}

type Hotspot = { slot: string; name_he: string; box: Box; u: number; v: number; credit: Credit | null; variants: Credit[]; placement: string };
function hotspots(frame: Frame): Hotspot[] {
  if (!frame.boxes || !frame.room) return [];
  const fid = JSON.parse(readFileSync(repoPath(frame.boxes), 'utf8')) as Fidelity;
  const room = catalog.rooms.find((r) => r.id === frame.room);
  if (!room) return [];
  const out: Hotspot[] = [];
  for (const [key, m] of Object.entries(fid.products)) {
    const [rk, slotId] = key.split('/');
    if (rk !== frame.box_room_key || !slotId) continue;
    const slot = room.slots.find((s) => s.id === slotId);
    if (!slot) continue;
    if (m.visible_pct_clay !== null && m.visible_pct_clay < 50) continue; // the counting rule: under 50% visible, no point
    const products = slot.options.map((o) => catalog.products.find((p) => p.id === o.product_id)).filter((p): p is PublicProduct => !!p);
    const [u0, u1, v0, v1] = m.box_uv;
    out.push({
      slot: slot.id,
      name_he: slot.name_he,
      box: m.box_uv,
      // the mark sits inside the product, low in the box (the deepest point of a standing object), never on its edge
      u: (u0 + u1) / 2,
      v: v0 + (v1 - v0) * 0.62,
      credit: products[0] ? credit(products[0], slot.placement) : null,
      variants: products.map((p) => credit(p, slot.placement)),
      placement: slot.placement,
    });
  }
  return out.sort((a, b) => a.u - b.u);
}

const resolved: Record<string, unknown> = { style: src.style, issue_he: src.issue_he, label_he: src.label_he, rooms: src.rooms, styles: src.styles, focus_phone_closeup: src.focus_phone_closeup, frames: {} };
const framesOut = resolved.frames as Record<string, unknown>;
for (const [id, f] of Object.entries(src.frames)) {
  const img = sharp(repoPath(f.src));
  const meta = await img.metadata();
  const W = meta.width!;
  const H = meta.height!;
  for (const w of WIDTHS) await encode(img, `${id}/${w}`, w);
  // the phone window: full height, 3:5, centred on mobile_window_u (clamped to the frame)
  const ww = Math.round(H * 0.6);
  const left = Math.round(Math.min(W - ww, Math.max(0, f.mobile_window_u * W - ww / 2)));
  const phone = img.clone().extract({ left, top: 0, width: ww, height: H });
  for (const w of PHONE_WIDTHS) await encode(phone, `${id}/m${w}`, w);
  framesOut[id] = {
    ...f,
    width: W,
    height: H,
    aspect: W / H,
    window: { u0: left / W, u1: (left + ww) / W },
    lqip: await lqip(img, 32, Math.round((32 * H) / W)),
    lqip_phone: await lqip(phone, 24, 40),
    srcset: WIDTHS.map((w) => `/media/test/${id}/${w}`),
    srcset_phone: PHONE_WIDTHS.map((w) => `/media/test/${id}/m${w}`),
    hotspots: hotspots(f),
  };
  console.log(`${id}: ${W}×${H}, window u ${(left / W).toFixed(3)}–${((left + ww) / W).toFixed(3)}, ${(framesOut[id] as { hotspots: unknown[] }).hotspots.length} hotspots`);
}

// the P-D pan clip, as exported by motion-agent (export_seq.py); copied, never re-encoded
const panManifest = JSON.parse(readFileSync(repoPath(src.pan.manifest), 'utf8')) as {
  frames: number;
  fps: number;
  play_s: number;
  easing: { accel: number; land: number };
  variants: Record<string, { w: number; h: number; webp_frames: number; webp_fps: number }>;
};
const panOut: Record<string, { w: number; h: number; avif: number; webp: number }> = {};
for (const variant of ['1920', 'mobile']) {
  const from = repoPath(src.pan.dir, variant);
  const to = join(OUT, 'p-d', variant);
  mkdirSync(to, { recursive: true });
  const files = readdirSync(from).filter((f) => /^\d{4}\.(avif|webp)$/.test(f));
  for (const f of files) copyFileSync(join(from, f), join(to, f));
  const v = panManifest.variants[variant]!;
  panOut[variant] = { w: v.w, h: v.h, avif: files.filter((f) => f.endsWith('.avif')).length, webp: files.filter((f) => f.endsWith('.webp')).length };
}
resolved.pan = { ...src.pan, src: '/media/test/p-d', frames: panManifest.frames, fps: panManifest.fps, play_s: panManifest.play_s, easing: panManifest.easing, variants: panOut };
console.log(`P-D: ${panManifest.frames} frames, ${panManifest.play_s} s, variants ${Object.entries(panOut).map(([k, v]) => `${k} ${v.avif} avif / ${v.webp} webp`).join(', ')}`);

mkdirSync(GENERATED, { recursive: true });
writeFileSync(join(GENERATED, 'test-page.nordic.json'), JSON.stringify(resolved, null, 1));

// ---------- the page: the template with the data the first paint needs ----------
const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
type FrameOut = Frame & { lqip: string; lqip_phone: string; srcset: string[]; srcset_phone: string[]; aspect: number; window: { u0: number; u1: number }; hotspots: Hotspot[]; width: number; height: number };
const F = framesOut as Record<string, FrameOut>;
const picture = (id: string, alt: string, eager: boolean) => {
  const f = F[id]!;
  const set = (list: string[], ext: 'avif' | 'webp', widths: number[]) => list.map((s, i) => `${s}.${ext} ${widths[i]}w`).join(', ');
  return `<picture class="mag-pic" data-frame="${id}">
  <source media="(max-width: 719px)" type="image/avif" srcset="${set(f.srcset_phone, 'avif', PHONE_WIDTHS)}" sizes="60svh" />
  <source media="(max-width: 719px)" type="image/webp" srcset="${set(f.srcset_phone, 'webp', PHONE_WIDTHS)}" sizes="60svh" />
  <source type="image/avif" srcset="${set(f.srcset, 'avif', WIDTHS)}" sizes="100vw" />
  <img src="${f.srcset[1]}.webp" srcset="${set(f.srcset, 'webp', WIDTHS)}" sizes="100vw" alt="${esc(alt)}" width="${f.width}" height="${f.height}" decoding="async" ${eager ? 'fetchpriority="high"' : 'loading="lazy"'} style="object-position: ${(f.u0 * 100).toFixed(1)}% ${(f.v0 * 100).toFixed(1)}%" />
</picture>`;
};
const lqipImg = (id: string) => {
  const f = F[id]!;
  return `<img class="mag-lqip" src="${f.lqip}" alt="" aria-hidden="true" width="${f.width}" height="${f.height}" style="object-position: ${(f.u0 * 100).toFixed(1)}% ${(f.v0 * 100).toFixed(1)}%" /><img class="mag-lqip mag-lqip-phone" src="${f.lqip_phone}" alt="" aria-hidden="true" width="24" height="40" />`;
};
const marks = (id: string) =>
  F[id]!.hotspots
    .map((h) => {
      const c = h.credit;
      const label = c ? `${h.name_he}: ${c.name_he}. ${c.detail_he}${c.unavailable ? '. המלאי אינו זמין כעת' : ''}` : `${h.name_he}: ממתינה למוצר`;
      return `<button type="button" class="mag-mark" data-slot="${h.slot}" data-u="${h.u}" data-v="${h.v}" data-box="${h.box.join(',')}" style="--u: ${h.u}; --v: ${h.v}" aria-label="${esc(label)}. פתיחת הווריאציות"><span class="mag-dot" aria-hidden="true"></span></button>`;
    })
    .join('\n');
const roomsList = src.rooms
  .map((r) => {
    const live = r.frame && F[r.frame];
    return `<li class="mag-toc-row${live ? '' : ' is-next'}">${live ? `<a class="mag-toc-link" href="#room-${r.id}" data-room="${r.id}">` : '<span class="mag-toc-link">'}<span class="mag-toc-n num">${r.n}</span><span class="mag-toc-name">${esc(r.name_he)}</span><span class="mag-toc-cap">${live ? 'נורדי' : 'בגיליונות הבאים'}</span>${live ? '</a>' : '</span>'}</li>`;
  })
  .join('\n');
const stylesLine = src.styles.map((s) => `<span class="mag-style${s.available ? ' is-on' : ''}">${esc(s.name_he)}${s.available ? '' : ' <span class="mag-cap">(בגיליונות הבאים)</span>'}</span>`).join('<span class="mag-sep" aria-hidden="true"> · </span>');
const creditsList = (id: string) =>
  F[id]!.hotspots
    .map((h, i) => {
      const c = h.credit;
      return `<li class="mag-credit" data-slot="${h.slot}"><span class="mag-credit-n num">${String(i + 1).padStart(2, '0')}</span><span class="mag-credit-body"><span class="mag-credit-name">${esc(c ? c.name_he : h.name_he)}</span><span class="mag-credit-detail">${esc(c ? c.detail_he : 'ממתינה למוצר')}${c?.unavailable ? ' · המלאי אינו זמין כעת' : ''}</span></span></li>`;
    })
    .join('\n');

let html = readFileSync(sitePath('tools/test-page/index.template.html'), 'utf8');
const fill: Record<string, string> = {
  LABEL: esc(src.label_he),
  ISSUE: esc(src.issue_he),
  COVER_PICTURE: picture('H0', 'הכניסה: המבט אל הסלון המואר מעבר לפתח, הקונסולה מימין', true),
  COVER_LQIP: lqipImg('H0'),
  M0_PICTURE: picture('M0', 'הסלון הנורדי: ספה בשיבולת שועל, שלישייה מעל הספה, אגרטל על אדן החלון', false),
  M0_LQIP: lqipImg('M0'),
  M0_MARKS: marks('M0'),
  M0_CREDITS: creditsList('M0'),
  D1_PICTURE: picture('D1', 'המטבח ופינת האוכל: השולחן מתחת לתלויה, קו המטבח ברקע', false),
  D1_LQIP: lqipImg('D1'),
  D1_MARKS: marks('D1'),
  D1_CREDITS: creditsList('D1'),
  ROOMS: roomsList,
  STYLES: stylesLine,
  M0_NOTE: esc(F.M0!.note_he),
  D1_NOTE: esc(F.D1!.note_he),
  H0_NOTE: esc(F.H0!.note_he),
  PAN_NOTE: esc(src.pan.note_he),
  DATA: JSON.stringify(resolved).replace(/</g, '\\u003c'),
};
for (const [k, v] of Object.entries(fill)) html = html.split(`{{${k}}}`).join(v);
const left = html.match(/\{\{[A-Z0-9_]+\}\}/g);
if (left) throw new Error(`template placeholders left: ${left.join(', ')}`);
mkdirSync(sitePath('web/test'), { recursive: true });
writeFileSync(sitePath('web/test/index.html'), html);
console.log(`test page → web/test/index.html (${(html.length / 1024).toFixed(1)} KB with the LQIPs), manifest → .generated/test-page.nordic.json`);
