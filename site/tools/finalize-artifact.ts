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

const FONTS =
  'https://fonts.googleapis.com/css2?family=Assistant:wght@400;600&family=Frank+Ruhl+Libre:wght@300;500&display=swap';
const page = [
  '<title>הבית · תצוגה מקדימה</title>',
  `<style>${css}</style>`,
  '<link rel="preconnect" href="https://fonts.googleapis.com">',
  '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
  `<link rel="stylesheet" href="${FONTS}">`,
  '<meta name="description" content="תצוגה מקדימה של החנות: הסלון הנורדי, נקודות מוצר, גלגל וריאציות, עמוד מוצר, סל ותשלום מדומה. תמונות ומחירים זמניים.">',
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
  transitions: Record<string, { src: string; frames: number }>;
};
const scene = JSON.parse(readFileSync(sitePath('.generated/scene.living-room.nordic.json'), 'utf8')) as Scene;
const lo = scene.widths.lo;
const files = new Set<string>();
for (const b of scene.base) for (const w of b.widths.filter((x) => x <= lo)) files.add(`${b.src}.${w}.webp`);
for (const w of scene.hall.widths.filter((x) => x <= lo)) files.add(`${scene.hall.src}.${w}.webp`);
files.add(`${scene.depth.src}.webp`);
for (const s of Object.values(scene.slots))
  for (const set of [s.product, s.shadow, s.light]) for (const src of set?.src ?? []) files.add(`${src}.${lo}.webp`);
for (const t of Object.values(scene.transitions))
  for (let i = 1; i <= t.frames; i++) files.add(`${t.src}/${String(i).padStart(3, '0')}.webp`);

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
