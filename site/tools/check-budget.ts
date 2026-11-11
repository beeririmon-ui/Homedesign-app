/**
 * Bundle and first-load budgets (skeleton-spec, "ביצועים"). Static estimate from web/dist; the e2e suite measures
 * the real transfer in a mobile browser (e2e/perf.spec.ts).
 *
 *   first load of the living room on mobile ≤ 3 MB: HTML + JS + CSS + Hebrew/Latin fonts + the poster and every layer
 *   of the default composition at the width the engine picks on a 412×915 @2x phone, plus the depth map.
 *   JS entry ≤ 80 KB gzip, CSS ≤ 15 KB gzip. S13: the room's own JS stays ≤ 74 KB (a goal, not a raised budget): the
 *   pages off its first paint are lazy chunks (web/src/pages/lazy.tsx), and the browser's shared code carries no zod.
 *   S5, the story (when built): a page's JS ≤ 40 KB gzip and CSS ≤ 15 KB gzip; its first view on a phone ≤ 1.2 MB, a
 *   detail page's ≤ 0.9 MB.
 */
import { readFileSync, readdirSync, existsSync, statSync } from 'node:fs';
import { gzipSync } from 'node:zlib';
import { join } from 'node:path';
import { sitePath } from './lib/paths';
import { lazyPagesInEntry, lazyPagesMissing, readGraph } from './lib/bundle-graph';

const DIST = sitePath('web/dist');
const MB = 1024 * 1024;
const BUDGET = { firstLoad: 3 * MB, jsGz: 80 * 1024, cssGz: 15 * 1024 };

type Scene = {
  aspect: number;
  widths: { lo: number; hi: number };
  base: { src: string; widths: number[] }[];
  slots: Record<string, { product: { src: string[] } | null; shadow: { src: string[] } | null; light: { src: string[] } | null }>;
  depth: { src: string };
};
type Catalog = {
  rooms: { id: string; slots: { id: string; has_shadow: boolean; has_light: boolean; options: { position: number; is_default: boolean }[] }[] }[];
};

if (!existsSync(DIST)) {
  console.error('web/dist is missing: run `npm run build` first.');
  process.exit(1);
}
const scene = JSON.parse(readFileSync(sitePath('.generated/scene.living-room.nordic.json'), 'utf8')) as Scene;
const catalog = JSON.parse(readFileSync(sitePath('.generated/catalog.public.json'), 'utf8')) as Catalog;
const room = catalog.rooms.find((r) => r.id === 'living-room')!;

const assets = readdirSync(join(DIST, 'assets'));
const gz = (f: string) => gzipSync(readFileSync(f)).length;
// the entry: the scripts and stylesheets the room page's HTML references (its own and the chunks it preloads); another
// entry of the build (the test page, /test/) has its own files and is reported, not budgeted here
const entryHtml = readFileSync(join(DIST, 'index.html'), 'utf8');
const referenced = new Set([...entryHtml.matchAll(/\/assets\/([^"' ]+\.(?:js|css))/g)].map((m) => m[1]!));
const js = assets.filter((f) => f.endsWith('.js') && referenced.has(f)).map((f) => gz(join(DIST, 'assets', f)));
const css = assets.filter((f) => f.endsWith('.css') && referenced.has(f)).map((f) => gz(join(DIST, 'assets', f)));
const otherJs = assets.filter((f) => f.endsWith('.js') && !referenced.has(f)).map((f) => gz(join(DIST, 'assets', f)));
const otherCss = assets.filter((f) => f.endsWith('.css') && !referenced.has(f)).map((f) => gz(join(DIST, 'assets', f)));
// one woff2 per weight for the Hebrew subset and one for Latin (unicode-range: a Hebrew page needs both)
const fonts = assets.filter((f) => /-(hebrew|latin)-\d{3}-normal-.*\.woff2$/.test(f)).reduce((s, f) => s + statSync(join(DIST, 'assets', f)).size, 0);
const html = gz(join(DIST, 'rooms/living-room/index.html'));

// phone: 412×915 CSS px, DPR 2, header 60 px; the stage is cover-fitted to the 16:9 frame
const vw = 412;
const vh = 915 - 60;
const dpr = 2;
// mirrors the poster's sizes (portrait: min((100svh - 60px) × 1.78, 1080px)) and the engine (phones compose at lo)
const need = Math.min(Math.max(vw, vh * scene.aspect), 1080) * dpr;
const shell = scene.base[0]!;
const posterW = shell.widths.find((w) => w >= need) ?? shell.widths[shell.widths.length - 1]!;
const res = vw <= 900 ? scene.widths.lo : posterW > scene.widths.lo ? scene.widths.hi : scene.widths.lo;
/** a media file's size: the AVIF where the browser reads it, else the WebP. S16 (QA ת43): `['webp']` for a browser without AVIF */
type Formats = ('avif' | 'webp')[];
const file = (src: string, w?: number, formats: Formats = ['avif', 'webp']) => {
  for (const ext of formats) {
    const p = sitePath('web/public/media', `${src}${w ? `.${w}` : ''}.${ext}`);
    if (existsSync(p)) return statSync(p).size;
  }
  return 0;
};
const roomMedia = (formats: Formats) => {
  let bytes = file(shell.src, posterW, formats) + file(scene.depth.src, undefined, formats);
  let files = 2;
  for (const s of room.slots) {
    const sc = scene.slots[s.id];
    if (!sc) continue;
    const n = (s.options.find((o) => o.is_default)?.position ?? 1) - 1;
    for (const set of [sc.product, s.has_shadow ? sc.shadow : null, s.has_light ? sc.light : null]) {
      const src = set?.src[n] ?? set?.src[0];
      if (src) {
        bytes += file(src, res, formats);
        files++;
      }
    }
  }
  return { bytes, files };
};
const { bytes: layers, files: count } = roomMedia(['avif', 'webp']);
const layersNoAvif = roomMedia(['webp']).bytes;

const sum = (a: number[]) => a.reduce((s, x) => s + x, 0);
const total = html + sum(js) + sum(css) + fonts + layers;
const kb = (n: number) => `${(n / 1024).toFixed(1)} KB`;
const rows: [string, number, number | null][] = [
  ['JS (gzip), the room page entry', sum(js), BUDGET.jsGz],
  ['CSS (gzip), the room page entry', sum(css), BUDGET.cssGz],
  // S13: the pages off the room's first paint (product, cart, checkout, order, legal) are chunks loaded on their route
  [`lazy chunks + test page: JS ${otherJs.length} files, CSS ${otherCss.length}`, sum(otherJs) + sum(otherCss), null],
  ['fonts (woff2, he+latin)', fonts, null],
  [`room media (${count} files, shell @${posterW}, layers @${res})`, layers, null],
  ['first load, living room, mobile', total, BUDGET.firstLoad],
  // S16, QA ת43: a browser without AVIF loads every WebP fallback instead
  ['first load, living room, mobile, no AVIF', total - layers + layersNoAvif, BUDGET.firstLoad],
];
// S14 (QA ת29/ת30): a direct entry to another house (warm-modern) on the same phone: its own page, the room's entry and
// the house's chunk, the poster (its default composition, at the width the same sizes pick) and the composition the
// engine draws at the house's native width (the base, the default set's layers, the depth map). Behind the flag: the
// public build has no house pages.
const housePage = join(DIST, 'house/living-room/warm-modern/index.html');
const houseData = sitePath('.generated/house.living-room.warm-modern.json');
if (existsSync(housePage) && existsSync(houseData)) {
  const hs = (JSON.parse(readFileSync(houseData, 'utf8')) as { scene: Scene & { native?: number; poster?: { src: string; widths: number[] } } }).scene;
  const chunk = assets.filter((f) => /^warm-modern-.*\.js$/.test(f)).map((f) => gz(join(DIST, 'assets', f)));
  const pst = hs.poster ?? hs.base[0]!;
  const pw = pst.widths.find((w) => w >= need) ?? pst.widths[pst.widths.length - 1]!;
  const at = hs.native ?? hs.widths.hi;
  const houseMedia = (formats: Formats) => {
    let m = file(pst.src, pw, formats) + file(hs.depth.src, undefined, formats) + file(hs.base[0]!.src, at, formats);
    for (const sc of Object.values(hs.slots)) for (const set of [sc.product, sc.shadow, sc.light]) if (set?.src[0]) m += file(set.src[0], at, formats);
    return m;
  };
  const media = houseMedia(['avif', 'webp']);
  // S16, QA ת43: a browser without AVIF: the poster's WebP fallback, and the engine's composition (it starts at idle there)
  const mediaNoAvif = houseMedia(['webp']);
  const page = gz(housePage) + sum(js) + sum(chunk) + sum(css) + fonts;
  rows.push(
    [`warm-modern house media (poster @${pw}, composition @${at})`, media, null],
    ['first load, the warm-modern house, mobile', page + media, BUDGET.firstLoad],
    [`warm-modern house media, no AVIF (WebP poster @${pw}, composition @${at})`, mediaNoAvif, null],
    ['first load, the warm-modern house, mobile, no AVIF', page + mediaNoAvif, BUDGET.firstLoad],
  );
}
// S5: the story's pages (behind the flag; absent from the public build). A story page's own scripts and styles, and its
// first view on the phone: HTML, scripts, styles, fonts and the first frame's phone picture at 412 @2x (AVIF, which
// every browser the site supports reads). A detail page the same way, with its first picture.
const storyPage = join(DIST, 'story/living-room/nordic/index.html');
if (existsSync(storyPage)) {
  const STORY = { jsGz: 40 * 1024, cssGz: 15 * 1024, firstView: 1.2 * MB, detailView: 0.9 * MB };
  const refs = (page: string) => [...readFileSync(page, 'utf8').matchAll(/\/assets\/([^"' ]+\.(?:js|css))/g)].map((m) => m[1]!);
  const own = (page: string, ext: string) => [...new Set(refs(page).filter((f) => f.endsWith(ext)))].map((f) => gz(join(DIST, 'assets', f)));
  /** the smallest picture of the first srcset that covers 824 px (412 @2x), from the media folder */
  const firstPicture = (page: string): number => {
    const set = /srcset="([^"]+)"/.exec(readFileSync(page, 'utf8'))?.[1] ?? '';
    const cands = set.split(', ').map((c) => {
      const [url = '', w = '0w'] = c.trim().split(' ');
      return { url: url.replace(/\?.*$/, ''), w: parseInt(w) };
    });
    const pick = cands.find((c) => c.w >= 824) ?? cands[cands.length - 1];
    if (!pick) return 0;
    const f = join(DIST, pick.url);
    return existsSync(f) ? statSync(f).size : 0;
  };
  const view = (page: string) => gz(page) + sum(own(page, '.js')) + sum(own(page, '.css')) + fonts + firstPicture(page);
  const detailDir = join(DIST, 'story/living-room/nordic/p');
  const detail = existsSync(detailDir) ? join(detailDir, readdirSync(detailDir).sort()[0]!, 'index.html') : null;
  rows.push(
    ['JS (gzip), a story page', sum(own(storyPage, '.js')), STORY.jsGz],
    ['CSS (gzip), a story page', sum(own(storyPage, '.css')), STORY.cssGz],
    ['first view, a story page, mobile (the Nordic living room)', view(storyPage), STORY.firstView],
    ...(detail ? ([['first view, a detail page, mobile', view(detail), STORY.detailView]] as [string, number, number][]) : []),
  );
}
// S13: the goal under the budget, so the next features have room; and no lazy page is in the room's entry.
// S16, QA ת44: checked by content, not by file name: the build's chunk graph (tools/lib/bundle-graph.ts) says which
// modules' code each chunk carries; the entry's static closure must carry none of the lazy pages
const ROOM_GOAL = 74 * 1024;
let failed = false;
if (sum(js) > ROOM_GOAL) console.log(`note  the room's JS is over the S13 goal of ${kb(ROOM_GOAL)}: split before adding`);
const graph = readGraph();
if (!graph) {
  failed = true;
  console.log('FAIL  .generated/bundle-graph.json is missing: the web build writes it (web/vite.config.ts, bundleGraph)');
} else {
  const entry = [...referenced].filter((f) => f.endsWith('.js')).map((f) => `assets/${f}`);
  const lazyInEntry = lazyPagesInEntry(graph, entry);
  const missing = lazyPagesMissing(graph);
  if (lazyInEntry.length) {
    failed = true;
    console.log(`FAIL  a lazy page's code is in the room's entry: ${lazyInEntry.join(', ')}`);
  } else if (missing.length) {
    failed = true;
    console.log(`FAIL  a lazy page is in no chunk of the build (renamed or removed?): ${missing.join(', ')}`);
  } else console.log(`ok    no lazy page's code in the room's entry (by content: ${entry.length} entry chunk(s) and their static imports)`);
}
for (const [name, v, max] of rows) {
  const over = max !== null && v > max;
  failed ||= over;
  console.log(`${over ? 'FAIL' : 'ok  '}  ${name.padEnd(56)} ${kb(v).padStart(10)}${max ? `  / ${kb(max)}` : ''}`);
}
if (failed) process.exit(1);
