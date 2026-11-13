/**
 * dist-artifact/index.html (vite --mode artifact, JS and CSS already inlined) → the claude.ai Artifact page contract:
 *   no doctype/html/head/body; <title> first, then <style>; Google Fonts is the only external resource;
 *   images as relative files next to the page (media/...), WebP only, the reduced set src/catalog.ts declares.
 */
import { readFileSync, writeFileSync, mkdirSync, copyFileSync, existsSync, readdirSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { sitePath } from './lib/paths';

const OUT = sitePath('dist-artifact');
const MEDIA = sitePath('web/public/media');
const built = readFileSync(join(OUT, 'index.html'), 'utf8');

const styles = [...built.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)].map((m) => m[1]!.trim());
const scripts = [...built.matchAll(/<script type="module"[^>]*>([\s\S]*?)<\/script>/g)].map((m) => m[1]!.trim());
if (styles.length !== 1 || scripts.length !== 1) throw new Error(`expected one inlined style and one script, got ${styles.length}/${scripts.length}`);
const css = styles[0]!;
if (!css.startsWith(':root{')) throw new Error('the stylesheet must start with the :root light tokens');

const FONTS = 'https://fonts.googleapis.com/css2?family=Assistant:wght@400;600&family=Frank+Ruhl+Libre:wght@300;500&display=swap';
const page = [
  '<title>הבית · תצוגה מקדימה</title>',
  `<style>${css}</style>`,
  '<link rel="preconnect" href="https://fonts.googleapis.com">',
  '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
  `<link rel="stylesheet" href="${FONTS}">`,
  '<meta name="description" content="תצוגה מקדימה: הדמיית הסיור בבית המודרני החם (דלת הכניסה, הסלון, חשיפת המוצרים, גלגל הגרסאות ומעבר הסגנון), ומאחוריה החנות. חלקים זמניים מסומנים.">',
  '<div id="app"></div>',
  `<script type="module">${scripts[0]!.replace(/<\/script/gi, '<\\/script')}</script>`,
  '',
].join('\n');
writeFileSync(join(OUT, 'index.html'), page);

// ---- media: exactly what the artifact scene can request ----
type Scene = {
  widths: { lo: number };
  base: { src: string; widths: number[] }[];
  slots: Record<string, { product: { src: string[] } | null; shadow: { src: string[] } | null; light: { src: string[] } | null }>;
  depth: { src: string };
  hall: { src: string; widths: number[] };
};
const scene = JSON.parse(readFileSync(sitePath('.generated/scene.living-room.nordic.json'), 'utf8')) as Scene;
const lo = scene.widths.lo;
const files = new Set<string>();
for (const b of scene.base) for (const w of b.widths.filter((x) => x <= lo)) files.add(`${b.src}.${w}.webp`);
for (const w of scene.hall.widths.filter((x) => x <= lo)) files.add(`${scene.hall.src}.${w}.webp`);
files.add(`${scene.depth.src}.webp`);
for (const s of Object.values(scene.slots)) for (const set of [s.product, s.shadow, s.light]) for (const src of set?.src ?? []) files.add(`${src}.${lo}.webp`);
// MOCK1: the walk to the hall (T-E0) is not shipped (web/src/catalog.ts: the Artifact's scene has no transitions); its
// files' place goes to the tour: the warm-modern base and every layer, shadow and wheel picture of the mock-up
type Tour = {
  native: number;
  widths: { lo: number; hi: number };
  card_width: number;
  base: { src: string };
  slots: { src: string; options: { position: number; card: { src: string } }[] }[];
};
const tour = JSON.parse(readFileSync(sitePath('.generated/tour.living-room.warm-modern.json'), 'utf8')) as Tour;
// MOCK2: the preview ships one width, `lo`, and the page composes there (web/src/tour/data.ts widthFor in an artifact
// build): half the bytes of the layers' own width, and the file count stays inside the Artifact's 200
const tw = tour.widths.lo;
files.add(`${tour.base.src}.${tw}.webp`);
for (const s of tour.slots)
  for (const o of s.options) {
    for (const kind of [`product.${tw}`, `shadow.${tw}`]) files.add(`${s.src}/${o.position}.${kind}.webp`);
    // the wheel's card: the product on its own (a studio picture of ours, or its layer trimmed)
    files.add(`${o.card.src}.webp`);
  }
// FR-I: the supplier's photo of every shown product (one per product, encoded by tools/supplier-images.ts)
type SupplierManifest = {
  width: number;
  products: Record<string, { src: string }>;
  options?: Record<string, { files: { name: string; artifact: boolean }[] }>;
};
const supplier = JSON.parse(readFileSync(sitePath('.generated/supplier-images.json'), 'utf8')) as SupplierManifest;
for (const s of Object.values(supplier.products)) files.add(`${s.src}.webp`);
// supplier options: the pictures src/catalog.ts uses in the Artifact (a capped set, tools/supplier-images.ts)
for (const [pid, o] of Object.entries(supplier.options ?? {}))
  for (const f of o.files) if (f.artifact) files.add(`products/${pid}/${f.name}.${supplier.width}.webp`);

rmSync(join(OUT, 'media'), { recursive: true, force: true });
let missing = 0;
for (const f of files) {
  const from = join(MEDIA, f);
  if (!existsSync(from)) {
    console.warn(`missing media: ${f}`);
    missing++;
    continue;
  }
  const to = join(OUT, 'media', f);
  mkdirSync(dirname(to), { recursive: true });
  copyFileSync(from, to);
}
// nothing else in the folder (vite may leave a favicon etc.)
for (const name of readdirSync(OUT)) if (name !== 'index.html' && name !== 'media') rmSync(join(OUT, name), { recursive: true, force: true });
console.log(`artifact: index.html + ${files.size - missing} media files${missing ? ` (${missing} missing)` : ''}`);
if (missing) process.exit(1);
